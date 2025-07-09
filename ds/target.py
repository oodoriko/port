from typing import Dict, Tuple

import numpy as np
from config import TargetConfig
from numpy.lib.stride_tricks import sliding_window_view


def compute_log_return(series: np.array, horizon: int) -> np.array:
    shifted_series = np.roll(series, -horizon)
    shifted_series[-horizon:] = np.nan
    return np.log(shifted_series) - np.log(series)


def label_directional_return(
    ret: np.array, pos_thresh: float, neg_thresh: float
) -> np.array:
    return np.where(ret > pos_thresh, 1, np.where(ret < neg_thresh, -1, 0))


def compute_mae_mfe(low, high, price, horizon: int) -> Tuple[np.array, np.array]:
    lows = sliding_window_view(low, window_shape=horizon).min(axis=1)
    highs = sliding_window_view(high, window_shape=horizon).max(axis=1)
    # Use the price values corresponding to the sliding window results
    price_window = price[horizon - 1 :]
    mae = lows / price_window - 1
    mfe = highs / price_window - 1
    pad_size = len(price) - len(mae)
    mae_padded = np.concatenate([mae, np.full(pad_size, np.nan)])
    mfe_padded = np.concatenate([mfe, np.full(pad_size, np.nan)])

    return mae_padded, mfe_padded


def compute_vwap(
    low: np.array,
    high: np.array,
    price: np.array,
    volume: np.array,
    timestamps: np.array,
) -> np.array:
    """need to reset at midnight utc"""
    typical_price = (low + high + price) / 3

    if isinstance(timestamps[0], (int, float)):
        import pandas as pd

        timestamps = pd.to_datetime(timestamps, unit="s")

    daily_groups = timestamps.date
    vwap = np.zeros_like(typical_price, dtype=float)

    for date in np.unique(daily_groups):
        day_mask = daily_groups == date
        if day_mask.sum() > 0:
            day_tp = typical_price[day_mask]
            day_vol = volume[day_mask]

            cum_pv = np.cumsum(day_tp * day_vol)
            cum_vol = np.cumsum(day_vol)

            day_vwap = np.where(cum_vol > 0, cum_pv / cum_vol, day_tp)
            vwap[day_mask] = day_vwap

    return vwap


def bucket_quantiles(series: np.array, q: int = 5) -> np.array:
    # Remove NaN values for percentile calculation
    valid_series = series[~np.isnan(series)]
    if len(valid_series) == 0:
        return np.full_like(series, 0, dtype=int)

    # Calculate quantile edges (q+1 edges for q buckets)
    edges = np.percentile(valid_series, np.linspace(0, 100, q + 1))
    # Remove the first edge (0th percentile) to get q edges
    edges = edges[1:]

    # Use digitize to assign bucket indices (0 to q-1)
    return np.digitize(series, edges) - 1


def build_target(
    low: np.array,
    high: np.array,
    price: np.array,
    volume: np.array,
    timestamps: np.array,
    horizon: int,
    threshold: float,
) -> np.array:
    vwap = compute_vwap(low, high, price, volume, timestamps)
    vwap_ret = compute_log_return(vwap, horizon)
    label_vwap = label_directional_return(vwap_ret, threshold, -threshold)
    quant_vwap = bucket_quantiles(vwap_ret)

    # using close price
    close_ret = compute_log_return(price, horizon)
    label_close = label_directional_return(close_ret, threshold, -threshold)

    # mae and mfe
    mae_mfe = compute_mae_mfe(low, high, price, horizon)

    return vwap_ret, label_vwap, quant_vwap, close_ret, label_close, mae_mfe


def build_targets(
    low: np.array,
    high: np.array,
    price: np.array,
    volume: np.array,
    timestamps: np.array,
    config: TargetConfig,
) -> Dict[Tuple[int, float], Dict[str, np.array]]:
    targets = {}
    for w, t in config.windows_thresholds:
        vwap_ret, label_vwap, quant_vwap, close_ret, label_close, (mae, mfe) = (
            build_target(low, high, price, volume, timestamps, w, t)
        )
        targets[(w, t)] = {
            "timestamp": timestamps,
            "vwap_ret": vwap_ret,
            "label_vwap": label_vwap,
            "quant_vwap": quant_vwap,
            "close_ret": close_ret,
            "label_close": label_close,
            "mae": mae,
            "mfe": mfe,
        }
    return targets
