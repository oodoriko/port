from collections import defaultdict

import numpy as np
import pandas as pd

from config import INITIAL_SETUP, Benchmarks
from data.data import BenchmarkData, PriceData, ProductData
from portfolio.constraints import Constraints
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
        self.benchmark = benchmark
        self.name = name
        self.setup = additional_setup
        self.set_up_constraints(constraints)
        self.transaction_cost = additional_setup.get("transaction_cost", 0.001)

        self.portfolio_value = additional_setup.get("initial_capital", 0)
        self.holdings = additional_setup.get("initial_holdings", [])
        # self.capital = additional_setup.get("initial_capital", 0), going to assume i have unlimited capital
        self.populate_universe()
        self.populate_prices()

        self.watchlist = [ticker for ticker in self.universe if ticker not in self.holdings]

        self.holdings_history = {}
        self.trades_history = (
            {}
        )  # weights and trades are the same thing here, dict with keyed by date, value the plan
        self.portfolio_value_history = {}

        """use this status to keep track of unexecuted trades plan,
        only needed bc current trades are buy all or sell all and signals are
        all technical. there is chance of selling the whole portfolio or buying
        the whole benchmark in a extended bull/bear market.
        
        when i have more strategies e.g. fundamental and trades on weights diff, i do not
        have to use this keep track of trades status, weights are automatically adjusted by
        constraints"""
        self.trades_status = {}

        self.analytics = None
        self.metrics = {}
        self.holdings_summary = {}

    def set_up_constraints(self, constraints):
        if constraints is not None:
            self.constraints = Constraints(constraints)

    def populate_universe(self):
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
        self.product_data = product_data[filter]
        self.universe = self.product_data.ticker.tolist()

    def populate_prices(self):
        prices = PriceData().get_data(self.universe)
        self.open_prices = prices["open"]
        self.close_prices = prices["close"]
        self.volumes = prices["volume"]

        self.open_prices.set_index(pd.to_datetime(self.open_prices.Date), inplace=True)
        self.close_prices.set_index(pd.to_datetime(self.close_prices.Date), inplace=True)
        self.volumes.set_index(pd.to_datetime(self.volumes.Date), inplace=True)

    # getters
    def get_universe(self):
        return self.universe

    def get_prices(self, type: str):
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
        date: str = None,
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
        if start_date is None and end_date is None:
            if lookback_window != np.inf:
                return prices[prices.index < date].iloc[-lookback_window:]
            elif lookahead_window != np.inf:
                return prices[prices.index > date].iloc[:lookahead_window]
            return prices
        return prices[(prices.index >= start_date) & (prices.index <= end_date)]

    # operational
    def trade(self, date, trades_plan: dict[str, int]):
        execute_trades = self.constraints.evaluate_trades(
            trades_plan,
            positions_size=len(self.universe) if len(self.holdings) == 0 else len(self.holdings),
            max_holdings=len(self.universe),  # because we started with no holdings
        )
        if not execute_trades:
            self.trades_status[date] = 0
            return

        actions = defaultdict(list)
        for ticker, signal in trades_plan.items():
            actions[signal].append(ticker)

        sell_positions = actions[-1]
        buy_positions = actions[1]

        sell_proceed = self.calculate_sell_proceed(sell_positions, date)
        buy_cost = self.calculate_buy_cost(buy_positions, date)

        # update portfolio
        new_holdings = [
            ticker for ticker in self.holdings if ticker not in sell_positions
        ] + buy_positions
        self.holdings = new_holdings
        self.holdings_history[date] = self.holdings

        self.watchlist = [ticker for ticker in self.universe if ticker not in new_holdings]

        self.trades_status[date] = 1
        self.trades_history[date] = trades_plan
        self.portfolio_value_history[date] = self.calculate_portfolio_value(sell_proceed - buy_cost)

    def calculate_sell_proceed(self, sell_positions, date):
        prices = self.get_prices_by_dates(
            "open", start_date=date, end_date=date, lookahead_window=1
        )  # today open price

        transaction_cost = self.transaction_cost
        if prices.empty:
            return 0
        sell_proceed = prices[sell_positions].iloc[0].sum() * (1 - transaction_cost)
        return sell_proceed

    def calculate_buy_cost(self, buy_positions, date):
        prices = self.get_prices_by_dates(
            "open", start_date=date, end_date=date, lookahead_window=1
        )  # today open price
        transaction_cost = self.transaction_cost
        if prices.empty:
            return 0
        buy_cost = prices[buy_positions].iloc[0].sum() * (1 + transaction_cost)
        return buy_cost

    def calculate_portfolio_value(self, incremental):
        return self.portfolio_value + incremental

    def generate_analytics(self, rf=0.02, bmk_returns=0.1):
        self.analytics = PortfolioAnalytics(
            self.portfolio_value_history,
            self.trades_history,
            self.trades_status,
            self.product_data,
        )
        self.metrics = self.analytics.performance(rf=rf, bmk_returns=bmk_returns)
        self.holdings_summary = self.analytics.holdings()

    def generate_report(self, rf=0.02, bmk_returns=0.1, filename=None):
        if self.analytics is None:
            self.generate_analytics(rf=rf, bmk_returns=bmk_returns)
        return generate_report(self, rf=rf, bmk_returns=bmk_returns, filename=filename)
