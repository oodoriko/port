import json
from dataclasses import dataclass, field
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
    # below are used to reduce trading universe, different from exposure constraints
    min_market_cap: float = 0
    max_market_cap: float = float("inf")
    exclude_sectors: List[Sectors] = field(default_factory=list)
    include_countries: List[Countries] = field(
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
            "exclude_sectors": self.exclude_sectors,
            "include_countries": self.include_countries,
            "min_market_cap": self.min_market_cap,
            "max_market_cap": self.max_market_cap,
        }


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
        self.constraints = Constraints(constraints)
        if verbose:
            setup_for_display = make_json_serializable(self.setup)
            print(f"Portfolio setup: {json.dumps(setup_for_display, indent=4)}")

        # Portfolio state
        self.portfolio_value = setup.get("initial_value", 0)
        self.holdings = setup.get("initial_holdings", {}).copy()
        self.capital = setup.get("initial_capital", 0)

        # Data
        self.universe, self.product_data = self._initialize_universe()
        self.open_prices, self.close_prices, self.volumes = (
            self._initialize_price_data()
        )
        self._setup_constraints_data()

        # Trading history tracking
        self.holdings_history: Dict[str, Dict[str, float]] = {}
        self.trading_plan_history: Dict[str, Dict[str, int]] = {}
        self.transaction_history: Dict[str, Dict[str, float]] = {}
        self.trading_status: Dict[str, int] = {}
        self.capital_history: Dict[np.datetime64, float] = {}

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
        exclude_sectors = [
            sector.value for sector in self.setup.get("exclude_sectors", [])
        ]
        include_countries = [
            country.value for country in self.setup.get("include_countries", [])
        ]

        sector_filter = ~product_data.sector.isin(exclude_sectors)
        market_cap_filter = (
            product_data.marketCap >= self.setup.get("min_market_cap")
        ) & (product_data.marketCap <= self.setup.get("max_market_cap"))
        country_filter = product_data.country.isin(include_countries)

        combined_filter = sector_filter & market_cap_filter & country_filter
        return product_data[combined_filter]

    def _initialize_price_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        prices = PriceData().get_data(self.universe)
        if len(prices) == 0:
            raise ValueError(f"No price data found for any tickers")

        open_prices = prices["open"]
        open_prices.set_index(pd.to_datetime(open_prices.Date), inplace=True)
        close_prices = prices["close"]
        close_prices.set_index(pd.to_datetime(close_prices.Date), inplace=True)
        volumes = prices["volume"]
        volumes.set_index(pd.to_datetime(volumes.Date), inplace=True)

        return open_prices, close_prices, volumes

    def _setup_constraints_data(self) -> None:
        self.constraints.set_product_data(self.product_data)
        self.constraints.set_price(self.open_prices)
        self.constraints.set_volume(self.volumes)

    def get_universe(self) -> List[str]:
        return self.universe

    def get_prices(
        self,
        price_type: str,
        end_date: Optional[str] = None,
        start_date: Optional[str] = None,
        lookback_window: int = np.inf,
        lookahead_window: int = np.inf,
    ) -> pd.DataFrame:
        price_data = getattr(self, f"{price_type}_prices")
        return get_prices_by_dates(
            price_data, end_date, start_date, lookback_window, lookahead_window
        )

    def trade(
        self, date: np.datetime64, trades: List[int], trading_plan: Dict[str, int]
    ) -> None:
        if not self._can_execute_trades(trades):
            self.trading_status[date] = -1
            return

        self._update_capital_for_date(date)

        # Initialize trading state
        shares_to_be_traded = {}
        new_holdings_state = self.holdings.copy()
        executed_trading_plan = trading_plan.copy()

        # Process sell trades first, eventually will need to use constraint class
        self.capital += self._process_sell_trades(
            date=date,
            trading_plan=trading_plan,
            shares_to_be_traded=shares_to_be_traded,
            new_holdings_state=new_holdings_state,
            executed_trading_plan=executed_trading_plan,
        )

        # Process buy trades using constraint class
        # there is a chance nothing be bought, so we need to add the capital back
        self.capital = self.constraints.allocate_capital_to_buy(
            date=date,
            capital=self.capital,
            trading_plan=trading_plan,
            new_holdings_state=new_holdings_state,
            shares_to_be_traded=shares_to_be_traded,
            executed_trading_plan=executed_trading_plan,
            allocation_method=self.setup.get("allocation_method"),
        )

        # Update portfolio state
        self._update_portfolio_state(
            date, shares_to_be_traded, new_holdings_state, executed_trading_plan
        )

    def _can_execute_trades(self, trades: List[int]) -> bool:
        positions_size = (
            len(self.universe) if len(self.holdings) == 0 else len(self.holdings)
        )
        max_holdings = len(self.universe)

        return self.constraints.evaluate_trades(trades, positions_size, max_holdings)

    def _update_capital_for_date(self, date: str) -> None:
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

    def _process_sell_trades(
        self,
        date: np.datetime64,
        trading_plan: Dict[str, int],
        shares_to_be_traded: Dict[str, float],
        new_holdings_state: Dict[str, float],
        executed_trading_plan: Dict[str, int],
    ) -> None:
        sell_tickers = []
        sell_shares = []

        for ticker, signal in trading_plan.items():
            if signal == -1:
                if ticker in self.holdings:
                    shares_to_sell = self.holdings[ticker]
                    shares_to_be_traded[ticker] = -shares_to_sell
                    new_holdings_state.pop(ticker, None)
                    sell_tickers.append(ticker)
                    sell_shares.append(shares_to_sell)
                elif self.constraints.constraints.get("long_only"):
                    executed_trading_plan[ticker] = 0
                else:
                    raise NotImplementedError("i haven't think about short selling yet")

        if sell_tickers:
            sell_prices = self.open_prices.loc[date, sell_tickers]
            sell_proceeds = np.sum(sell_prices * sell_shares)
            return sell_proceeds
        return 0

    def _update_portfolio_state(
        self,
        date: np.datetime64,
        shares_to_be_traded: Dict[str, float],
        new_holdings_state: Dict[str, float],
        executed_trading_plan: Dict[str, int],
    ) -> None:
        self.trading_status[date] = 1 if shares_to_be_traded else 0
        self.trading_plan_history[date] = executed_trading_plan
        self.transaction_history[date] = shares_to_be_traded
        self.holdings_history[date] = new_holdings_state
        self.holdings = new_holdings_state
        self.capital_history[date] = self.capital

    def trade_batch(self, trading_plan: pd.DataFrame) -> None:
        for date in trading_plan.index:
            date_signals = trading_plan.loc[date]
            trading_plan_dict = date_signals.to_dict()
            trades = date_signals.tolist()
            self.trade(date, trades, trading_plan_dict)
