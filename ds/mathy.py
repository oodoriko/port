import numpy as np
import talib
from numba import njit


def _ema(price: np.ndarray, period: int) -> np.ndarray:  # T x n_coins
    alpha = 2 / (period + 1)

    if price.ndim == 1:
        # Handle 1D array (single time series)
        if len(price) == 0:
            return np.array([])
        ema = np.zeros_like(price)
        ema[0] = price[0]  # initialize day one value
        for t in range(1, price.shape[0]):
            ema[t] = alpha * price[t] + (1 - alpha) * ema[t - 1]
        return ema
    else:
        # Handle 2D array (T x n_coins)
        if price.shape[0] == 0:
            return np.array([])
        ema = np.zeros_like(price)
        ema[0, :] = price[0, :]  # initialize day one value
        for t in range(1, price.shape[0]):
            ema[t, :] = alpha * price[t, :] + (1 - alpha) * ema[t - 1, :]
        return ema


def _ema_talib(price: np.ndarray, period: int) -> np.ndarray:
    return np.apply_along_axis(
        lambda x: talib.EMA(x, timeperiod=period), axis=0, arr=price
    )


def _rsi(price: np.ndarray, period: int) -> np.ndarray:
    if price.ndim == 1:
        # Handle 1D array (single time series)
        p = price
        if len(p) <= period:
            # If data length is less than or equal to period, return all NaN
            return np.full(len(p), np.nan)

        deltas = p[1:] - p[:-1]
        seed = deltas[:period]
        up = seed[seed > 0].sum() / period
        down = -seed[seed < 0].sum() / period
        rs = up / down if down != 0 else 0
        rsi = np.empty(len(p), dtype=np.float64)
        rsi[:period] = np.nan
        rsi[period] = 100.0 - 100.0 / (1.0 + rs)
        upval = up
        downval = down
        for i in range(period + 1, len(p)):
            delta = deltas[i - 1]
            upval = (upval * (period - 1) + (delta if delta > 0 else 0)) / period
            downval = (downval * (period - 1) + (-delta if delta < 0 else 0)) / period
            rs = upval / downval if downval != 0 else 0
            rsi[i] = 100.0 - 100.0 / (1.0 + rs)
        return rsi
    else:
        # Handle 2D array (T x n_coins)
        T, n_coins = price.shape
        rsi = np.empty((T, n_coins), dtype=np.float64)
        for j in range(n_coins):
            p = price[:, j]
            if len(p) <= period:
                # If data length is less than or equal to period, return all NaN
                rsi[:, j] = np.nan
                continue

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
                downval = (
                    downval * (period - 1) + (-delta if delta < 0 else 0)
                ) / period
                rs = upval / downval if downval != 0 else 0
                rsi[i, j] = 100.0 - 100.0 / (1.0 + rs)
        return rsi


def _rsi_talib(price: np.ndarray, period: int) -> np.ndarray:
    return np.apply_along_axis(
        lambda x: talib.RSI(x, timeperiod=period), axis=0, arr=price
    )


def _macd(price: np.ndarray, fast_period: int, slow_period: int, signal_period: int):
    ema_fast = _ema(price, fast_period)
    ema_slow = _ema(price, slow_period)
    macd_line = ema_fast - ema_slow
    macd_signal = _ema(macd_line, signal_period)
    macd_hist = macd_line - macd_signal
    return macd_line, macd_signal, macd_hist


def _macd_talib(
    price: np.ndarray, fast_period: int, slow_period: int, signal_period: int
):
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


def _lag1(n: np.ndarray) -> np.ndarray:
    lag1 = np.empty_like(n, dtype=float)
    lag1[0] = np.nan
    lag1[1:] = n[:-1]
    return lag1


