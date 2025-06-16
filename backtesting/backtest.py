from datetime import timedelta

import pandas as pd
from tqdm import tqdm

from backtesting.scenarios import Scenario
from portfolio.analytics import AdvancedPortfolioAnalytics, PortfolioAnalytics
from reporting.report import generate_simple_report
from strategies.strategy import vote_batch, vote_single_date


class Backtest:
    def __init__(
        self,
        scenario: Scenario,
        verbose: bool = False,
    ):
        if scenario.get_strategies() is None:
            raise ValueError("Strategies are not set in scenario")

        self.start_date = scenario.start_date
        self.end_date = scenario.end_date
        self.strategies = scenario.get_strategies()  # list of Strategy objects
        self.trading_dates = scenario.get_trading_dates()
        self.portfolio = scenario.get_portfolio()
        self.contains_filters = scenario.contains_filters
        self.verbose = verbose
        self.scenario = scenario

    def run(self):
        actual_trading_dates = []
        if self.verbose:
            print(f"Backtest starting... whomp whomp!")
            print(
                f"Total trading days: {len(self.trading_dates)}\n"
                f"Universe size: {len(self.portfolio.get_universe())}\n"
                f"Total strategies: {len(self.strategies)}\n"
                f"Starting in {self.start_date}\n"
                f"Ending in {self.end_date}"
            )

        # get data
        universe = self.portfolio.get_universe()
        max_lookback = max(strategy.min_window for strategy in self.strategies)
        data_start_date = self.start_date - timedelta(days=max_lookback)

        for date in tqdm(
            self.trading_dates,
            desc="Backtesting by date x strategy",
            unit="day",
            disable=not self.verbose,
        ):
            signals = {}

            # get trading plan
            for strategy in self.strategies:
                price_type = strategy.price_type
                # price include today's price, make sure to exclude it in signal generation
                prices = self.portfolio.get_prices(
                    price_type, end_date=date, start_date=data_start_date
                )
                signal = strategy.generate_signals_single_date(prices.loc[:, universe])
                signals[strategy.name.value] = signal
            trades = vote_single_date(pd.DataFrame(signals), self.contains_filters)
            trading_plan = dict(zip(universe, trades))
            trade_disabled = self.portfolio.trade(date, trading_plan)
            actual_trading_dates.append(date)
            if trade_disabled:
                print(f"Hit max drawdown on {date}")
                break
        if self.verbose:
            print("Ding ding ding! Backtest completed!")
        self.scenario.set_actual_trading_dates(actual_trading_dates)

    def run_batch(self, verbose: bool = True):
        if verbose:
            print(f"Backtest starting... swoosh!")
            print(
                f"Universe size: {len(self.portfolio.get_universe())}\n"
                f"Total trading days: {len(self.trading_dates)}\n"
                f"Total strategies: {len(self.strategies)}\n"
                f"Starting in {self.start_date}\n"
                f"Ending in {self.end_date}"
            )
        universe = self.portfolio.get_universe()
        price_type = "close"  # Use close price for all strategies in batch mode

        # Generate signals for all dates
        max_lookback = max(strategy.min_window for strategy in self.strategies)
        data_start_date = self.start_date - timedelta(days=max_lookback)

        # price include today's price, make sure to exclude it in signal generation
        prices = self.portfolio.get_prices(
            price_type, start_date=data_start_date, end_date=self.end_date
        )[universe]

        run_start_date = prices.loc[self.start_date :, :].index[
            0
        ]  # start date may fall on a weekend, we find the closest biz date that has price data as run start date
        data_r = prices.reset_index()
        run_start_index = data_r[data_r["Date"] == run_start_date].index[0]
        del data_r

        signals = []
        for strategy in tqdm(
            self.strategies,
            desc="Backtesting by strategy",
            unit="strategy",
            disable=not verbose,
        ):
            signal = strategy.generate_signals_batch(prices, run_start_index)
            signals.append(signal)
        trading_plan = vote_batch(signals, self.contains_filters)

        trade_disabled, actual_trading_dates = self.portfolio.trade_batch(trading_plan)
        if trade_disabled:
            print(f"Hit max drawdown on {self.trading_dates[-1]}")

        if verbose:
            print("Backtest completed!")

        self.scenario.set_actual_trading_dates(actual_trading_dates)

    def generate_analytics(self, rf=0.02, bmk_returns=0.1):
        return PortfolioAnalytics(
            self.portfolio,
            rf=rf,
            bmk_returns=bmk_returns,
            trading_dates=self.scenario.get_actual_trading_dates(),
        )

    def generate_advanced_analytics(self, rf=0.02, bmk_returns=0.1):
        return AdvancedPortfolioAnalytics(
            self.portfolio,
            rf=rf,
            bmk_returns=bmk_returns,
            trading_dates=self.scenario.get_actual_trading_dates(),
        )

    def generate_report(self, rf=0.02, bmk_returns=0.1, filename=None):
        analytics = self.generate_advanced_analytics(rf=rf, bmk_returns=bmk_returns)
        return generate_simple_report(
            analytics,
            start_date=self.start_date,
            end_date=self.end_date,
            rf=rf,
            bmk_returns=bmk_returns,
            filename=filename,
        )

    def get_portfolio(self):
        return self.portfolio
