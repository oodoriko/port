import numpy as np


class Constraints:
    """dummy dumb dumb bad"""

    def __init__(self, constraints: dict):
        self.constraints = constraints

    def list_constraints(self):
        return self.constraints

    def evaluate_trades(self, trades_plan: dict[str, int], positions_size: int, max_holdings: int):
        if trades_plan is None or len(trades_plan) == 0:
            return True
        value, count = np.unique(list(trades_plan.values()), return_counts=True)

        max_short_count = max(
            max_holdings / 2, self.constraints["max_short_count"] * positions_size
        )
        max_long_count = max(max_holdings / 2, self.constraints["max_long_count"] * positions_size)

        short_count_idx = np.where(value == -1)[0]
        if len(short_count_idx) > 0:
            short_count = count[short_count_idx[0]]
            if short_count > max_short_count:
                return False
        long_count_idx = np.where(value == 1)[0]
        if len(long_count_idx) > 0:
            long_count = count[long_count_idx[0]]
            if long_count > max_long_count:
                return False
        return True
