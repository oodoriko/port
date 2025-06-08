import numpy as np
import pandas as pd


class TransactionCost:
    def __init__(
        self,
        base_volatility: float = 0.02,
        temporary_impact_coeff: float = 0.142,
        temporary_exponent: float = 0.6,
        timing_cost_factor: float = 0.5,
    ):
        self.eta = temporary_impact_coeff
        self.beta = temporary_exponent
        self.timing_factor = timing_cost_factor
        self.base_volatility = base_volatility

    def calculate_transaction_costs(
        self,
        shares: dict[str, float],
        execution_time_days: float = 1.0,
        volume: pd.DataFrame = None,
        price: pd.DataFrame = None,
    ) -> dict[str, float]:
        if len(shares) == 0:
            return 0

        cost_multiple = self.get_cost_multiple(volume, shares, execution_time_days)
        total_cost = {
            ticker: val * price[ticker] * cost_multiple[ticker] for ticker, val in shares.items()
        }
        return list(total_cost.values())[0]

    def get_cost_multiple(
        self,
        volume: pd.DataFrame,
        shares: dict[str, float],
        execution_time_days: float = 1.0,
    ) -> dict[str, float]:
        volume = volume[shares.keys()].T
        volume.columns = ["volume"]
        volume["shares"] = shares
        volume["participation_rate"] = volume["shares"] / volume["volume"]

        # Static liquidity factor based on volume levels
        volume_liquidity_map = {
            (0, 100_000): 2.0,
            (100_000, 500_000): 1.5,
            (500_000, 1_000_000): 1.2,
            (1_000_000, 5_000_000): 1.0,
            (5_000_000, float("inf")): 0.8,
        }

        def get_liquidity_factor(volume):
            for (min_vol, max_vol), factor in volume_liquidity_map.items():
                if min_vol <= volume < max_vol:
                    return factor
            return 1.0

        volume["liquidity_factor"] = volume["volume"].apply(get_liquidity_factor)
        volume["temporary_impact"] = (
            (volume["participation_rate"].abs() / execution_time_days) ** self.beta
        ) * self.eta

        volume["timing_cost"] = self.timing_factor * np.sqrt(execution_time_days)

        volume["total_cost_multiple"] = (
            volume["liquidity_factor"] + volume["temporary_impact"] + volume["timing_cost"]
        ) * self.base_volatility
        return volume["total_cost_multiple"].to_dict()