def _stochastic_talib(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    k_period: int,
    d_period: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Fastest stochastic using TA-Lib - returns %K and %D"""
    if high.ndim == 1:
        k_percent, d_percent = talib.STOCH(
            high,
            low,
            close,
            fastk_period=k_period,
            slowk_period=d_period,
            slowk_matype=0,  # SMA
            slowd_period=d_period,
            slowd_matype=0,
        )
        return k_percent, d_percent
    else:
        T, n_coins = high.shape
        k_values = np.zeros((T, n_coins))
        d_values = np.zeros((T, n_coins))
        for i in range(n_coins):
            k_values[:, i], d_values[:, i] = _stochastic_talib(
                high[:, i], low[:, i], close[:, i], k_period, d_period
            )
        return k_values, d_values


@njit
def _stochastic_numba(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    k_period: int,
    d_period: int,
) -> tuple[np.ndarray, np.ndarray]:
    T, n_coins = high.shape
    k_values = np.empty((T, n_coins), dtype=np.float64)
    d_values = np.empty((T, n_coins), dtype=np.float64)

    for j in range(n_coins):
        h = high[:, j]
        l = low[:, j]
        c = close[:, j]

        k_values[: k_period - 1, j] = np.nan
        d_values[: k_period + d_period - 2, j] = np.nan

        for i in range(k_period - 1, T):
            highest_high = np.max(h[i - k_period + 1 : i + 1])
            lowest_low = np.min(l[i - k_period + 1 : i + 1])

            if highest_high == lowest_low:
                k_values[i, j] = 50.0  # Avoid division by zero
            else:
                k_values[i, j] = (
                    100.0 * (c[i] - lowest_low) / (highest_high - lowest_low)
                )

        for i in range(k_period + d_period - 2, T):
            d_values[i, j] = np.mean(k_values[i - d_period + 1 : i + 1, j])

    return k_values, d_values


@njit
def _bollinger_numba(
    price: np.ndarray, period: int, std_dev: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    T, n_coins = price.shape
    upper = np.empty((T, n_coins), dtype=np.float64)
    middle = np.empty((T, n_coins), dtype=np.float64)
    lower = np.empty((T, n_coins), dtype=np.float64)

    for j in range(n_coins):
        p = price[:, j]

        upper[: period - 1, j] = np.nan
        middle[: period - 1, j] = np.nan
        lower[: period - 1, j] = np.nan

        for i in range(period - 1, T):
            window = p[i - period + 1 : i + 1]
            mean_val = np.mean(window)
            std_val = np.std(window)

            middle[i, j] = mean_val
            band_width = std_dev * std_val
            upper[i, j] = mean_val + band_width
            lower[i, j] = mean_val - band_width

    return upper, middle, lower


def _bollinger_talib(
    price: np.ndarray, period: int, std_dev: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if price.ndim == 1:
        return talib.BBANDS(
            price, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev, matype=0
        )
    else:
        T, n_coins = price.shape
        upper = np.zeros((T, n_coins))
        middle = np.zeros((T, n_coins))
        lower = np.zeros((T, n_coins))
        for i in range(n_coins):
            upper[:, i], middle[:, i], lower[:, i] = talib.BBANDS(
                price[:, i],
                timeperiod=period,
                nbdevup=std_dev,
                nbdevdn=std_dev,
                matype=0,
            )
        return upper, middle, lower


def _mfi_talib(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    period: int,
) -> np.ndarray:
    if high.ndim == 1:
        return talib.MFI(high, low, close, volume, timeperiod=period)
    else:
        T, n_coins = high.shape
        mfi_values = np.zeros((T, n_coins))
        for i in range(n_coins):
            mfi_values[:, i] = talib.MFI(
                high[:, i], low[:, i], close[:, i], volume[:, i], timeperiod=period
            )
        return mfi_values


@njit
def _mfi_numba(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    period: int,
) -> np.ndarray:
    T, n_coins = high.shape
    mfi_values = np.empty((T, n_coins), dtype=np.float64)

    for j in range(n_coins):
        h = high[:, j]
        l = low[:, j]
        c = close[:, j]
        v = volume[:, j]

        mfi_values[:period, j] = np.nan
        typical_prices = (h + l + c) / 3.0

        if period < T:
            pos_flow_sum = 0.0
            neg_flow_sum = 0.0

            for i in range(1, period + 1):
                raw_money_flow = typical_prices[i] * v[i]
                if typical_prices[i] > typical_prices[i - 1]:
                    pos_flow_sum += raw_money_flow
                elif typical_prices[i] < typical_prices[i - 1]:
                    neg_flow_sum += raw_money_flow

            if neg_flow_sum == 0:
                mfi_values[period, j] = 100.0
            else:
                money_ratio = pos_flow_sum / neg_flow_sum
                mfi_values[period, j] = 100.0 - (100.0 / (1.0 + money_ratio))

            for i in range(period + 1, T):
                old_raw_flow = typical_prices[i - period] * v[i - period]
                if i - period > 0:
                    if typical_prices[i - period] > typical_prices[i - period - 1]:
                        pos_flow_sum -= old_raw_flow
                    elif typical_prices[i - period] < typical_prices[i - period - 1]:
                        neg_flow_sum -= old_raw_flow

                new_raw_flow = typical_prices[i] * v[i]
                if typical_prices[i] > typical_prices[i - 1]:
                    pos_flow_sum += new_raw_flow
                elif typical_prices[i] < typical_prices[i - 1]:
                    neg_flow_sum += new_raw_flow

                if neg_flow_sum == 0:
                    mfi_values[i, j] = 100.0
                else:
                    money_ratio = pos_flow_sum / neg_flow_sum
                    mfi_values[i, j] = 100.0 - (100.0 / (1.0 + money_ratio))

    return mfi_values


def _vwap_talib(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    period: int,
) -> np.ndarray:
    typical_price = (high + low + close) / 3.0

    if typical_price.ndim == 1:
        pv = typical_price * volume
        rolling_pv = talib.SMA(pv, timeperiod=period)
        rolling_vol = talib.SMA(volume, timeperiod=period)
        vwap = rolling_pv / np.where(rolling_vol == 0, np.nan, rolling_vol)
        return np.nan_to_num(vwap, nan=0.0)
    else:
        T, n_coins = typical_price.shape
        vwap_values = np.zeros((T, n_coins))
        for i in range(n_coins):
            vwap_values[:, i] = _vwap_talib(
                high[:, i], low[:, i], close[:, i], volume[:, i], period
            )
        return vwap_values


@njit
def _vwap_rolling_numba(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    period: int,
) -> np.ndarray:
    T, n_coins = high.shape
    vwap_values = np.empty((T, n_coins), dtype=np.float64)

    for j in range(n_coins):
        h = high[:, j]
        l = low[:, j]
        c = close[:, j]
        v = volume[:, j]

        vwap_values[: period - 1, j] = np.nan
        typical_price = (h + l + c) / 3.0

        for i in range(period - 1, T):
            start_idx = i - period + 1
            window_tp = typical_price[start_idx : i + 1]
            window_vol = v[start_idx : i + 1]

            total_pv = np.sum(window_tp * window_vol)
            total_vol = np.sum(window_vol)

            if total_vol == 0:
                vwap_values[i, j] = typical_price[i]
            else:
                vwap_values[i, j] = total_pv / total_vol

    return vwap_values


@njit
def _vwap_session_numba(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    session_starts: np.ndarray,
) -> np.ndarray:
    T, n_coins = high.shape
    vwap_values = np.empty((T, n_coins), dtype=np.float64)

    for j in range(n_coins):
        h = high[:, j]
        l = low[:, j]
        c = close[:, j]
        v = volume[:, j]

        typical_price = (h + l + c) / 3.0

        session_pv_sum = 0.0
        session_vol_sum = 0.0

        for i in range(T):
            if session_starts[i] == 1:
                session_pv_sum = 0.0
                session_vol_sum = 0.0

            session_pv_sum += typical_price[i] * v[i]
            session_vol_sum += v[i]

            if session_vol_sum == 0:
                vwap_values[i, j] = typical_price[i]
            else:
                vwap_values[i, j] = session_pv_sum / session_vol_sum

    return vwap_values


def _vwap_session_daily(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    timestamps: np.ndarray = None,
) -> np.ndarray:
    """Session VWAP with daily reset (assumes daily data or intraday with date info)"""
    if timestamps is None:
        # Simple daily reset - assumes data is ordered chronologically
        # Reset every 390 periods (6.5 hours * 60 minutes for minute data)
        # Or detect significant gaps in volume/price
        if high.ndim == 1:
            # Handle 1D array
            session_starts = np.zeros(len(high), dtype=np.int32)
            session_starts[0] = 1  # First period is always session start

            # Simple heuristic: reset when there's a significant gap or every 390 periods
            for i in range(1, len(high)):
                if i % 390 == 0:  # Daily reset for minute data
                    session_starts[i] = 1

            # Calculate VWAP for 1D array
            typical_price = (high + low + close) / 3.0
            vwap_values = np.empty_like(high, dtype=np.float64)

            session_pv_sum = 0.0
            session_vol_sum = 0.0

            for i in range(len(high)):
                if session_starts[i] == 1:
                    session_pv_sum = 0.0
                    session_vol_sum = 0.0

                session_pv_sum += typical_price[i] * volume[i]
                session_vol_sum += volume[i]

                if session_vol_sum == 0:
                    vwap_values[i] = typical_price[i]
                else:
                    vwap_values[i] = session_pv_sum / session_vol_sum

            return vwap_values
        else:
            # Handle 2D array
            session_starts = np.zeros(high.shape[0], dtype=np.int32)
            session_starts[0] = 1
            for i in range(1, high.shape[0]):
                if i % 390 == 0:  # Daily reset
                    session_starts[i] = 1
    else:
        # Use provided timestamps to detect session starts
        session_starts = np.zeros(len(timestamps), dtype=np.int32)
        session_starts[0] = 1
        # Detect new trading days (implementation depends on timestamp format)

    return _vwap_session_numba(high, low, close, volume, session_starts)


def _donchian_talib(
    high: np.ndarray, low: np.ndarray, period: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if high.ndim == 1:
        upper = talib.MAX(high, timeperiod=period)  # Highest high
        lower = talib.MIN(low, timeperiod=period)  # Lowest low
        middle = (upper + lower) / 2.0
        return upper, middle, lower
    else:
        T, n_coins = high.shape
        upper_vals = np.zeros((T, n_coins))
        middle_vals = np.zeros((T, n_coins))
        lower_vals = np.zeros((T, n_coins))
        for i in range(n_coins):
            upper_vals[:, i], middle_vals[:, i], lower_vals[:, i] = _donchian_talib(
                high[:, i], low[:, i], period
            )
        return upper_vals, middle_vals, lower_vals


@njit
def _donchian_numba(
    high: np.ndarray, low: np.ndarray, period: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    T, n_coins = high.shape
    upper = np.empty((T, n_coins), dtype=np.float64)
    lower = np.empty((T, n_coins), dtype=np.float64)
    middle = np.empty((T, n_coins), dtype=np.float64)

    for j in range(n_coins):
        h = high[:, j]
        l = low[:, j]

        upper[: period - 1, j] = np.nan
        lower[: period - 1, j] = np.nan
        middle[: period - 1, j] = np.nan

        for i in range(period - 1, T):
            start_idx = i - period + 1
            window_high = h[start_idx : i + 1]
            window_low = l[start_idx : i + 1]

            upper[i, j] = np.max(window_high)
            lower[i, j] = np.min(window_low)
            middle[i, j] = (upper[i, j] + lower[i, j]) / 2.0

    return upper, middle, lower


def _atr_talib(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int
) -> np.ndarray:
    if high.ndim == 1:
        return talib.ATR(high, low, close, timeperiod=period)
    else:
        T, n_coins = high.shape
        atr_values = np.zeros((T, n_coins))
        for i in range(n_coins):
            atr_values[:, i] = talib.ATR(
                high[:, i], low[:, i], close[:, i], timeperiod=period
            )
        return atr_values


@njit
def _atr_numba(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int
) -> np.ndarray:
    T, n_coins = high.shape
    atr_values = np.empty((T, n_coins), dtype=np.float64)

    for j in range(n_coins):
        h = high[:, j]
        l = low[:, j]
        c = close[:, j]

        atr_values[0, j] = h[0] - l[0]  # first TR = high - low

        tr_sum = atr_values[0, j]
        count = 1

        for i in range(1, T):
            hl = h[i] - l[i]
            hc = abs(h[i] - c[i - 1])
            lc = abs(l[i] - c[i - 1])
            tr = max(hl, hc, lc)

            if count < period:
                tr_sum += tr
                count += 1
                atr_values[i, j] = tr_sum / count
            else:
                # wilder's smoothing
                atr_values[i, j] = ((period - 1) * atr_values[i - 1, j] + tr) / period

    return atr_values
