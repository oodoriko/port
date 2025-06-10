from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from config import INITIAL_SETUP, SIMPLE_CONSTRAINTS, Benchmarks
from data.data import BenchmarkData, PriceData, ProductData, get_prices_by_dates
from portfolio.constraints import Constraints
from portfolio.cost import TransactionCost
from portfolio.utils import is_business_period_end


class Portfolio:
    def __init__(
        self,
        name: Optional[str] = None,
        benchmark: Benchmarks = Benchmarks.SP500,
        constraints: Dict = SIMPLE_CONSTRAINTS,
        additional_setup: Dict = INITIAL_SETUP,
    ):
        self.name = name
        self.benchmark = benchmark
        self.setup = additional_setup
        self.cost = TransactionCost()
        self.constraints = Constraints(constraints)

        # Portfolio state
        self.portfolio_value = 0
        self.holdings = additional_setup.get("initial_holdings", {}).copy()
        self.capital = additional_setup.get("initial_capital", 0)

        # Data
        self.universe, self.product_data = self._initialize_universe()
        self.open_prices, self.close_prices, self.volumes = (
            self._initialize_price_data()
        )
        self._setup_constraints_data()

        # Trading history tracking
        self.holdings_history: Dict[str, Dict[str, float]] = {}
        self.trading_history: Dict[str, Dict[str, int]] = {}
        self.transaction_history: Dict[str, Dict[str, float]] = {}
        self.trading_status: Dict[str, int] = {}

    def _initialize_universe(self) -> Tuple[List[str], pd.DataFrame]:
        tickers = BenchmarkData().get_constituents(self.benchmark)
        product_data = ProductData().get_data(tickers)

        filtered_data = self._apply_universe_filters(product_data)
        universe = filtered_data.ticker.tolist()

        return universe, filtered_data

    def _apply_universe_filters(self, product_data: pd.DataFrame) -> pd.DataFrame:
        exclude_sectors = [
            sector.value for sector in self.constraints.constraints["exclude_sectors"]
        ]
        include_countries = [
            country.value
            for country in self.constraints.constraints["include_countries"]
        ]

        sector_filter = ~product_data.sector.isin(exclude_sectors)
        market_cap_filter = (
            product_data.marketCap >= self.constraints.constraints["min_market_cap"]
        ) & (product_data.marketCap <= self.constraints.constraints["max_market_cap"])
        country_filter = product_data.country.isin(include_countries)

        combined_filter = sector_filter & market_cap_filter & country_filter
        return product_data[combined_filter]

    def _initialize_price_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        prices = PriceData().get_data(self.universe)

        open_prices = self._prepare_price_dataframe(prices["open"])
        close_prices = self._prepare_price_dataframe(prices["close"])
        volumes = self._prepare_price_dataframe(prices["volume"])

        return open_prices, close_prices, volumes

    def _prepare_price_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        df_copy = df.copy()
        df_copy.set_index(pd.to_datetime(df_copy.Date), inplace=True)
        return df_copy

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
        if price_type not in ["open", "close", "volume"]:
            raise ValueError(
                f"Invalid price type: {price_type}, available types: open, close, volume"
            )

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
        new_holdings = self.holdings.copy()
        executed_trading_plan = trading_plan.copy()

        # Process sell trades first
        self._process_sell_trades(
            date, trading_plan, shares_to_be_traded, new_holdings, executed_trading_plan
        )

        # Process buy trades
        self.capital = self.constraints.allocate_capital_to_buy(
            date,
            self.capital,
            trading_plan,
            new_holdings,
            shares_to_be_traded,
            executed_trading_plan,
        )

        # Update portfolio state
        self._update_portfolio_state(
            date, shares_to_be_traded, new_holdings, executed_trading_plan
        )

    def trade_batch(self, trading_plan: pd.DataFrame) -> None:
        for date in trading_plan.index:
            date_signals = trading_plan.loc[date]
            trading_plan_dict = date_signals.to_dict()
            trades = date_signals.tolist()
            self.trade(date, trades, trading_plan_dict)

    def _can_execute_trades(self, trades: List[int]) -> bool:
        positions_size = (
            len(self.universe) if len(self.holdings) == 0 else len(self.holdings)
        )
        max_holdings = len(self.universe)

        return self.constraints.evaluate_trades(trades, positions_size, max_holdings)

    def _update_capital_for_date(self, date: str) -> None:
        """Update capital based on growth settings."""
        growth_freq = self.setup.get("capital_growth_freq", "D")
        growth_amt = self.setup.get("new_capital_growth_amt", 0)

        if growth_amt == 0:
            return

        if growth_freq == "D":
            self.capital += growth_amt
        else:
            period_ends = is_business_period_end(date)

            should_add_capital = False
            if growth_freq == "W" and period_ends["week"]:  # Weekly
                should_add_capital = True
            elif growth_freq == "M" and period_ends["month"]:  # Monthly
                should_add_capital = True
            elif growth_freq == "Q" and period_ends["quarter"]:  # Quarterly
                should_add_capital = True
            elif growth_freq == "Y" and period_ends["year"]:  # Yearly
                should_add_capital = True

            if should_add_capital:
                self.capital += growth_amt

        growth_pct = self.setup.get("new_capital_growth_pct", 0)
        if growth_pct > 0:
            initial_capital = self.setup.get("initial_capital", 0)
            self.capital = initial_capital * (1 + growth_pct)

    def _process_sell_trades(
        self,
        date: np.datetime64,
        trading_plan: Dict[str, int],
        shares_to_be_traded: Dict[str, float],
        new_holdings: Dict[str, float],
        executed_trading_plan: Dict[str, int],
    ) -> None:
        sell_tickers = []
        sell_shares = []

        for ticker, signal in trading_plan.items():
            if signal == -1:
                if ticker in self.holdings:
                    shares_to_sell = self.holdings[ticker]
                    shares_to_be_traded[ticker] = -shares_to_sell
                    new_holdings.pop(ticker, None)
                    sell_tickers.append(ticker)
                    sell_shares.append(shares_to_sell)
                elif self.constraints.constraints.get("long_only"):
                    executed_trading_plan[ticker] = 0

        # Calculate sell proceeds
        if sell_tickers:
            sell_prices = self.open_prices.loc[date, sell_tickers]
            sell_proceeds = np.sum(sell_prices * sell_shares)
            self.capital += sell_proceeds

    def _update_portfolio_state(
        self,
        date: np.datetime64,
        shares_to_be_traded: Dict[str, float],
        new_holdings: Dict[str, float],
        executed_trading_plan: Dict[str, int],
    ) -> None:
        """Update portfolio state after trading."""
        self.trading_status[date] = 1 if shares_to_be_traded else 0
        self.trading_history[date] = executed_trading_plan
        self.transaction_history[date] = shares_to_be_traded
        self.holdings_history[date] = new_holdings
        self.holdings = new_holdings
