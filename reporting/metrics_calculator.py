import numpy as np
import pandas as pd

annualization_factor = {
    "year": 252,
    "month": 12,
    "quarter": 4,
}


def calculate_sharpe(returns_data, time_attribute, min_periods, rf):

    sharpe_ratios = {}
    unique_periods = getattr(returns_data.index, time_attribute).unique()

    for period in unique_periods:
        period_returns = returns_data[getattr(returns_data.index, time_attribute) == period]
        if len(period_returns) > min_periods:
            period_annual_return = (1 + period_returns.mean()) ** annualization_factor[
                time_attribute
            ] - 1
            period_annual_vol = period_returns.std() * np.sqrt(annualization_factor[time_attribute])
            if period_annual_vol != 0:
                sharpe_ratios[period] = (period_annual_return - rf) / period_annual_vol

    return pd.Series(sharpe_ratios)


def calculate_ir(returns_data, time_attribute, min_periods, bmk_returns):
    information_ratios = {}
    unique_periods = getattr(returns_data.index, time_attribute).unique()

    for period in unique_periods:
        period_returns = returns_data[getattr(returns_data.index, time_attribute) == period]
        if len(period_returns) > min_periods:
            period_annual_return = (1 + period_returns.mean()) ** annualization_factor[
                time_attribute
            ] - 1
            period_annual_vol = period_returns.std() * np.sqrt(annualization_factor[time_attribute])
            if period_annual_vol != 0:
                information_ratios[period] = (
                    period_annual_return - bmk_returns
                ) / period_annual_vol

    return pd.Series(information_ratios)


def get_return(data: pd.Series, annualized=False, freq="M"):
    if annualized:
        vals = list(data.values)
        total_return = (vals[-1] - vals[0]) / vals[0] if len(vals) > 1 and vals[0] != 0 else 0
        annualized_return = (1 + total_return) ** (252 / len(vals)) - 1 if len(vals) > 1 else 0
        return total_return, annualized_return

    # Use updated pandas frequency aliases
    freq_mapping = {"M": "ME", "Q": "QE", "Y": "YE"}
    freq = freq_mapping.get(freq, freq)

    return data.resample(freq).last().pct_change().dropna()
