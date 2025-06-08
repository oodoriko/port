import pandas as pd
from tqdm import tqdm

from backtesting.scenarios import Scenario
from config import DEFAULT_BACKTEST_PARAMS, StrategyTypes
from portfolio.portfolio import Portfolio
from strategies.strategy import Strategy, plurality_voting_batch


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
        self.trading_dates = pd.bdate_range(start=start_date, end=end_date, freq="B")

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

    def run(self):
        print(f"Backtest starting... whomp whomp!")
        print(
            f"Total trading days: {len(self.trading_dates)}\nUniverse size: {len(self.portfolio.get_universe())}\n Starting in {self.start_date}\n Ending in {self.end_date}"
        )

        # get data
        universe = self.portfolio.get_universe()

        for date in tqdm(self.trading_dates, desc="Backtesting", unit="day"):
            signals = {}

            # get trading plan
            for strategy_name in self.strategies:
                strategy = Strategy.create(strategy_name)
                price_type = strategy.price_type
                min_window = strategy.min_window
                prices = self.portfolio.get_prices_by_dates(
                    price_type, end_date=date, lookback_window=min_window
                )
                signal = strategy.generate_signals_single(prices.loc[:, universe])
                signals[strategy.name.value] = signal
            trades = plurality_voting_batch(pd.DataFrame(signals)).Signal.tolist()
            trading_plan = dict(zip(universe, trades))
            self.portfolio.trade(date, trades, trading_plan)

        print("Ding ding ding! Backtest completed!")

    def generate_report(self, rf=0.02, bmk_returns=0.1, filename=None):
        self.portfolio.generate_analytics()
        return self.portfolio.generate_report(rf=rf, bmk_returns=bmk_returns, filename=filename)

    def get_portfolio(self) -> Portfolio:
        return self.portfolio

    def get_trading_dates(self) -> pd.DatetimeIndex:
        return self.trading_dates

    def get_strategies(self) -> list[StrategyTypes]:
        return [strategy.name for strategy in self.strategies]
