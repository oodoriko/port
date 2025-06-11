import warnings
from collections import Counter
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

from strategies.indicators import TechnicalIndicators

warnings.filterwarnings("ignore")


class StrategyTypes(Enum):
    """strategy classification types"""

    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    MEAN_REVERSION = "mean_reversion"


class Strategies(Enum):
    """available trading strategies, note a strategy belongs to a strategy type"""

    MACD_CROSSOVER = "macd_x"
    RSI_CROSSOVER = "rsi_x"
    BOLLINGER_BANDS = "b_bands"
    Z_SCORE_MEAN_REVERSION = "z"


class Strategy:
    """maybe i don't need this...."""

    """filter means the signal is used as a negative signal"""

    def __init__(self, name: Strategies):
        self.name = name
        self.price_type = "close"
        self.min_window = 60
        self.is_filter = False

    @classmethod
    def create(cls, strategy_name: Strategies, is_filter: bool = False) -> "Strategy":
        if strategy_name == Strategies.MACD_CROSSOVER:
            return MACD(is_filter=is_filter)
        elif strategy_name == Strategies.RSI_CROSSOVER:
            return RSI(is_filter=is_filter)
        elif strategy_name == Strategies.BOLLINGER_BANDS:
            return BollingerBands(is_filter=is_filter)
        elif strategy_name == Strategies.Z_SCORE_MEAN_REVERSION:
            return ZScoreMeanReversion(is_filter=is_filter)
        else:
            raise ValueError(f"Invalid strategy name: {strategy_name}")


class MomentumStrategy(Strategy):
    def __init__(self, name: StrategyTypes, is_filter: bool = False):
        super().__init__(name)
        self.is_filter = is_filter
        self.strategy_type = StrategyTypes.MOMENTUM


class MeanReversionStrategy(Strategy):
    def __init__(self, name: str, is_filter: bool = False):
        super().__init__(name)
        self.is_filter = is_filter
        self.strategy_type = StrategyTypes.MEAN_REVERSION


class VolatilityStrategy(Strategy):
    def __init__(self, name: str, is_filter: bool = False):
        super().__init__(name)
        self.is_filter = is_filter
        self.strategy_type = StrategyTypes.VOLATILITY


class MACD(MomentumStrategy):
    """macd strategy - cross over. macd needs a good warm up period for stabilization"""

    def __init__(
        self,
        fast_period=12,
        slow_period=26,
        signal_period=9,
        is_filter: bool = False,
    ):
        super().__init__(Strategies.MACD_CROSSOVER, is_filter)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.min_window = max(200, slow_period * 4)  # 200 periods or 4x slow period

    def get_signal(self, arr: np.ndarray) -> int:
        prev, current = TechnicalIndicators.macd(
            arr, self.fast_period, self.slow_period, self.signal_period
        )
        filter_signal = -1 if self.is_filter else 1
        if prev <= 0 and current > 0:
            return 1 * filter_signal
        elif prev >= 0 and current < 0:
            return -1 * filter_signal
        else:
            return 0 * filter_signal

    def generate_signals_batch(
        self, data: pd.DataFrame, run_start_index: int
    ) -> pd.DataFrame:
        """data: row is keyed by date, column is ticker, value is close price, full history of data"""
        """Returns dataframe with same structure containing trading signals (-1, 0, 1)"""

        data_arr = data.to_numpy()
        signals = [
            np.apply_along_axis(self.get_signal, arr=data_arr[:i, :], axis=0)
            for i in range(run_start_index, len(data_arr))
        ]
        return pd.DataFrame(
            signals, index=data.index[run_start_index:], columns=data.columns
        )

    def generate_signals_single_date(self, data: pd.DataFrame) -> dict[str, int]:
        """data only up to run date"""
        """most feasible for live trading, assumes the data passed is in right dates range"""
        if len(data) < self.slow_period + self.signal_period:
            return {ticker: 0 for ticker in data.columns}

        data_arr = data.to_numpy()
        signals = np.apply_along_axis(
            self.get_signal, arr=data_arr[:-1], axis=0
        )  # exclude current day price
        return {ticker: signal for ticker, signal in zip(data.columns, signals)}


