import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from data.data import (
    BenchmarkData,
    Countries,
    PriceData,
    ProductData,
    Sectors,
    get_prices_by_dates,
)
from portfolio.constraints import Constraints
from portfolio.cost import TransactionCost
from portfolio.utils import is_business_period_end, make_json_serializable


class CapitalGrowthFrequency(Enum):
    DAILY = "D"
    WEEKLY = "W"
    MONTHLY = "M"
    QUARTERLY = "Q"
    YEARLY = "Y"


class AllocationMethod(Enum):
    EQUAL = "equal"
    MAX_MARKET_CAP = "max_market_cap"
    HIGHEST_VOLUME = "highest_volume"
    OPTIMIZER = "optimizer"


@dataclass
class PortfolioConfig:
    initial_capital: float = 100_000
    initial_holdings: Dict[str, float] = field(default_factory=dict)
    initial_value: float = 0

    capital_growth_freq: str = CapitalGrowthFrequency.MONTHLY.value
    new_capital_growth_pct: float = 0
    new_capital_growth_amt: float = 10000
    allocation_method: str = AllocationMethod.EQUAL.value
    trailing_stop_loss_pct: float = 0.05
    trailing_update_threshold: float = 0.02
    # below are used to reduce trading universe, different from exposure constraints
    min_market_cap: float = 0
    max_market_cap: float = float("inf")
    excluded_sectors: List[Sectors] = field(default_factory=list)
    included_countries: List[Countries] = field(
        default_factory=lambda: [Countries.UNITED_STATES]
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial_capital": self.initial_capital,
            "initial_holdings": self.initial_holdings,
            "initial_value": self.initial_value,
            "capital_growth_freq": self.capital_growth_freq,
            "new_capital_growth_pct": self.new_capital_growth_pct,
            "new_capital_growth_amt": self.new_capital_growth_amt,
            "allocation_method": self.allocation_method,
            "excluded_sectors": self.excluded_sectors,
            "included_countries": self.included_countries,
            "min_market_cap": self.min_market_cap,
            "max_market_cap": self.max_market_cap,
            "trailing_stop_loss_pct": self.trailing_stop_loss_pct,
            "trailing_update_threshold": self.trailing_update_threshold,
        }


class ExitReason(Enum):
    SELL = "sell"
    STOP_LOSS = "stop_loss"
    MAX_DRAWDOWN = "max_drawdown"


@dataclass
class Position:
    ticker: str
    entry_date: date
    entry_price: float = 0
    entry_shares: float = 0
    exit_date: date = None
    exit_price: float = 0
    exit_shares: float = 0
    stop_price: float = 0
    exit_reason: ExitReason = None
    highest_price: float = 0


