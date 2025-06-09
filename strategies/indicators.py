"""actually do the math here, strategy will make the trading decisions based on the math here"""

import talib
import numpy as np

class TechnicalIndicators:
    @staticmethod
    def macd(prices: np.ndarray, fast_period=12, slow_period=26, signal_period=9):
        _, _, histogram = talib.MACD(
            prices,
            fastperiod=fast_period,
            slowperiod=slow_period,
            signalperiod=signal_period
        )        
        
        # Handle insufficient data cases
        if len(histogram) < 2 or np.isnan(histogram[-1]) or np.isnan(histogram[-2]):
            return 0.0, 0.0
            
        return histogram[-2], histogram[-1]

    @staticmethod
    def rsi(prices: np.ndarray, period=14):
        '''talib rsi use simple moving average for initial period then exponential smoothing
        the amount of data passed in in day one matters'''
        return talib.RSI(prices, timeperiod=period)

    @staticmethod
    def bollinger_bands(prices: np.ndarray, period=20, std_dev=2):
        upper_band, middle_band, lower_band = talib.BBANDS(
            prices, 
            timeperiod=period, 
            nbdevup=std_dev, 
            nbdevdn=std_dev, 
            matype=0  # Simple Moving Average
        )
        return upper_band, middle_band, lower_band

    @staticmethod
    def zscore(prices: np.ndarray, period=20):
        # TA-Lib doesn't have a direct zscore function, so we'll use its components
        rolling_mean = talib.SMA(prices, timeperiod=period)
        rolling_std = talib.STDDEV(prices, timeperiod=period)
        z_score = (prices - rolling_mean) / rolling_std
        return z_score
