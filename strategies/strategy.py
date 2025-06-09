import warnings
from collections import Counter

import numpy as np
import pandas as pd

from config import Strategies, StrategyTypes
from strategies.indicators import TechnicalIndicators

warnings.filterwarnings("ignore")


class Strategy:
    """maybe i don't need this...."""

    def __init__(self, name: Strategies):
        self.name = name
        self.price_type = "close"
        self.min_window = 60

    @classmethod
    def create(cls, strategy_name: Strategies) -> "Strategy":
        if strategy_name == Strategies.MACD_CROSSOVER:
            return MACD()
        elif strategy_name == Strategies.RSI_CROSSOVER:
            return RSI()
        elif strategy_name == Strategies.BOLLINGER_BANDS:
            return BollingerBands()
        elif strategy_name == Strategies.Z_SCORE_MEAN_REVERSION:
            return ZScoreMeanReversion()
        else:
            raise ValueError(f"Invalid strategy name: {strategy_name}")

    def generate_signals_batch(self) -> pd.DataFrame:
        pass

    def generate_signals_single(self) -> dict[str, int]:
        pass


class MomentumStrategy(Strategy):
    def __init__(self, name: StrategyTypes):
        super().__init__(name)
        self.strategy_type = StrategyTypes.MOMENTUM


class MeanReversionStrategy(Strategy):
    def __init__(self, name: str):
        super().__init__(name)
        self.strategy_type = StrategyTypes.MEAN_REVERSION


class VolatilityStrategy(Strategy):
    def __init__(self, name: str):
        super().__init__(name)
        self.strategy_type = StrategyTypes.VOLATILITY


class MACD(MomentumStrategy):
    """macd strategy - cross over. macd needs a good warm up period for stabilization"""

    def __init__(
        self,
        fast_period=12,
        slow_period=26,
        signal_period=9,
    ):
        super().__init__(Strategies.MACD_CROSSOVER)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.min_window = max(200, slow_period * 4)  # 200 periods or 4x slow period 

    def rules(self, prev: float, current: float) -> int:
        if prev <= 0 and current > 0:
            return 1
        elif prev >= 0 and current < 0:
            return -1
        else:
            return 0
        
    def generate_signals_batch(self, data: pd.DataFrame) -> pd.DataFrame:
        """data: row is keyed by date, column is ticker, value is close price"""
        """Returns dataframe with same structure containing MACD histogram values"""
        result = pd.DataFrame(index=data.index, columns=data.columns)
        if len(data) < self.min_window:
            print(f"Not enough data to calculate MACD for {data.columns}")
            return result
       
        for ticker in data.columns:
            histogram = TechnicalIndicators.macd(
                data[ticker], self.fast_period, self.slow_period, self.signal_period
            )
            print(ticker)
            return histogram
    


    def generate_signals_single(self, data: pd.DataFrame) -> dict[str, int]:
        """most feasible for live trading, assumes the data passed is in right dates range"""
        if len(data) < self.slow_period + self.signal_period:
            return {ticker: 0 for ticker in data.columns}

        results = []
        for ticker in data.columns:
            histogram = TechnicalIndicators.macd(
                data[ticker], self.fast_period, self.slow_period, self.signal_period
            )
            return histogram
        #     current = histogram.iloc[-1]
        #     previous = histogram.iloc[-2]

        #     if len(histogram) < 2:
        #         results[ticker] = 0
        #         continue

        #     if previous <= 0 and current > 0:
        #         results[ticker] = 1
        #     elif previous >= 0 and current < 0:
        #         results[ticker] = -1
        #     else:
        #         results[ticker] = 0
        # return results


