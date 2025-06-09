from collections import defaultdict

import numpy as np
import pandas as pd

from config import INITIAL_SETUP, Benchmarks
from data.data import BenchmarkData, PriceData, ProductData, get_prices_by_dates
from portfolio.constraints import Constraints
from portfolio.cost import TransactionCost
from reporting.portfolio_analytics import PortfolioAnalytics
from reporting.report_generator import generate_report


class Portfolio:
    def __init__(
        self,
        name=None,
        benchmark=Benchmarks.SP500,
        constraints={},
        additional_setup=INITIAL_SETUP,
    ):
        self.name = name
        self.benchmark = benchmark
        self.setup = additional_setup
        self.constraints = Constraints(constraints)
        self.cost = TransactionCost()

        self.allow_short = additional_setup.get("allow_short", False)
        self.portfolio_value = additional_setup.get("initial_capital", 0)
        self.holdings = additional_setup.get("initial_holdings", {}).copy()
        # self.capital = additional_setup.get("initial_capital", 0), going to assume i have unlimited capital
        self.universe, self.product_data = self.get_data()
        self.open_prices, self.close_prices, self.volumes = self.get_historical_prices()

        self.holdings_history = {}  # {date: {ticker: shares, ...}}
        self.trading_history = {}  # {date: [1, 0, -1, 0, 1]} => trade action
        self.transaction_history = {}  # {date: {ticker: shares, ...}}
        self.trading_status = {}  # keeping record of days traded/not traded/cancelled

    def get_data(self) -> tuple[list[str], pd.DataFrame]:
        tickers = BenchmarkData().get_constituents(self.benchmark)
        product_data = ProductData().get_data(tickers)

        # filter tickers by setup constraints
        exclude_sectors_str = [sector.value for sector in self.setup["exclude_sectors"]]
        include_countries_str = [country.value for country in self.setup["include_countries"]]

        filter = (
            (~product_data.sector.isin(exclude_sectors_str))
            & (product_data.marketCap >= self.setup["min_market_cap"])
            & (product_data.marketCap <= self.setup["max_market_cap"])
            & (product_data.country.isin(include_countries_str))
        )
        product_data = product_data[filter]
        universe = product_data.ticker.tolist()
        return universe, product_data

    def get_historical_prices(self) -> pd.DataFrame:
        prices = PriceData().get_data(self.universe)
        open_prices = prices["open"]
        close_prices = prices["close"]
        volumes = prices["volume"]

        open_prices.set_index(pd.to_datetime(open_prices.Date), inplace=True)
        close_prices.set_index(pd.to_datetime(close_prices.Date), inplace=True)
        volumes.set_index(pd.to_datetime(volumes.Date), inplace=True)
        return open_prices, close_prices, volumes

    def get_universe(self) -> list[str]:
        return self.universe

    def get_prices(
        self,
        type: str,
        end_date: str = None,
        start_date: str = None,
        lookback_window: int = np.inf,
        lookahead_window: int = np.inf,
    ) -> pd.DataFrame:
        if type not in ["open", "close", "volume"]:
            raise ValueError(f"Invalid price type: {type}, available types: open, close, volume")
        var_name = f"{type}_prices"
        return get_prices_by_dates(
            getattr(self, var_name), end_date, start_date, lookback_window, lookahead_window
        )

    def trade(self, date, trades: list[int], trading_plan: dict[str, int]) -> None:
        execute_trades = self.constraints.evaluate_trades(
            trades,
            positions_size=len(self.universe) if len(self.holdings) == 0 else len(self.holdings),
            max_holdings=len(self.universe),  # because we started with no holdings
        )
        if not execute_trades:
            print(f"Trades not executed for {date} because of constraints")
            self.trading_status[date] = -1
            return

        shares = {}
        new_holdings = self.holdings.copy()
        # Create a copy of trading_plan to avoid modifying the original
        executed_trading_plan = trading_plan.copy()
        
        for ticker, signal in trading_plan.items():
            # always sell all, buy 1, never short
            if signal == 1:
                shares[ticker] = 1
                new_holdings[ticker] = new_holdings.get(ticker, 0) + 1
            if signal == -1:
                if ticker in self.holdings:
                    shares[ticker] = -1 * self.holdings[ticker]
                    del new_holdings[ticker]
                elif not self.allow_short:
                    # Don't modify the original trading_plan, modify the copy instead
                    executed_trading_plan[ticker] = 0

        self.trading_status[date] = 1 if len(shares) > 0 else 0
        self.trading_history[date] = executed_trading_plan
        self.transaction_history[date] = shares
        self.holdings_history[date] = new_holdings
        self.holdings = new_holdings

    def trade_batch(self, trading_plan: pd.DataFrame) -> None:
        for date in trading_plan.index:
            date_signals = trading_plan.loc[date]
            trading_plan_dict = {ticker: signal for ticker, signal in date_signals.items()}
            trades = date_signals.tolist()
            self.trade(date, trades, trading_plan_dict)


