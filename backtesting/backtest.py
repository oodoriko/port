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
            f"Total trading days: {len(self.trading_dates)}\nUniverse size: {len(self.portfolio.get_universe())}\n Starting in {self.start_date}\n Ending in {self.end_date}"
        )

        # get data
        universe = self.portfolio.get_universe()
        strategies = [Strategy.create(s) for s in self.strategies]
        max_lookback = max(strategy.min_window for strategy in strategies)
        for date in tqdm(self.trading_dates, desc="Backtesting", unit="day"):
            signals = {}

            # get trading plan
            for strategy in strategies:
                price_type = strategy.price_type
                prices = self.portfolio.get_prices(
                    price_type, end_date=date, lookback_window=max_lookback # uses prev close price
                )
                signal = strategy.generate_signals_single(prices.loc[:, universe])
                signals[strategy.name.value] = signal
            trades = plurality_voting_batch(pd.DataFrame(signals)).Signal.tolist()
            trading_plan = dict(zip(universe, trades))
            self.portfolio.trade(date, trades, trading_plan)

        print("Ding ding ding! Backtest completed!")

    def run_batch(self):
        """
        Batch version of run() that produces identical results.
        Currently uses date-by-date processing to ensure correctness.
        Future optimization: modify generate_signals_batch methods to handle chronological windowing.
        """
        print(f"Backtest starting... swoosh!")
        print(
            f"Total trading days: {len(self.trading_dates)}\nUniverse size: {len(self.portfolio.get_universe())}\n Starting in {self.start_date}\n Ending in {self.end_date}"
        )

        universe = self.portfolio.get_universe()
        strategies = [Strategy.create(s) for s in self.strategies]
        price_type = "close"  # Use close price for all strategies in batch mode
        
        # Generate signals for all dates
        all_trading_plans = {}
        
        for date in self.trading_dates:
            # Generate signals for this date using the same logic as run()
            signals = {}
            for strategy in strategies:
                prices = self.portfolio.get_prices(
                    price_type, end_date=date, lookback_window=strategy.min_window
                ).loc[:, universe]
                signal = strategy.generate_signals_single(prices)
                signals[strategy.name.value] = signal
            
            # Apply plurality voting and create trading plan
            trades = plurality_voting_batch(pd.DataFrame(signals)).Signal.tolist()
            trading_plan = dict(zip(universe, trades))
            all_trading_plans[date] = trading_plan
        
        # Convert to DataFrame and execute batch trading
        trading_plan_df = pd.DataFrame.from_dict(all_trading_plans, orient='index')
        trading_plan_df.index = pd.to_datetime(trading_plan_df.index)
        
        self.portfolio.trade_batch(trading_plan_df)
        print("Backtest completed!")

    def generate_analytics(self, rf=0.02, bmk_returns=0.1):
        return PortfolioAnalytics(
            self.portfolio,
            self.start_date,
            self.end_date,
            rf=rf,
            bmk_returns=bmk_returns,
        )
        # self.metrics = self.analytics.calculate_metrics()
        # self.holdings_summary = self.analytics.holdings()

    def generate_report(self, rf=0.02, bmk_returns=0.1, filename=None):
        # analytics = self.generate_analytics(rf=rf, bmk_returns=bmk_returns)
        return generate_report(self, rf=rf, bmk_returns=bmk_returns, filename=filename)
