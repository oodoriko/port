"""actually do the math here, strategy will make the trading decisions based on the math here"""

import talib
import numpy as np

class TechnicalIndicators:
    @staticmethod
    def macd(prices, fast_period=12, slow_period=26, signal_period=9):
        price_values = prices.values.astype(np.float64)
        _, _, histogram = talib.MACD(
            price_values,
            fastperiod=fast_period,
            slowperiod=slow_period,
            signalperiod=signal_period
        )        
        return histogram[-2], histogram[-1]

    @staticmethod
    def rsi(prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def bollinger_bands(prices, period=20, std_dev=2):
        middle_band = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        return upper_band, middle_band, lower_band

    @staticmethod
    def zscore(prices, period=20):
        rolling_mean = prices.rolling(window=period).mean()
        rolling_std = prices.rolling(window=period).std()
        z_score = (prices - rolling_mean) / rolling_std
        return z_score