class RSI(MomentumStrategy):
    """RSI strategy - overbought/oversold"""

    def __init__(self, period=14, is_filter: bool = False):
        super().__init__(Strategies.RSI_CROSSOVER, is_filter)
        self.period = period
        self.min_window = (period // 10 + 1) * 10

    def get_signals(self, prices: np.ndarray) -> np.ndarray:
        rsi = TechnicalIndicators.rsi(prices, self.period)
        filter_signal = -1 if self.is_filter else 1
        return (
            np.where(
                rsi < 30,
                1,  # buy
                np.where(rsi > 70, -1, 0),  # sell  # hold
            )
            * filter_signal
        )

    def generate_signals_batch(
        self, data: pd.DataFrame, start_index: int
    ) -> pd.DataFrame:
        results = np.apply_along_axis(self.get_signals, arr=data.to_numpy(), axis=0)[
            start_index:
        ]
        return pd.DataFrame(
            results, index=data.index[start_index:], columns=data.columns
        )

    def generate_signals_single_date(self, data: pd.DataFrame) -> dict[str, int]:
        """most feasible for live trading, assumes the data passed is in right dates range"""
        if len(data) < self.period:
            return {ticker: 0 for ticker in data.columns}
        results = np.apply_along_axis(self.get_signals, arr=data.to_numpy(), axis=0)[-1]
        return dict(zip(data.columns, results))


class BollingerBands(VolatilityStrategy):
    """Bollinger Bands strategy - breakout"""

    def __init__(self, period=20, std_dev=2, is_filter: bool = False):
        super().__init__(Strategies.BOLLINGER_BANDS, is_filter)
        self.period = period
        self.std_dev = std_dev
        self.min_window = (period // 10 + 1) * 10

    def get_signals(self, prices: np.ndarray) -> np.ndarray:
        upper, _, lower = TechnicalIndicators.bollinger_bands(
            prices, self.period, self.std_dev
        )
        filter_signal = -1 if self.is_filter else 1
        return (
            np.where(
                prices > upper,
                1,  # buy
                np.where(prices < lower, -1, 0),  # sell  # hold
            )
            * filter_signal
        )

    def generate_signals_batch(
        self, data: pd.DataFrame, start_index: int
    ) -> pd.DataFrame:
        results = np.apply_along_axis(self.get_signals, arr=data.to_numpy(), axis=0)[
            start_index:
        ]
        return pd.DataFrame(
            results, index=data.index[start_index:], columns=data.columns
        )

    def generate_signals_single_date(self, data: pd.DataFrame) -> dict[str, int]:
        """most feasible for live trading, assumes the data passed is in right dates range"""
        if len(data) < self.period:
            return {ticker: 0 for ticker in data.columns}
        results = np.apply_along_axis(self.get_signals, arr=data.to_numpy(), axis=0)[-1]
        return dict(zip(data.columns, results))


class ZScoreMeanReversion(MeanReversionStrategy):
    def __init__(
        self,
        lookback_period=20,
        entry_threshold=2.0,
        exit_threshold=0.5,
        is_filter: bool = False,
    ):
        super().__init__(Strategies.Z_SCORE_MEAN_REVERSION, is_filter)
        self.lookback_period = lookback_period
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        self.min_window = (lookback_period // 10 + 1) * 10

    def get_signals(self, prices: np.ndarray) -> np.ndarray:
        z_scores = TechnicalIndicators.zscore(prices, self.lookback_period)
        filter_signal = -1 if self.is_filter else 1
        return (
            np.where(
                z_scores > self.entry_threshold,
                -1,
                np.where(z_scores < -self.entry_threshold, 1, 0),
            )
            * filter_signal
        )

    def generate_signals_batch(
        self, data: pd.DataFrame, start_index: int
    ) -> pd.DataFrame:
        results = np.apply_along_axis(self.get_signals, arr=data.to_numpy(), axis=0)[
            start_index:
        ]
        return pd.DataFrame(
            results, index=data.index[start_index:], columns=data.columns
        )

    def generate_signals_single_date(self, data: pd.DataFrame) -> dict[str, int]:
        """most feasible for live trading, assumes the data passed is in right dates range"""
        if len(data) < self.lookback_period:
            return {ticker: 0 for ticker in data.columns}
        results = np.apply_along_axis(self.get_signals, arr=data.to_numpy(), axis=0)[-1]
        return dict(zip(data.columns, results))


def vote_batch(
    strategies: Any, contains_filters: bool = False, tie_breaker: int = 0
) -> Any:
    if contains_filters:
        return sum_voting_batch(strategies)
    else:
        return plurality_voting_batch(strategies, tie_breaker)


def vote_single_date(
    strategies: Any, contains_filters: bool = False, tie_breaker: int = 0
) -> Any:
    if contains_filters:
        return sum_voting_single_date(strategies)
    else:
        return plurality_voting_single_date(strategies, tie_breaker)


def _plurality_voting(strategies: list[int], tie_breaker=0) -> int:
    """strategies: list of ints, each int is a signal for the SAME ticker from different strategies"""
    counts = Counter(strategies)
    most_common = counts.most_common()
    if len(most_common) == 1:
        return most_common[0][0]
    else:
        if most_common[0][1] == most_common[1][1]:
            return tie_breaker
        else:
            return most_common[0][0]


def plurality_voting_single_date(strategies: pd.DataFrame, tie_breaker=0) -> list[int]:
    strategies["Signal"] = strategies.apply(
        lambda x: _plurality_voting(x, tie_breaker=tie_breaker), axis=1
    )
    return strategies.Signal.tolist()


def plurality_voting_batch(
    strategies: list[pd.DataFrame], tie_breaker=0
) -> pd.DataFrame:
    common_index = strategies[0].index
    common_columns = strategies[0].columns

    # Ensure all DataFrames have the same structure
    for i, df in enumerate(strategies[1:], 1):
        if not df.index.equals(common_index):
            raise ValueError(f"DataFrame {i} has different index than DataFrame 0")
        if not df.columns.equals(common_columns):
            raise ValueError(f"DataFrame {i} has different columns than DataFrame 0")

    # vectorize
    stacked = np.stack([df.values for df in strategies], axis=2)
    flat_stacked = stacked.reshape(-1, stacked.shape[2])
    flat_result = np.array(
        [_plurality_voting(row.tolist(), tie_breaker) for row in flat_stacked]
    )
    result_values = flat_result.reshape(stacked.shape[:2])
    result = pd.DataFrame(result_values, index=common_index, columns=common_columns)
    return result


def sum_voting_single_date(strategies: list[int]) -> list[int]:
    return list(np.sign(strategies.sum(axis=1)))


def sum_voting_batch(strategies: list[pd.DataFrame]) -> pd.DataFrame:
    return np.sign(sum(strategies))
