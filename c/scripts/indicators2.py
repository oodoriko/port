from enum import Enum

import numpy as np
from mathy import _ema, _ema_talib, _macd, _macd_talib, _rsi, _rsi_talib

DEFAULT_PARAMETERS = {
    "ema_fast_period": 12,
    "ema_medium_period": 26,
    "ema_slow_period": 50,
    "rsi_period": 3,
    "rsi_overbought": 70,
    "rsi_oversold": 30,
    "rsi_neutral": 50,
    "rsi_bullish_divergence": 40,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
}


class IT(Enum):
    EMA_S = "ema_slow"
    EMA_M = "ema_medium"
    EMA_F = "ema_fast"
    EMA_F_M = "ema_fast_above_medium"
    EMA_F_S = "ema_fast_above_slow"
    EMA_P_M = "price_above_ema_medium"
    EMA_TRI_BULL = "ema_triple_bullish"

    RSI = "rsi"
    RSI_OB = "rsi_overbought"
    RSI_OS = "rsi_oversold"
    RSI_NEUTRAL = "rsi_neutral"
    RSI_BULL_DIV = "rsi_bullish_divergence"

    MACD = "macd"
    MACD_BULL = "macd_bullish"
    MACD_XU = "macd_cross_up"
    MACD_XD = "macd_cross_down"
    MACD_HIST_INC = "macd_histogram_increasing"


class PriceType(Enum):
    CLOSE = "close"
    HIGH = "high"
    LOW = "low"


