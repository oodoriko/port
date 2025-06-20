from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

import numpy as np
import pandas as pd


@dataclass
class ConstraintsConfig:
    long_only: bool = True
    cash_pct: float = 0.0
    max_position_size: float = 0.3
    max_drawdown_limit: float = 0.3
    # not used yet
    # rebalance_threshold: float = 0.05
    # max_daily_trades: int = 100
    # blackout_dates: List[str] = field(default_factory=list)
    # default_position_size: float = 0.3
    # sector_exposure: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # country_exposure: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return {
            "long_only": self.long_only,
            "cash_pct": self.cash_pct,
            "max_position_size": self.max_position_size,
            "max_drawdown_limit": self.max_drawdown_limit,
            # not used yet
            # "sector_exposure": self.sector_exposure,
            # "country_exposure": self.country_exposure,
            # "rebalance_threshold": self.rebalance_threshold,
            # "max_daily_trades": self.max_daily_trades,
            # "blackout_dates": self.blackout_dates,
            # "default_position_size": self.default_position_size,
        }


class Constraints:
    def __init__(
        self,
        trailing_stop_loss_pct: float,
        constraints: dict,
        product_data: pd.DataFrame,
    ):
        self.trailing_stop_loss_pct = trailing_stop_loss_pct
        self.constraints = constraints
        self.product_data = product_data

    def get_constraints(self) -> dict:
        return self.constraints

    def trigger_max_drawdown(
        self, portfolio_value: float, portfolio_value_curve: dict
    ) -> bool:
        """good!"""
        if self.constraints is None or len(self.constraints) == 0:
            return False
        if portfolio_value_curve is None or len(portfolio_value_curve) == 0:
            return False
        min_value = min(list(portfolio_value_curve.values()))

        max_drawdown = (min_value - portfolio_value) / min_value
        if max_drawdown > self.constraints["max_drawdown_limit"]:
            return True
        return False

    def check_stop_loss(self, active_positions: dict, price: pd.Series) -> dict:
        """since we are implementing trailing stop loss, whenever a the stop price is
        triggered, all positions are closed for the ticker. But the logic here assumes a fixed
        stop price for each positions, meaning there is a high chance only a part of the position
        whose stop price is triggered is closed. keeping this logic because it is more generic
        """
        closed_positions = {}
        for ticker, positions in active_positions.items():
            today_open_price = price[ticker]
            for date, position in positions.items():
                if today_open_price < position.stop_price:
                    closed_positions[ticker] = closed_positions.get(ticker, []) + [date]
        return closed_positions

    def allocate_capital_to_buy(
        self,
        capital: float,
        portfolio_value: float,
        new_positions: list[str],
        allocation_method: str,
        prices: pd.Series,
        volumes: pd.Series,
        cost_function: Callable,
    ) -> dict:
        available_capital = capital * (1 - self.constraints.get("cash_pct", 0.0))
        return self._execute_allocation_strategy(
            capital=available_capital,
            portfolio_value=portfolio_value,
            tickers=new_positions,
            method=allocation_method,
            prices=prices,
            volumes=volumes,
            cost_function=cost_function,
        )

    def _execute_allocation_strategy(
        self,
        capital: float,
        portfolio_value: float,
        tickers: list[str],
        method: str,
        prices: pd.Series,
        volumes: pd.Series,
        cost_function: Callable,
    ) -> dict:
        if method == "equal":
            return self._allocate_equal_weights(
                capital=capital,
                tickers=tickers,
                volumes=volumes,
                prices=prices,
                portfolio_value=portfolio_value,
                cost_function=cost_function,
            )
        elif method == "max_market_cap":
            priority_list = self._get_market_cap_priority(tickers)
            return self._allocate_by_priority(
                capital=capital,
                priority_list=priority_list,
                volumes=volumes,
                prices=prices,
                portfolio_value=portfolio_value,
                cost_function=cost_function,
            )
        elif method == "highest_volume":
            priority_list = self._get_volume_priority(volumes)
            return self._allocate_by_priority(
                capital=capital,
                priority_list=priority_list,
                volumes=volumes,
                prices=prices,
                portfolio_value=portfolio_value,
                cost_function=cost_function,
            )
        elif method == "optimizer":
            raise NotImplementedError("Optimizer not implemented")
        else:
            raise ValueError(f"Invalid capital allocation method: {method}")

    def _allocate_equal_weights(
        self,
        capital: float,
        tickers: list[str],
        prices: pd.Series,
        volumes: pd.Series,
        portfolio_value: float,
        cost_function: Callable,
    ) -> dict:
        stop_loss_pct = self.trailing_stop_loss_pct
        max_position_size = portfolio_value * self.constraints["max_position_size"]
        budget_per_ticker = capital / len(tickers)
        budget_per_ticker = max(0, min(budget_per_ticker, max_position_size))
        remaining_capital = capital
        transaction_entries = {}
        # first iteration, allocate capital to each ticker based on risk
        for ticker in tickers:
            risk_per_share = prices[ticker] * stop_loss_pct
            max_shares_by_risk = budget_per_ticker / risk_per_share
            transaction_entries[ticker] = max_shares_by_risk

        # second iteration, allocate capital to each ticker based on cash (using risk_based_shares
        transaction_costs = cost_function(
            shares=transaction_entries,
            volume=volumes,
            price=prices,
        )
        for ticker, shares in transaction_entries.items():
            budget = max(0, budget_per_ticker - transaction_costs[ticker] / shares)
            max_shares_by_cash = budget / prices[ticker]
            transaction_entries[ticker] = max_shares_by_cash
            remaining_capital -= transaction_entries[ticker] * prices[ticker]
        return transaction_entries

    def _allocate_by_priority(
        self,
        capital: float,
        priority_list: list[str],
        volumes: pd.Series,
        prices: pd.Series,
        portfolio_value: float,
        cost_function: Callable,
    ) -> dict:
        max_position_size = portfolio_value * self.constraints["max_position_size"]
        remaining_capital = capital

        transaction_entries = {}
        # first iteration, allocate capital to each ticker based on risk
        for ticker in priority_list:
            if remaining_capital <= 0:
                transaction_entries[ticker] = 0
                continue

            risk_per_share = prices[ticker] * self.trailing_stop_loss_pct
            budget_per_ticker = max(0, min(remaining_capital, max_position_size))
            max_shares_by_risk = budget_per_ticker / risk_per_share
            transaction_entries[ticker] = max_shares_by_risk
            remaining_capital -= max_shares_by_risk * prices[ticker]

        ## Allocate any remaining capital to the top priority ticker
        if remaining_capital > 0 and priority_list:
            top_ticker = priority_list[0]
            risk_per_share = prices[top_ticker] * self.trailing_stop_loss_pct
            budget_per_ticker = max(0, min(remaining_capital, max_position_size))
            max_shares_by_risk = budget_per_ticker / risk_per_share
            transaction_entries[top_ticker] = max_shares_by_risk
            remaining_capital -= max_shares_by_risk * prices[top_ticker]

        # second iteration, allocate capital to each ticker based on cash (using risk_based_shares
        remaining_capital = capital
        transaction_costs = cost_function(
            shares=transaction_entries,
            volume=volumes,
            price=prices,
        )
        for ticker, _ in transaction_entries.items():
            budget_per_ticker = (
                max(0, min(remaining_capital, max_position_size))
                - transaction_costs[ticker]
            )
            max_shares_by_cash = max(0, budget_per_ticker) / prices[ticker]
            transaction_entries[ticker] = max_shares_by_cash
            remaining_capital -= max_shares_by_cash * prices[ticker]

        return transaction_entries

    def _get_market_cap_priority(self, tickers: list[str]) -> list[str]:
        if self.product_data is None:
            raise ValueError("Product data not set. Call set_product_data() first.")

        return (
            self.product_data[self.product_data.ticker.isin(tickers)]
            .sort_values(by="marketCap", ascending=False)
            .ticker.tolist()
        )

    def _get_volume_priority(self, volumes: pd.Series) -> list[str]:
        return volumes.sort_values(ascending=False).index.tolist()
