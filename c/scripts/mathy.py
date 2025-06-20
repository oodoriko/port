import numpy as np
import talib
from numba import njit


@njit
def _ema(price: np.ndarray, period: int) -> np.ndarray:  # T x n_coins
    alpha = 2 / (period + 1)
    ema = np.zeros_like(price)
    ema[0, :] = price[0, :]  # initialize day one value
    for t in range(1, price.shape[0]):
        ema[t, :] = alpha * price[t, :] + (1 - alpha) * ema[t - 1, :]
    return ema


def _ema_talib(price: np.ndarray, period: int) -> np.ndarray:
    return np.apply_along_axis(lambda x: talib.EMA(x, timeperiod=period), axis=0, arr=price)


@njit
def _rsi(price: np.ndarray, period: int) -> np.ndarray:
    T, n_coins = price.shape
    rsi = np.empty((T, n_coins), dtype=np.float64)
    for j in range(n_coins):
        p = price[:, j]
        deltas = p[1:] - p[:-1]
        seed = deltas[:period]
        up = seed[seed > 0].sum() / period
        down = -seed[seed < 0].sum() / period
        rs = up / down if down != 0 else 0
        rsi[:period, j] = np.nan
        rsi[period, j] = 100.0 - 100.0 / (1.0 + rs)
        upval = up
        downval = down
        for i in range(period + 1, T):
            delta = deltas[i - 1]
            upval = (upval * (period - 1) + (delta if delta > 0 else 0)) / period
            downval = (downval * (period - 1) + (-delta if delta < 0 else 0)) / period
            rs = upval / downval if downval != 0 else 0
            rsi[i, j] = 100.0 - 100.0 / (1.0 + rs)
    return rsi


def _rsi_talib(price: np.ndarray, period: int) -> np.ndarray:
    return np.apply_along_axis(lambda x: talib.RSI(x, timeperiod=period), axis=0, arr=price)


def _macd(price: np.ndarray, fast_period: int, slow_period: int, signal_period: int):
    ema_fast = _ema(price, fast_period)
    ema_slow = _ema(price, slow_period)
    macd_line = ema_fast - ema_slow
    macd_signal = _ema(macd_line, signal_period)
    macd_hist = macd_line - macd_signal
    return macd_line, macd_signal, macd_hist


def _macd_talib(price: np.ndarray, fast_period: int, slow_period: int, signal_period: int):
    T, n_coins = price.shape
    macd_line = np.zeros((T, n_coins))
    macd_signal = np.zeros((T, n_coins))
    macd_hist = np.zeros((T, n_coins))
    for i in range(n_coins):
        macd_line[:, i], macd_signal[:, i], macd_hist[:, i] = talib.MACD(
            price[:, i],
            fastperiod=fast_period,
            slowperiod=slow_period,
            signalperiod=signal_period,
        )
    return macd_line, macd_signal, macd_hist
