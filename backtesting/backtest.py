from datetime import datetime, timedelta

import pandas as pd
from tqdm import tqdm

from config import DEFAULT_BACKTEST_PARAMS, StrategyTypes
from portfolio.portfolio import Portfolio
from strategies.strategy import Strategy, plurality_voting_batch


class Backtest:
    def __init__(
        self,
        portfolio: Portfolio,
        start_date: str = DEFAULT_BACKTEST_PARAMS["start_date"],
        end_date: str = DEFAULT_BACKTEST_PARAMS["end_date"],
        interval: str = DEFAULT_BACKTEST_PARAMS["interval"],
        strategies: list[StrategyTypes] = DEFAULT_BACKTEST_PARAMS["strategies"],
    ):
        self.portfolio = portfolio
        self.start_date = start_date
        self.end_date = end_date
        self.interval = interval
        self.strategies = [Strategy.create(strategy) for strategy in strategies]

    def run(self):
        start = datetime.strptime(self.start_date, "%Y-%m-%d")
        end = datetime.strptime(self.end_date, "%Y-%m-%d")
        dates = pd.bdate_range(start=start, end=end, freq="B")

        print(f"Backtest starting... whomp whomp!")
        print(f"Total trading days: {len(dates)} \n. Starting in {self.start_date}.")

        # get data
        universe = self.portfolio.get_universe()

        for date in tqdm(dates, desc="Backtesting", unit="day"):
            signals = {}

            # get trading plan
            for strategy in self.strategies:
                price_type = strategy.price_type
                min_window = strategy.min_window
                prices = self.portfolio.get_prices_by_dates(
                    price_type, date=date, lookback_window=min_window
                )
                signal = strategy.generate_signals_single(prices.loc[:, universe])
                signals[strategy.name.value] = signal
            trades = plurality_voting_batch(pd.DataFrame(signals)).Signal.tolist()
            trading_plan = dict(zip(universe, trades))
            self.portfolio.trade(date, trading_plan)

        print("Backtest completed!")

    def generate_report(self, rf=0.02, bmk_returns=0.1, filename=None):
        self.portfolio.generate_analytics()
        return self.portfolio.generate_report(rf=rf, bmk_returns=bmk_returns, filename=filename)
