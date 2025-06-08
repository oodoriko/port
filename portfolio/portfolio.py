from collections import defaultdict

import numpy as np
import pandas as pd

from config import INITIAL_SETUP, Benchmarks
from data.data import BenchmarkData, PriceData, ProductData
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
        initial_holdings = additional_setup.get("initial_holdings", {})
        self.holdings = {k: v for k, v in initial_holdings.items()}
        # self.capital = additional_setup.get("initial_capital", 0), going to assume i have unlimited capital

        self.universe, self.product_data = self.get_universe_data()
        self.populate_prices()

        self.holdings_history = {}
        self.trades_history = {}  # weights and trades are the same thing here {key: [plan1, plan2]}
        self.portfolio_value_history = {}
        self.transaction_cost_history = {}
        self.pnl_history = {}

        # hard constraint to avoid selling all positions or buying the benchmark
        self.trades_status = {}

        # for reporting
        self.analytics = None
        self.metrics = {}
        self.holdings_summary = {}

    def get_universe_data(self) -> tuple[list[str], pd.DataFrame]:
        tickers = BenchmarkData().get_constituents(self.benchmark)
        product_data = ProductData().get_data(tickers)

        # filter tickers by setup constraints
        exclude_sectors_str = [sector.value for sector in INITIAL_SETUP["exclude_sectors"]]
        include_countries_str = [country.value for country in INITIAL_SETUP["include_countries"]]

        filter = (
            (~product_data.sector.isin(exclude_sectors_str))
            & (product_data.marketCap >= INITIAL_SETUP["min_market_cap"])
            & (product_data.marketCap <= INITIAL_SETUP["max_market_cap"])
            & (product_data.country.isin(include_countries_str))
        )
        product_data = product_data[filter]
        universe = product_data.ticker.tolist()
        return universe, product_data

    def populate_prices(self) -> None:
        prices = PriceData().get_data(self.universe)
        self.open_prices = prices["open"]
        self.close_prices = prices["close"]
        self.volumes = prices["volume"]

        self.open_prices.set_index(pd.to_datetime(self.open_prices.Date), inplace=True)
        self.close_prices.set_index(pd.to_datetime(self.close_prices.Date), inplace=True)
        self.volumes.set_index(pd.to_datetime(self.volumes.Date), inplace=True)

    # getters
    def get_universe(self) -> list[str]:
        return self.universe

    def get_prices(self, type: str) -> pd.DataFrame:
        if type not in ["open", "close", "volume"]:
            raise ValueError(f"Invalid price type: {type}, available types: open, close, volume")
        if type == "open":
            return self.open_prices
        if type == "close":
            return self.close_prices
        if type == "volume":
            return self.volumes

    def get_prices_by_dates(
        self,
        type: str,
        end_date: str = None,
        start_date: str = None,
        lookback_window: int = np.inf,
        lookahead_window: int = np.inf,
    ) -> pd.DataFrame:
        if type not in ["open", "close", "volume"]:
            raise ValueError(f"Invalid price type: {type}, choose from: open, close, volume")
        prices = self.get_prices(type)

        # window is easier bc i don't have to get exchange open dates
        # exclude current day to avoid lookahead bias
        if lookback_window != np.inf or lookahead_window != np.inf:
            if lookback_window != np.inf:
                return prices[prices.index < end_date].iloc[-lookback_window:]
            elif lookahead_window != np.inf:
                return prices[prices.index > start_date].iloc[:lookahead_window]
            return prices
        return prices[(prices.index >= start_date) & (prices.index <= end_date)]

    # operational
    def trade(self, date, trades: list[int], trades_plan: dict[str, int]) -> None:
        execute_trades = self.constraints.evaluate_trades(
            trades,
            positions_size=len(self.universe) if len(self.holdings) == 0 else len(self.holdings),
            max_holdings=len(self.universe),  # because we started with no holdings
        )
        if not execute_trades:
            print(f"Trades not executed for {date} because of constraints")
            self.trades_status[date] = 0
            return

        today_open_prices = self.get_prices_by_dates("open", start_date=date, end_date=date)
        shares = {}
        for ticker, signal in trades_plan.items():
            # always sell all, buy 1, never short
            if not self.allow_short and signal == -1 and ticker not in self.holdings.keys():
                trades_plan[ticker] = -1
                continue
            if signal == 1:
                shares[ticker] = 1
                self.holdings[ticker] = self.holdings.get(ticker, 0) + 1
            if signal == -1:
                shares[ticker] = -1 * self.holdings[ticker]
                del self.holdings[ticker]

        # calculate pnl and transaction cost
        pnl = self.calculate_pnl(today_open_prices, shares)
        transaction_cost = self.cost.calculate_transaction_costs(
            shares,
            volume=self.get_prices_by_dates("volume", end_date=date, lookback_window=1),
            price=self.get_prices_by_dates("open", start_date=date, end_date=date),
        )
        self.portfolio_value = self.calculate_portfolio_value(today_open_prices)

        # update portfolio
        self.holdings_history[date] = list(self.holdings.keys())
        self.trades_status[date] = 1 if not len(shares) > 0 else 0
        self.trades_history[date] = trades_plan
        self.portfolio_value_history[date] = self.portfolio_value
        self.transaction_cost_history[date] = transaction_cost
        self.pnl_history[date] = pnl

    def calculate_pnl(self, prices: pd.DataFrame, shares: dict[str, float]) -> float:
        if prices.empty:
            return 0

        pnl = sum([val * prices[ticker] for ticker, val in shares.items()])
        if isinstance(pnl, pd.Series):
            return pnl.values[0]
        return 0

    def calculate_portfolio_value(self, prices: pd.DataFrame) -> float:
        if prices.empty:
            return 0

        portfolio_value = sum([val * prices[ticker] for ticker, val in self.holdings.items()])
        if isinstance(portfolio_value, pd.Series):
            return portfolio_value.values[0]
        return 0

    def generate_analytics(self, rf=0.02, bmk_returns=0.1) -> None:
        self.analytics = PortfolioAnalytics(
            self.portfolio_value_history,
            self.trades_history,
            self.trades_status,
            self.product_data,
            self.holdings_history,
        )
        self.metrics = self.analytics.performance(rf=rf, bmk_returns=bmk_returns)
        self.holdings_summary = self.analytics.holdings()

    def generate_report(self, rf=0.02, bmk_returns=0.1, filename=None) -> str:
        if self.analytics is None:
            self.generate_analytics(rf=rf, bmk_returns=bmk_returns)
        return generate_report(self, rf=rf, bmk_returns=bmk_returns, filename=filename)
