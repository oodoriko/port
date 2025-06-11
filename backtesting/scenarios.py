from typing import Optional

import numpy as np
import pandas as pd

from config import PortfolioSetup, TradingConstraints
from portfolio.portfolio import Portfolio
from strategies.strategy import StrategyTypes


class Scenario:
    def __init__(
        self,
        name,
        start_date,
        end_date,
        constraints,
        portfolio_setup,
        benchmark,
        portfolio_name: Optional[str] = None,
    ):
        self.name = name
        self.strategies = None
        self.start_date = start_date
        self.end_date = end_date
        self.scenario_description = ""
        self.portfolio = Portfolio(
            name=portfolio_name,
            benchmark=benchmark,
            constraints=constraints,
            setup=portfolio_setup,
        )
        self.trading_dates = self.get_trading_dates()
        self.contains_filters = False

    def get_start_date(self) -> str:
        return self.start_date

    def get_end_date(self) -> str:
        return self.end_date

    def get_name(self) -> str:
        return self.name

    def get_portfolio(self) -> Portfolio:
        return self.portfolio

    def get_portfolio_setup(self) -> PortfolioSetup:
        return self.portfolio.setup

    def get_constraints(self) -> TradingConstraints:
        return self.portfolio.constraints

    def get_strategies(self) -> list[StrategyTypes]:
        return self.strategies

    def set_name(self, name):
        self.name = name

    def set_scenario_description(self, scenario_description):
        self.scenario_description = scenario_description

    def set_strategies(self, strategies: list[StrategyTypes]):
        self.strategies = strategies
        self.contains_filters = any(strategy.is_filter for strategy in strategies)

    def get_trading_dates(self) -> list[np.datetime64]:
        return list(
            np.intersect1d(
                self.portfolio.open_prices.index,
                pd.date_range(self.start_date, self.end_date),
            )
        )
