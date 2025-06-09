import numpy as np
import pandas as pd
from tqdm import tqdm

from backtesting.scenarios import Scenario
from config import DEFAULT_BACKTEST_PARAMS, StrategyTypes
from portfolio.portfolio import Portfolio
from reporting.portfolio_analytics import PortfolioAnalytics
from reporting.report_generator import generate_report
from strategies.strategy import Strategy, plurality_voting_batch, plurality_voting_batch_batch


class Backtest:
    def __init__(
        self,
        portfolio: Portfolio,
        start_date: str = DEFAULT_BACKTEST_PARAMS["start_date"],
        end_date: str = DEFAULT_BACKTEST_PARAMS["end_date"],
        strategies: list[StrategyTypes] = DEFAULT_BACKTEST_PARAMS["strategies"],
    ):
        self.portfolio = portfolio
        self.start_date = start_date
        self.end_date = end_date
        self.strategies = strategies
        self.trading_dates = list(
            np.intersect1d(portfolio.open_prices.index, pd.date_range(start_date, end_date))
        )

    @classmethod
    def from_scenario(cls, scenario: Scenario) -> "Backtest":
        portfolio = Portfolio(
            name=scenario.name,
            benchmark=scenario.benchmark,
            constraints=scenario.constraints,
            additional_setup=scenario.additional_setup,
        )

        instance = cls(
            portfolio=portfolio,
            start_date=scenario.start_date,
            end_date=scenario.end_date,
            strategies=scenario.strategies,
        )

        instance.scenario = scenario
        return instance

    def get_portfolio(self) -> Portfolio:
        return self.portfolio

    def get_trading_dates(self) -> pd.DatetimeIndex:
        return self.trading_dates

    def get_strategies(self) -> list[StrategyTypes]:
        return [strategy.name for strategy in self.strategies]

    def run(self):
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
        strategies = [Strategy.create(s) for s in self.strategies]
        max_lookback = max(strategy.min_window for strategy in strategies)
        data_start_date = pd.Timestamp(self.start_date) - pd.Timedelta(days=max_lookback)

        for date in tqdm(self.trading_dates, desc="Backtesting by date x strategy", unit="day"):
            signals = {}

            # get trading plan
            for strategy in strategies:
                price_type = strategy.price_type
                # price include today's price, make sure to exclude it in signal generation
                prices = self.portfolio.get_prices(
                    price_type, end_date=date, start_date=data_start_date
                )
                signal = strategy.generate_signals_single_date(prices.loc[:, universe])
                signals[strategy.name.value] = signal
            trades = plurality_voting_batch(pd.DataFrame(signals)).Signal.tolist()
            trading_plan = dict(zip(universe, trades))
            self.portfolio.trade(date, trades, trading_plan)

        print("Ding ding ding! Backtest completed!")

    def run_batch(self):
        print(f"Backtest starting... swoosh!")
        print(
            f"Universe size: {len(self.portfolio.get_universe())}\n"
            f"Total trading days: {len(self.trading_dates)}\n"
            f"Total strategies: {len(self.strategies)}\n"
            f"Starting in {self.start_date}\n"
            f"Ending in {self.end_date}"
        )
        universe = self.portfolio.get_universe()
        strategies = [Strategy.create(s) for s in self.strategies]
        price_type = "close"  # Use close price for all strategies in batch mode
        
        # Generate signals for all dates
        max_lookback = max(strategy.min_window for strategy in strategies)
        data_start_date = pd.Timestamp(self.start_date) - pd.Timedelta(days=max_lookback)

        # price include today's price, make sure to exclude it in signal generation
        prices = self.portfolio.get_prices(price_type, start_date=data_start_date, end_date=self.end_date)[universe]

        run_start_date = prices.loc[self.start_date:, :].index[0] # start date may fall on a weekend, we find the closest biz date that has price data as run start date
        data_r = prices.reset_index()
        run_start_index = data_r[data_r["Date"] == run_start_date].index[0]
        del data_r

        signals = []
        for strategy in tqdm(strategies, desc="Backtesting by strategy", unit="strategy"):
            signal = strategy.generate_signals_batch(prices, run_start_index)
            signals.append(signal)
        trading_plan= plurality_voting_batch_batch(signals)

        self.portfolio.trade_batch(trading_plan)
        print("Backtest completed!")

    def generate_analytics(self, rf=0.02, bmk_returns=0.1):
        return PortfolioAnalytics(
            self.portfolio,
            self.start_date,
            self.end_date,
            rf=rf,
            bmk_returns=bmk_returns,
        )

    def generate_report(self, rf=0.02, bmk_returns=0.1, filename=None):
        # analytics = self.generate_analytics(rf=rf, bmk_returns=bmk_returns)
        return generate_report(self, rf=rf, bmk_returns=bmk_returns, filename=filename)
