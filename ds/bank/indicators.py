from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

import numpy as np
import pandas as pd

from .config import *
from .mathy import (
    _atr_talib,
    _bollinger_talib,
    _donchian_talib,
    _lag1,
    _macd,
    _mfi_talib,
    _rsi,
    _stochastic_talib,
    _vwap_session_daily,
    _vwap_talib,
)


class Indicator(ABC):
    def __init__(self, **params: Any) -> None:
        self.params: Dict[str, Any] = params

    @abstractmethod
    def compute(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:  # pragma: no cover
        raise NotImplementedError


# i can make a data class for the params, but its not worth it, even dict is not necessary
# indicators are PLURAL!! bc there could be variations for the same windows
# ---------------------------------------------------------------------------
# Momentum
# ---------------------------------------------------------------------------
class StochasticIndicators(Indicator):
    def __init__(self, params: list[int], feature_names: list[str]) -> None:
        """params: [k, d, include_delta, include_k_lag1, include_d_lag1]"""
        self.k, self.d, self.include_delta, self.include_k_lag1, self.include_d_lag1 = (
            params
        )
        self.feature_names = feature_names

    def compute(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, _volume: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        # T * n_coins
        k, d = _stochastic_talib(high, low, close, self.k, self.d)

        k_minus_d = k - d
        k_delta = np.diff(k, prepend=np.nan) if self.include_delta else None
        k_lag1 = _lag1(k) if self.include_k_lag1 else None
        d_lag1 = _lag1(d) if self.include_d_lag1 else None
        return k, d, k_minus_d, k_delta, k_lag1, d_lag1


class MACDHistogramIndicators(Indicator):
    def __init__(self, params: list[int], feature_names: list[str]) -> None:
        """params: [fast, slow, signal, include_lag1, include_hist_delta]"""
        (
            self.fast,
            self.slow,
            self.signal,
            self.include_lag1,
            self.include_hist_delta,
        ) = params
        self.feature_names = feature_names

    def compute(
        self,
        _high: np.ndarray,
        _low: np.ndarray,
        close: np.ndarray,
        _volume: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """returns macd_hist, macd_hist_delta, macd_hist_lag1"""
        _, _, macd_hist = _macd(close, self.fast, self.slow, self.signal)
        macd_hist_delta = (
            np.diff(macd_hist, prepend=np.nan) if self.include_hist_delta else None
        )
        macd_hist_lag1 = _lag1(macd_hist) if self.include_lag1 else None
        return macd_hist, macd_hist_delta, macd_hist_lag1


class RSIIndicators(Indicator):
    def __init__(self, params: list[int], feature_names: list[str]) -> None:
        """params: [rsi_window, include_delta]"""
        self.rsi_window, self.include_delta = params
        self.feature_names = feature_names

    def compute(
        self,
        _high: np.ndarray,
        _low: np.ndarray,
        close: np.ndarray,
        _volume: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """returns rsi, rsi_delta"""
        rsi = _rsi(close, self.rsi_window)
        rsi_delta = np.diff(rsi, prepend=np.nan) if self.include_delta else None
        return rsi, rsi_delta


# ---------------------------------------------------------------------------
# Volatility
# ---------------------------------------------------------------------------
class BollingerIndicators(Indicator):
    def __init__(self, params: list[int, int, str], feature_names: list[str]) -> None:
        """params: [bb_window, std_dev, types]"""
        self.bb_window, self.std_dev, self.type = params
        self.feature_names = feature_names

    def compute(
        self,
        _high: np.ndarray,
        _low: np.ndarray,
        close: np.ndarray,
        _volume: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """returns bollinger_band, bollinger_band_z"""
        upper, middle, lower = _bollinger_talib(
            close,
            self.bb_window,
            self.std_dev,
        )

        middle = np.where(middle == 0, np.nan, middle)
        bb_width = (upper - lower) / middle
        bb_width = np.nan_to_num(bb_width, nan=0.0, posinf=0.0, neginf=0.0)

        band_range = upper - lower
        band_range = np.where(band_range == 0, np.nan, band_range)
        bb_zscore = (close - middle) / (band_range / 2)
        bb_zscore = np.nan_to_num(bb_zscore, nan=0.0)

        return bb_width, bb_zscore


# ---------------------------------------------------------------------------
# Volume‑based
# ---------------------------------------------------------------------------
class MFIIndicators(Indicator):
    def __init__(self, params: list[int], feature_names: list[str]) -> None:
        """params: [mfi_window, include_delta]"""
        self.mfi_window, self.include_delta = params
        self.feature_names = feature_names

    def compute(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """returns mfi, mfi_delta - requires OHLCV data"""
        mfi = _mfi_talib(high, low, close, volume, self.mfi_window)
        mfi_delta = np.diff(mfi, prepend=np.nan) if self.include_delta else None
        return mfi, mfi_delta


class VWAPDistanceIndicators(Indicator):
    def __init__(self, params: int, feature_names: list[str]) -> None:
        """params: vwap_rolling_window"""
        self.vwap_rolling_window = params
        self.feature_names = feature_names

    def compute(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """returns vwap_dist_rolling, vwap_dist_session"""
        typical_price = (high + low + close) / 3.0

        vwap_rolling = _vwap_talib(high, low, close, volume, self.vwap_rolling_window)
        vwap_rolling = np.where(vwap_rolling == 0, np.nan, vwap_rolling)
        vwap_dist_rolling = (typical_price - vwap_rolling) / vwap_rolling
        vwap_dist_rolling = np.nan_to_num(vwap_dist_rolling, nan=0.0)

        vwap_session = _vwap_session_daily(high, low, close, volume)
        vwap_session = np.where(vwap_session == 0, np.nan, vwap_session)
        vwap_dist_session = (typical_price - vwap_session) / vwap_session
        vwap_dist_session = np.nan_to_num(vwap_dist_session, nan=0.0)

        return vwap_dist_rolling, vwap_dist_session


# ---------------------------------------------------------------------------
# Price Structure
# ---------------------------------------------------------------------------
class DonchianIndicators(Indicator):
    def __init__(self, params: int, feature_names: list[str]) -> None:
        """params: donchian_window"""
        self.donchian_window = params
        self.feature_names = feature_names

    def compute(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        _volume: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """returns donchian_band_width, donchian_price_position"""
        upper, middle, lower = _donchian_talib(high, low, self.donchian_window)

        middle = np.where(middle == 0, np.nan, middle)
        donchian_band_width = (upper - lower) / middle
        donchian_band_width = np.nan_to_num(donchian_band_width, nan=0.0)

        band_range = upper - lower
        band_range = np.where(band_range == 0, np.nan, band_range)
        donchian_price_position = (close - lower) / band_range
        donchian_price_position = np.nan_to_num(donchian_price_position, nan=0.5)

        return donchian_band_width, donchian_price_position


class ATRIndicators(Indicator):
    def __init__(self, params: int, feature_names: list[str]) -> None:
        """params: atr_window"""
        self.atr_window = params
        self.feature_names = feature_names

    def compute(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        _volume: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """returns atr, atr_normalized_price"""
        atr = _atr_talib(high, low, close, self.atr_window)

        close = np.where(close == 0, np.nan, close)
        atr_normalized_price = atr / close
        atr_normalized_price = np.nan_to_num(atr_normalized_price, nan=0.0)

        return atr, atr_normalized_price


# ---------------------------------------------------------------------------
# Registry and builders
# ---------------------------------------------------------------------------
INDICATOR_REGISTRY = {
    "stochastic": StochasticIndicators,
    "macd": MACDHistogramIndicators,
    "rsi": RSIIndicators,
    "bollinger": BollingerIndicators,
    "mfi": MFIIndicators,
    "vwap": VWAPDistanceIndicators,
    "donchian": DonchianIndicators,
    "atr": ATRIndicators,
}


def build_indicator(
    name: str, params: list[int] | int, feature_names: list[str]
) -> Indicator:
    cls = INDICATOR_REGISTRY[name]
    return cls(params, feature_names)


def build_indicators(config: FeatureBankConfig) -> list[Indicator]:
    ind = []
    for group_name, group_cfg in vars(config).items():  # momentum, volatility, ...
        print(f"Initiating {group_name}")
        if isinstance(group_cfg, str):
            continue
        for sub_name, sub_cfg in vars(group_cfg).items():  # stochastic, macd, rsi, ...
            for params, feature_names in sub_cfg.features.items():
                indicator = build_indicator(sub_name, params, feature_names)
                ind.append(indicator)
    return ind
