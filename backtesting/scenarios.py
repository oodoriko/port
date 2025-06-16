import json
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd

from data.data import Benchmarks
from portfolio.constraints import ConstraintsConfig
from portfolio.portfolio import Portfolio, PortfolioConfig
from strategies.strategy import Strategy, StrategyTypes


class Scenario:
    def __init__(
        self,
        name: str,
        start_date: str,
        end_date: str,
        constraints: ConstraintsConfig,
        portfolio_config: PortfolioConfig,
        benchmark: Benchmarks,
        portfolio_name: Optional[str] = None,
        verbose: bool = False,
    ):
        self.name = name
        self.strategies = None
        self.start_date = pd.to_datetime(start_date).date()
        self.end_date = pd.to_datetime(end_date).date()
        self.scenario_description = ""
        self.portfolio = Portfolio(
            name=portfolio_name,
            benchmark=benchmark.value,
            constraints=constraints.to_dict(),
            setup=portfolio_config.to_dict(),
            verbose=verbose,
        )
        self.trading_dates = self.get_trading_dates()
        self.contains_filters = False
        self.verbose = verbose
        self.actual_trading_dates = []

    def get_start_date(self) -> str:
        return self.start_date

    def get_end_date(self) -> str:
        return self.end_date

    def get_name(self) -> str:
        return self.name

    def get_portfolio(self) -> Portfolio:
        return self.portfolio

    def get_portfolio_config(self) -> dict:
        return self.portfolio.setup

    def get_constraints(self) -> dict:
        return self.portfolio.constraints.get_constraints()

    def get_strategies(self) -> list[Strategy]:
        return self.strategies

    def set_name(self, name):
        self.name = name

    def set_scenario_description(self, scenario_description):
        self.scenario_description = scenario_description

    def set_strategies(self, strategies: dict[StrategyTypes, bool]):
        if isinstance(strategies, dict):
            strategies = [
                Strategy.create(strategy, is_positive=is_positive)
                for strategy, is_positive in strategies.items()
            ]
            if self.verbose:
                strategy_str = {
                    strategy.name.value: strategy.is_positive for strategy in strategies
                }
                print(f"Strategies: {json.dumps(strategy_str, indent=4)}")
        else:
            raise ValueError(f"Invalid strategies type: {type(strategies)}")

        self.strategies = strategies
        self.contains_filters = any(strategy.is_positive for strategy in strategies)

    def set_actual_trading_dates(self, actual_trading_dates: list[date]):
        self.actual_trading_dates = actual_trading_dates

    def get_actual_trading_dates(self) -> list[date] | None:
        return self.actual_trading_dates

    def get_trading_dates(self) -> list[date]:
        return pd.to_datetime(
            np.intersect1d(
                pd.to_datetime(self.portfolio.open_prices.index),
                pd.date_range(self.start_date, self.end_date),
            )
        ).date