class Portfolio:
    def __init__(
        self,
        name: Optional[str] = None,
        benchmark: str = None,
        setup: Dict = None,
        constraints: Dict = None,
        verbose: bool = False,
    ):
        self.name = name
        self.benchmark = benchmark
        self.verbose = verbose
        self.setup = setup
        self.cost = TransactionCost()

        if verbose:
            setup_for_display = make_json_serializable(self.setup)
            print(f"Portfolio setup: {json.dumps(setup_for_display, indent=4)}")

        # Portfolio state
        self.portfolio_value = setup.get("initial_value", 0)
        self.active_positions = setup.get(
            "initial_holdings", {}
        ).copy()  # {ticker: {date: Position}}
        self.capital = setup.get("initial_capital", 0)

        # Data
        self.universe, self.product_data = self._initialize_universe()
        self.open_prices, self.close_prices, self.volumes = (
            self._initialize_price_data()
        )

        self.constraints = Constraints(
            trailing_stop_loss_pct=self.setup.get("trailing_stop_loss_pct"),
            constraints=constraints,
            product_data=self.product_data,
        )

        # Trading history tracking
        self.portfolio_value_curve: Dict[date, float] = {}
        self.capital_curve: Dict[date, float] = {}
        self.holdings_history: Dict[date, Dict[str, float]] = {}
        self.signals_history: Dict[date, list[float]] = {}
        self.executed_plan_history: Dict[date, dict[str, int | str]] = {}

        """below are updated during trading instead of in _update_portfolio_state"""
        ##  {date: {ticker: [Position1, Position2]}}, this means a ticker can have multiple positions closed on the same date
        self.closed_positions: Dict[date, Dict[str, list[Position]]] = {}
        ## {date: {ticker: {shares: float, exit_price: float, transaction_costs: float, sell_proceeds: float}}}
        self.stop_loss_history: Dict[date, dict[str, float]] = {}
        self.sell_history: Dict[date, dict[str, float]] = {}
        ## {date: {ticker: {shares: float, entry_price: float, transaction_costs: float, purchase_proceeds: float}}}
        self.buy_history: Dict[date, dict[str, float]] = {}

    def set_name(self, name):
        self.name = name

    def _initialize_universe(self) -> Tuple[List[str], pd.DataFrame]:
        tickers = BenchmarkData().get_constituents(self.benchmark)
        if len(tickers) == 0:
            raise ValueError(f"No tickers found for benchmark: {self.benchmark}")
        product_data = ProductData().get_data(tickers)
        if len(product_data) == 0:
            raise ValueError(f"No product data found for any tickers")

        filtered_data = self._apply_universe_filters(product_data)
        universe = filtered_data.ticker.tolist()

        return universe, filtered_data

    def _apply_universe_filters(self, product_data: pd.DataFrame) -> pd.DataFrame:
        excluded_sectors = [
            sector.value for sector in self.setup.get("excluded_sectors", [])
        ]
        included_countries = [
            country.value for country in self.setup.get("included_countries", [])
        ]

        sector_filter = ~product_data.sector.isin(excluded_sectors)
        market_cap_filter = (
            product_data.marketCap >= self.setup.get("min_market_cap")
        ) & (product_data.marketCap <= self.setup.get("max_market_cap"))
        country_filter = product_data.country.isin(included_countries)

        combined_filter = sector_filter & market_cap_filter & country_filter
        return product_data[combined_filter]

    def _initialize_price_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        prices = PriceData().get_data(self.universe)
        if len(prices) == 0:
            raise ValueError(f"No price data found for any tickers")

        open_prices = prices["open"]
        open_prices.set_index(open_prices.Date, inplace=True)
        close_prices = prices["close"]
        close_prices.set_index(close_prices.Date, inplace=True)
        volumes = prices["volume"]
        volumes.set_index(volumes.Date, inplace=True)

        return open_prices, close_prices, volumes

    def get_universe(self) -> List[str]:
        return self.universe

    def get_prices(
        self,
        price_type: str,
        end_date: Optional[date] = None,
        start_date: Optional[date] = None,
        lookback_window: int = np.inf,
        lookahead_window: int = np.inf,
    ) -> pd.DataFrame:
        price_data = getattr(self, f"{price_type}_prices")
        return get_prices_by_dates(
            price_data, end_date, start_date, lookback_window, lookahead_window
        )

    def _process_trading_signals(
        self, trading_plan: Dict[str, int], executed_trading_plan: Dict[str, int]
    ) -> Tuple[Dict[str, Dict], List[str], Dict[str, int]]:
        if not trading_plan:
            return {}, [], {}

        sell_closed_positions = {}
        new_positions = []

        tickers = np.array(list(trading_plan.keys()))
        signals = np.array(list(trading_plan.values()))

        sell_tickers = tickers[signals == -1]

        for ticker in sell_tickers:
            if ticker in self.active_positions:
                sell_closed_positions[ticker] = self.active_positions[ticker]
            else:
                if executed_trading_plan[ticker] == 0:
                    executed_trading_plan[ticker] = "No short sell"

        new_positions = tickers[signals == 1].tolist()

        return sell_closed_positions, new_positions

    def trade(self, date: date, trading_plan: Dict[str, int]) -> bool:
        # mark to market
        open_prices = self.open_prices.loc[date]
        self._mark_portfolio_to_market(open_prices)

        executed_trading_plan = trading_plan.copy()
        # check max drawdown
        if self.constraints.trigger_max_drawdown(
            self.portfolio_value, self.portfolio_value_curve
        ):
            print("max drawdown triggered")
            self._update_portfolio_state(
                "close", date, trading_plan, executed_trading_plan
            )
            return True

        # update stuff
        self._update_capital_for_date(date)
        self._update_trailing_stop_loss(open_prices)

        # process stop losses
        stop_loss_closed_positions = self.constraints.check_stop_loss(
            active_positions=self.active_positions, price=open_prices
        )
        if stop_loss_closed_positions:
            sell_proceeds, transaction_entries = self._close_positions(
                close_reason=ExitReason.STOP_LOSS,
                closed_positions=stop_loss_closed_positions,
                date=date,
            )
            self.capital += sell_proceeds
            self.stop_loss_history[date] = transaction_entries

        # process trading signals
        sell_closed_positions, new_positions = self._process_trading_signals(
            trading_plan, executed_trading_plan
        )

        # execute sell orders
        if sell_closed_positions:
            sell_proceeds, transaction_entries = self._close_positions(
                close_reason=ExitReason.SELL,
                closed_positions=sell_closed_positions,
                date=date,
                executed_trading_plan=executed_trading_plan,
            )
            self.capital += sell_proceeds
            self.sell_history[date] = transaction_entries

        # execute buy orders
        if new_positions:
            transaction_entries = self.constraints.allocate_capital_to_buy(
                capital=self.capital,
                portfolio_value=self.portfolio_value,
                new_positions=new_positions,
                allocation_method=self.setup.get("allocation_method"),
                prices=self.open_prices.loc[date, new_positions],
                volumes=self.volumes.loc[date, new_positions],
                cost_function=self.cost.calculate_transaction_costs,
            )
            if transaction_entries:
                remaining_capital, transaction_entries = self._open_positions(
                    date, transaction_entries, executed_trading_plan
                )
                self.capital = remaining_capital
                self.buy_history[date] = transaction_entries

        # update portfolio state with closing prices
        self._mark_portfolio_to_market(self.close_prices.loc[date])
        self._update_portfolio_state(
            type="update",
            date=date,
            trading_plan=trading_plan,
            executed_trading_plan=executed_trading_plan,
        )

        return False

    def _mark_portfolio_to_market(self, price: pd.Series) -> None:
        tickers = list(self.active_positions.keys())
        if not tickers:
            current_value = 0
        else:
            shares = np.array(
                [
                    np.sum([position.entry_shares for position in positions.values()])
                    for positions in self.active_positions.values()
                ]
            )
            prices = price[tickers].to_numpy()
            current_value = np.dot(shares, prices)

        self.portfolio_value = self.capital + current_value

    def _update_capital_for_date(self, date: date) -> None:
        """update capital based on growth settings"""
        growth_freq = self.setup.get("capital_growth_freq", "D")
        growth_amt = self.setup.get("new_capital_growth_amt", 0)
        growth_pct = self.setup.get("new_capital_growth_pct", 0)

        if growth_amt == 0 and growth_pct == 0:
            return 0

        if growth_amt != 0 and growth_pct != 0:
            raise ValueError("Cannot have both growth_amt and growth_pct")

        if growth_freq == "D":
            self.capital += growth_amt
            self.capital *= 1 + growth_pct
        else:
            period_ends = is_business_period_end(date)
            should_add_capital = False
            if growth_freq == "W" and period_ends["week"]:
                should_add_capital = True
            elif growth_freq == "M" and period_ends["month"]:
                should_add_capital = True
            elif growth_freq == "Q" and period_ends["quarter"]:
                should_add_capital = True
            elif growth_freq == "Y" and period_ends["year"]:
                should_add_capital = True

            if should_add_capital:
                self.capital += growth_amt
                self.capital *= 1 + growth_pct

    def _update_trailing_stop_loss(self, price: pd.Series) -> None:
        if not self.active_positions:
            return

        update_threshold = self.setup.get("trailing_update_threshold")
        stop_loss_pct = self.setup.get("trailing_stop_loss_pct")
        processed_tickers = []
        for ticker, positions in self.active_positions.items():
            if ticker in processed_tickers:
                continue
            current_price = price[ticker]
            current_highest = next(iter(positions.values())).highest_price

            if current_price / current_highest - 1 >= update_threshold:
                for position in positions.values():
                    position.highest_price = current_price
                    position.stop_price = current_price * (1 - stop_loss_pct)
            processed_tickers.append(ticker)

    def _close_positions(
        self,
        close_reason: ExitReason,
        closed_positions: Dict[str, list[date]],
        date: date,
        executed_trading_plan: Dict[str, int] = None,
    ) -> Tuple[float, Dict[str, float]]:
        sell_proceeds = 0
        transaction_entries = {}
        positions_to_delete = []  # [(ticker, date)] pairs to delete

        if date not in self.closed_positions:
            self.closed_positions[date] = {}

        for ticker, dates in closed_positions.items():
            today_open_price = self.open_prices.loc[date, ticker]
            shares_to_sell = 0

            for d in dates:
                position = self.active_positions[ticker][d]
                position.exit_date = date
                position.exit_price = today_open_price
                position.exit_shares = position.entry_shares
                position.exit_reason = close_reason

                self.closed_positions[date][ticker] = self.closed_positions[date].get(
                    ticker, []
                ) + [position]
                shares_to_sell += position.entry_shares
                positions_to_delete.append((ticker, d))
            transaction_costs = self.cost.calculate_transaction_costs(
                shares={ticker: shares_to_sell},
                volume=self.volumes.loc[date, [ticker]],
                price=self.open_prices.loc[date, [ticker]],
            )
            sell_proceeds += (
                today_open_price * shares_to_sell - transaction_costs[ticker]
            )
            transaction_entries[ticker] = {
                "exit_shares": shares_to_sell,
                "exit_price": today_open_price,
                "transaction_costs": transaction_costs[ticker],
                "sell_proceeds": sell_proceeds,
                "exit_reason": close_reason.value,
            }

        for ticker, d in positions_to_delete:
            if close_reason == ExitReason.STOP_LOSS:
                executed_trading_plan[ticker] = "Stop loss"
            elif close_reason == ExitReason.MAX_DRAWDOWN:
                executed_trading_plan[ticker] = "Max drawdown"

            del self.active_positions[ticker][d]
            if len(self.active_positions[ticker]) == 0:
                del self.active_positions[ticker]

        return sell_proceeds, transaction_entries

    def _open_positions(
        self,
        date: date,
        transaction_entries: Dict[str, float],
        executed_trading_plan: Dict[str, int],
    ) -> Tuple[float, Dict[str, float]]:
        prices = self.open_prices.loc[date, transaction_entries.keys()]
        remaining_capital = self.capital
        transaction_costs = self.cost.calculate_transaction_costs(
            shares=transaction_entries,
            volume=self.volumes.loc[date, transaction_entries.keys()],
            price=prices,
        )

        unaffordable_tickers = []
        for ticker, shares in transaction_entries.items():
            if shares == 0:  # not enough capital to buy, signal is not executed
                unaffordable_tickers.append(ticker)
                continue

            current_price = prices[ticker]

            if ticker not in self.active_positions:
                self.active_positions[ticker] = {}
                highest_price = current_price
            else:  # note that the highest price and stop price is already updated in _update_trailing_stop_loss
                highest_price = next(
                    iter(self.active_positions[ticker].values())
                ).highest_price

            self.active_positions[ticker][date] = Position(
                ticker=ticker,
                entry_date=date,
                entry_price=current_price,
                entry_shares=shares,
                highest_price=highest_price,
                stop_price=highest_price
                * (1 - self.setup.get("trailing_stop_loss_pct")),
            )

            purchase_proceeds = shares * current_price - transaction_costs[ticker]
            transaction_entries[ticker] = {
                "entry_price": current_price,
                "entry_shares": shares,
                "transaction_costs": transaction_costs[ticker],
                "purchase_proceeds": purchase_proceeds,
            }
            remaining_capital -= purchase_proceeds

        for ticker in unaffordable_tickers:
            executed_trading_plan[ticker] = "Insufficient capital"
            del transaction_entries[ticker]

        return remaining_capital, transaction_entries

    def _update_portfolio_state(
        self,
        type: str,  # update or close
        date: date,
        trading_plan: Dict[str, int],
        executed_trading_plan: Dict[str, int] = None,
    ) -> None:
        if type == "close":
            closed_positions = {k: -abs(v) for k, v in self.holdings.items()}
            sell_proceeds, _ = self._close_positions(
                close_reason=ExitReason.MAX_DRAWDOWN,
                closed_positions=closed_positions,
                date=date,
                executed_trading_plan=executed_trading_plan,
            )
            self.capital += sell_proceeds
            self.portfolio_value += self.capital
            self.active_positions.clear()

        self.portfolio_value_curve[date] = self.portfolio_value
        self.capital_curve[date] = self.capital
        self.holdings_history[date] = {
            ticker: np.sum([position.entry_shares for position in positions.values()])
            for ticker, positions in self.active_positions.items()
        }
        self.signals_history[date] = trading_plan
        self.executed_plan_history[date] = executed_trading_plan

    def trade_batch(self, trading_plan: pd.DataFrame) -> Tuple[bool, List[date]]:
        actual_trading_dates = []
        for date in trading_plan.index:
            date_signals = trading_plan.loc[date]
            trading_plan_dict = date_signals.to_dict()
            trade_disabled = self.trade(date, trading_plan_dict)
            actual_trading_dates.append(date)  # we will want the liquidation date data
            # break
            if trade_disabled:
                return True, actual_trading_dates
        return False, actual_trading_dates