class Indicators:
    def __init__(self, use_talib: bool = False, parameters: dict = None):
        self.cache = {}
        self.use_talib = use_talib
        self.ema_fast_period = parameters.get("ema_fast_period")
        self.ema_medium_period = parameters.get("ema_medium_period")
        self.ema_slow_period = parameters.get("ema_slow_period")
        self.rsi_period = parameters.get("rsi_period")
        self.rsi_overbought = parameters.get("rsi_overbought")
        self.rsi_oversold = parameters.get("rsi_oversold")
        self.rsi_neutral_threshold = parameters.get("rsi_neutral")
        self.rsi_bull_div_threshold = parameters.get("rsi_bullish_divergence")
        self.macd_fast = parameters.get("macd_fast")
        self.macd_slow = parameters.get("macd_slow")
        self.macd_signal = parameters.get("macd_signal")

    def clear_cache(self):
        self.cache = {}

    def ema(
        self,
        indicator_type: IT,
        price: np.ndarray,
        period: int,
        price_type: PriceType = PriceType.CLOSE,
    ) -> np.ndarray:
        if indicator_type is None:
            raise ValueError("indicator_type must be provided")
        if price_type is None:
            raise ValueError("price_type must be provided")
        if period is None:
            raise ValueError("period must be provided")
        if price is None:
            raise ValueError("price must be provided")
        if price.ndim != 2:
            raise ValueError("price must be a 2D array")

        key = (indicator_type, price_type)
        if key not in self.cache:
            if self.use_talib:
                self.cache[key] = _ema_talib(price, period)
            else:
                self.cache[key] = _ema(price, period)
        return self.cache[key]

    def rsi(
        self,
        price: np.ndarray,
        period: int,
        price_type: PriceType = PriceType.CLOSE,
    ) -> np.ndarray:
        if price is None:
            raise ValueError("price must be provided")
        if period is None:
            raise ValueError("period must be provided")
        if price_type is None:
            raise ValueError("price_type must be provided")

        key = ("RSI", price_type)
        if key not in self.cache:
            if self.use_talib:
                self.cache[key] = _rsi_talib(price, period)
            else:
                self.cache[key] = _rsi(price, period)
        return self.cache[key]

    def macd(
        self,
        price: np.ndarray,
        price_type: PriceType = None,
    ) -> tuple:
        key = (IT.MACD, price_type)
        if key not in self.cache:
            if self.use_talib:
                macd_line, macd_signal, macd_hist = _macd_talib(
                    price,
                    fast_period=self.macd_fast,
                    slow_period=self.macd_slow,
                    signal_period=self.macd_signal,
                )
            else:
                macd_line, macd_signal, macd_hist = _macd(
                    price, self.macd_fast, self.macd_slow, self.macd_signal
                )
            self.cache[key] = (macd_line, macd_signal, macd_hist)
        return self.cache[key]

    def ema_f_s(
        self,
        price: np.ndarray,
        price_type: PriceType = None,
    ) -> np.ndarray:
        key = (IT.EMA_F_S, price_type)
        if key in self.cache:
            return self.cache[key]
        if (IT.EMA_F, price_type) not in self.cache:
            self.cache[(IT.EMA_F, price_type)] = self.ema(
                IT.EMA_F, price_type, price, self.ema_fast_period
            )
        if (IT.EMA_S, price_type) not in self.cache:
            self.cache[(IT.EMA_S, price_type)] = self.ema(
                IT.EMA_S, price_type, price, self.ema_slow_period
            )
        self.cache[key] = self.cache[(IT.EMA_F, price_type)] > self.cache[(IT.EMA_S, price_type)]
        return self.cache[key].astype(int)

    def ema_f_m(
        self,
        price: np.ndarray,
        price_type: PriceType = None,
    ) -> np.ndarray:
        key = (IT.EMA_F_M, price_type)
        if key in self.cache:
            return self.cache[key]
        if (IT.EMA_F, price_type) not in self.cache:
            self.cache[(IT.EMA_F, price_type)] = self.ema(
                IT.EMA_F, price_type, price, self.ema_fast_period
            )
        if (IT.EMA_M, price_type) not in self.cache:
            self.cache[(IT.EMA_M, price_type)] = self.ema(
                IT.EMA_M, price_type, price, self.ema_medium_period
            )
        self.cache[key] = self.cache[(IT.EMA_F, price_type)] > self.cache[(IT.EMA_M, price_type)]
        return self.cache[key].astype(int)

    def ema_price_m(
        self,
        price: np.ndarray,
        price_type: PriceType = None,
    ) -> np.ndarray:
        key = (IT.EMA_P_M, price_type)
        if key in self.cache:
            return self.cache[key]
        if (IT.EMA_M, price_type) not in self.cache:
            self.cache[(IT.EMA_M, price_type)] = self.ema(
                IT.EMA_M, price_type, price, self.ema_medium_period
            )
        self.cache[key] = price > self.cache[(IT.EMA_M, price_type)]
        return self.cache[key].astype(int)

    def ema_triple_bull(
        self,
        price: np.ndarray,
        price_type: PriceType = None,
    ) -> np.ndarray:
        key = (IT.EMA_TRI_BULL, price_type)
        if key in self.cache:
            return self.cache[key]
        if (IT.EMA_F, price_type) not in self.cache:
            self.cache[(IT.EMA_F, price_type)] = self.ema(
                IT.EMA_F, price_type, price, self.ema_fast_period
            )
        if (IT.EMA_M, price_type) not in self.cache:
            self.cache[(IT.EMA_M, price_type)] = self.ema(
                IT.EMA_M, price_type, price, self.ema_medium_period
            )
        if (IT.EMA_S, price_type) not in self.cache:
            self.cache[(IT.EMA_S, price_type)] = self.ema(
                IT.EMA_S, price_type, price, self.ema_slow_period
            )
        self.cache[key] = (
            self.cache[(IT.EMA_F, price_type)] > self.cache[(IT.EMA_M, price_type)]
        ) & (self.cache[(IT.EMA_M, price_type)] > self.cache[(IT.EMA_S, price_type)])
        return self.cache[key].astype(int)

    def rsi_ob(
        self,
        price: np.ndarray,
        price_type: PriceType = None,
    ) -> np.ndarray:
        key = (IT.RSI_OB, price_type)
        if key not in self.cache:
            if (IT.RSI, price_type) not in self.cache:
                self.cache[(IT.RSI, price_type)] = self.rsi(price, self.rsi_period, price_type)
            self.cache[key] = (self.cache[(IT.RSI, price_type)] > self.rsi_overbought).astype(int)
        return self.cache[key]

    def rsi_os(
        self,
        price: np.ndarray,
        price_type: PriceType = None,
    ) -> np.ndarray:
        key = (IT.RSI_OS, price_type)
        if key not in self.cache:
            if (IT.RSI, price_type) not in self.cache:
                self.cache[(IT.RSI, price_type)] = self.rsi(price, self.rsi_period, price_type)
            self.cache[key] = (self.cache[(IT.RSI, price_type)] < self.rsi_oversold).astype(int)
        return self.cache[key]

    def rsi_neutral(
        self,
        price: np.ndarray,
        price_type: PriceType = None,
    ) -> np.ndarray:
        key = (IT.RSI_NEUTRAL, price_type)
        if key not in self.cache:
            if (IT.RSI, price_type) not in self.cache:
                self.cache[(IT.RSI, price_type)] = self.rsi(price, self.rsi_period, price_type)
            self.cache[key] = (
                (self.cache[(IT.RSI, price_type)] >= self.rsi_overbought)
                & (self.cache[(IT.RSI, price_type)] <= self.rsi_oversold)
            ).astype(int)
        return self.cache[key]

    def rsi_bull_div(
        self,
        price: np.ndarray,
        price_type: PriceType = None,
    ) -> np.ndarray:
        key = (IT.RSI_BULL_DIV, price_type)
        if key not in self.cache:
            if (IT.RSI, price_type) not in self.cache:
                self.cache[(IT.RSI, price_type)] = self.rsi(price, self.rsi_period, price_type)
            rsi_slope = np.diff(self.cache[(IT.RSI, price_type)], axis=0, prepend=np.nan)
            price_slope = np.diff(price, axis=0, prepend=np.nan)
            self.cache[key] = (
                (price_slope < 0)
                & (rsi_slope > 0)
                & (self.cache[(IT.RSI, price_type)] < self.rsi_bull_div_threshold)
            ).astype(int)
        return self.cache[key]

    def macd_bullish(
        self,
        price: np.ndarray,
        price_type: PriceType = PriceType.CLOSE,
    ) -> np.ndarray:
        key = ("MACD_BULLISH", price_type)
        if key not in self.cache:
            macd_line, macd_signal, _ = self.macd(price, price_type)
            self.cache[key] = (macd_line > macd_signal).astype(int)
        return self.cache[key]

    def macd_xu(
        self,
        price: np.ndarray,
        price_type: PriceType = None,
    ) -> np.ndarray:
        key = ("MACD_XU", price_type)
        if key not in self.cache:
            if (IT.MACD_BULL, price_type) not in self.cache:
                self.cache[(IT.MACD_BULL, price_type)] = self.macd_bullish(price, price_type)
            self.cache[key] = (
                np.diff(self.cache[(IT.MACD_BULL, price_type)], axis=0, prepend=np.nan) > 0
            ).astype(int)
        return self.cache[key]

    def macd_xd(
        self,
        price: np.ndarray,
        price_type: PriceType = None,
    ) -> np.ndarray:
        key = ("MACD_XD", price_type)
        if key not in self.cache:
            if (IT.MACD_BULL, price_type) not in self.cache:
                self.cache[(IT.MACD_BULL, price_type)] = self.macd_bullish(price, price_type)
            self.cache[key] = (
                -np.diff(self.cache[(IT.MACD_BULL, price_type)], axis=0, prepend=np.nan) < 0
            ).astype(int)
        return self.cache[key]

    def macd_hist_inc(
        self,
        price: np.ndarray,
        price_type: PriceType = None,
    ) -> np.ndarray:
        key = ("MACD_HIST_INC", price_type)
        if key not in self.cache:
            if (IT.MACD, price_type) not in self.cache:
                self.cache[(IT.MACD, price_type)] = self.macd(price, price_type)
            macd_hist = self.cache[(IT.MACD, price_type)][2]
            self.cache[key] = (np.diff(macd_hist, axis=0, prepend=np.nan) > 0).astype(int)
        return self.cache[key]
