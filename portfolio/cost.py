import numpy as np
import pandas as pd


class TransactionCost:
    def __init__(
        self,
        fixed_cost: float = 0.005,
        base_volatility: float = 0.02,
        temporary_impact_coeff: float = 0.142,
        temporary_exponent: float = 0.6,
        timing_cost_factor: float = 0.5,
    ):
        self.eta = temporary_impact_coeff
        self.beta = temporary_exponent
        self.timing_factor = timing_cost_factor
        self.base_volatility = base_volatility
        self.fixed_cost = fixed_cost

    def calculate_transaction_costs(
        self,
        shares: dict[str, float],
        execution_time_days: float = 1.0,
        volume: pd.DataFrame = None,  # single date
        price: pd.DataFrame = None,  # single date
    ) -> dict[str, float]:
        if len(shares) == 0:
            return 0
        cost_multiple = self.get_cost_multiple(volume, shares, execution_time_days)
        total_cost = {
            ticker: abs(val) * price[ticker] * (cost_multiple[ticker] + self.fixed_cost)
            for ticker, val in shares.items()
        }
        return total_cost

    def get_cost_multiple(
        self,
        volume: pd.DataFrame,
        shares: dict[str, float],  # tickers: shares
        execution_time_days: float = 1.0,
    ) -> dict[str, float]:
        if len(volume) != len(shares):
            volume = volume[shares.keys()]
        participation_rate = np.array(list(shares.values())) / volume
        liquidity_factor = volume.apply(self.get_liquidity_factor)
        temporary_impact = (
            (participation_rate.abs() / execution_time_days) ** self.beta
        ) * self.eta

        timing_cost = 0.5 * np.sqrt(execution_time_days)

        total_cost_multiple = (
            liquidity_factor + temporary_impact + timing_cost
        ) * self.base_volatility
        return total_cost_multiple.to_dict()

    def get_liquidity_factor(self, volume):
        volume_liquidity_map = {
            (0, 100_000): 2.0,
            (100_000, 500_000): 1.5,
            (500_000, 1_000_000): 1.2,
            (1_000_000, 5_000_000): 1.0,
            (5_000_000, float("inf")): 0.8,
        }

        for (min_vol, max_vol), factor in volume_liquidity_map.items():
            if min_vol <= volume < max_vol:
                return factor
        return 1.0