class RSI(MomentumStrategy):
    """RSI strategy - overbought/oversold"""

    def __init__(self, period=14):
        super().__init__(Strategies.RSI_CROSSOVER)
        self.period = period
        self.min_window = (period // 10 + 1) * 10

    def generate_signals_batch(self, data: pd.DataFrame) -> pd.DataFrame:
        results = {}
        for ticker in data.columns:
            rsi = TechnicalIndicators.rsi(data[ticker], self.period)
            signals = np.where(
                rsi < 30,
                1,  # buy
                np.where(rsi > 70, -1, 0),  # sell  # hold
            )
            results[ticker] = signals
        return pd.DataFrame(results, index=data.index)

    def generate_signals_single(self, data: pd.DataFrame) -> dict[str, int]:
        """most feasible for live trading, assumes the data passed is in right dates range"""
        if len(data) < self.period:
            return {ticker: 0 for ticker in data.columns}

        results = {}
        for ticker in data.columns:
            rsi = TechnicalIndicators.rsi(data[ticker], self.period)
            current = rsi.iloc[-1]

            if current < 30:
                results[ticker] = 1
            elif current > 70:
                results[ticker] = -1
            else:
                results[ticker] = 0
        return results


class BollingerBands(VolatilityStrategy):
    """Bollinger Bands strategy - breakout"""

    def __init__(self, period=20, std_dev=2):
        super().__init__(Strategies.BOLLINGER_BANDS)
        self.period = period
        self.std_dev = std_dev
        self.min_window = (period // 10 + 1) * 10

    def generate_signals_batch(self, data: pd.DataFrame) -> pd.DataFrame:
        results = {}
        for ticker in data.columns:
            upper, _, lower = TechnicalIndicators.bollinger_bands(
                data[ticker], self.period, self.std_dev
            )
            signals = np.where(
                data[ticker] > upper,
                1,  # buy
                np.where(data[ticker] < lower, -1, 0),  # sell  # hold
            )
            results[ticker] = signals
        return pd.DataFrame(results, index=data.index)

    def generate_signals_single(self, data: pd.DataFrame) -> dict[str, int]:
        """most feasible for live trading, assumes the data passed is in right dates range"""
        if len(data) < self.period:
            return {ticker: 0 for ticker in data.columns}

        results = {}
        for ticker in data.columns:
            upper, _, lower = TechnicalIndicators.bollinger_bands(
                data[ticker], self.period, self.std_dev
            )
            current = data[ticker].iloc[-1]

            if current > upper.iloc[-1]:
                results[ticker] = 1
            elif current < lower.iloc[-1]:
                results[ticker] = -1
            else:
                results[ticker] = 0
        return results


class ZScoreMeanReversion(MeanReversionStrategy):
    def __init__(
        self,
        lookback_period=20,
        entry_threshold=2.0,
        exit_threshold=0.5,
    ):
        super().__init__(Strategies.Z_SCORE_MEAN_REVERSION)
        self.lookback_period = lookback_period
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        self.min_window = (lookback_period // 10 + 1) * 10

    def generate_signals_batch(self, data: pd.DataFrame) -> pd.DataFrame:
        results = {}
        for ticker in data.columns:
            z_scores = TechnicalIndicators.zscore(data[ticker], self.lookback_period)
            signals = np.where(
                z_scores > self.entry_threshold,
                -1,
                np.where(
                    z_scores < -self.entry_threshold,
                    1,
                    np.where(
                        np.abs(z_scores) < self.exit_threshold,
                        0,
                        np.nan,
                    ),
                ),
            )
            signals = pd.Series(signals, index=data.index).fillna(method="ffill").fillna(0)
            results[ticker] = signals.values

        return pd.DataFrame(results, index=data.index)

    def generate_signals_single(self, data: pd.DataFrame) -> dict[str, int]:
        """most feasible for live trading, assumes the data passed is in right dates range"""
        if len(data) < self.lookback_period:
            return {ticker: 0 for ticker in data.columns}

        results = {}
        for ticker in data.columns:
            z_scores = TechnicalIndicators.zscore(data[ticker], self.lookback_period)
            current_zscore = z_scores.iloc[-1]

            if pd.isna(current_zscore):
                results[ticker] = 0
                continue

            if current_zscore > self.entry_threshold:
                results[ticker] = -1  # sell
            elif current_zscore < -self.entry_threshold:
                results[ticker] = 1  # buy
            elif abs(current_zscore) < self.exit_threshold:
                results[ticker] = 0  # neutral/exit
            else:
                results[ticker] = 0

        return results


def plurality_voting_single(strategies: list[int], tie_breaker=0) -> int:
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


def plurality_voting_batch(strategies: pd.DataFrame, tie_breaker=0) -> pd.DataFrame:
    strategies["Signal"] = strategies.apply(
        lambda x: plurality_voting_single(x, tie_breaker=tie_breaker), axis=1
    )
    return strategies

def plurality_voting_batch_batch(strategies: list[pd.DataFrame], tie_breaker=0) -> pd.DataFrame:
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
    flat_result = np.array([plurality_voting_single(row.tolist(), tie_breaker) 
                           for row in flat_stacked])
    result_values = flat_result.reshape(stacked.shape[:2])
    result = pd.DataFrame(result_values, index=common_index, columns=common_columns)
    return result

   