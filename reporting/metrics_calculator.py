import numpy as np
import pandas as pd

annualization_factor = {
    "YE": 252,
    "ME": 21,
    "QE": 63,
    "D": 1,
}


def calculate_sharpe(returns, rf, freq="D", annualized=False) -> float | pd.Series:
    daily_excess_return = returns - rf / 252  # assuming rf is 10yrs treasury
    if annualized:
        annualized_return = daily_excess_return.mean() * 252
        annualized_vol = returns.std() * np.sqrt(252)

        return annualized_return / annualized_vol if annualized_vol != 0 else 0

    daily_vol = returns.rolling(window=15, min_periods=15).std()
    daily_vol[daily_vol == 0] = pd.NA  # avoid division by zero

    excess_return = daily_excess_return * annualization_factor[freq]
    volatility = daily_vol * np.sqrt(annualization_factor[freq])
    return (excess_return / volatility).resample(freq).last()


def calculate_ir(daily_returns, bmk_returns, freq="D", annualized=False) -> float | pd.Series:
    daily_excess_return = daily_returns - bmk_returns
    if annualized:
        annualized_return = daily_excess_return.mean() * 252
        annualized_vol = daily_excess_return.std() * np.sqrt(252)
        return annualized_return / annualized_vol if annualized_vol != 0 else 0

    tracking_error = daily_excess_return.rolling(window=15, min_periods=15).std()
    tracking_error[tracking_error == 0] = pd.NA  # avoid division by zero

    excess_return = daily_excess_return * annualization_factor[freq]
    volatility = tracking_error * np.sqrt(annualization_factor[freq])
    return (excess_return / volatility).resample(freq).last()


def get_return(data: pd.Series, annualized=False, freq="D") -> tuple[float, float] | pd.Series:
    if annualized:
        # Use the actual data values, skipping day one
        start_idx = 1
        end_idx = len(data) - 1

        start_value = data.iloc[start_idx]
        end_value = data.iloc[end_idx]
        total_return = (end_value - start_value) / start_value if start_value != 0 else 0

        # Use trading days for annualization (standard in finance)
        trading_days = end_idx - start_idx + 1
        years = trading_days / 252  # 252 trading days per year

        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        return total_return, annualized_return
    if freq == "ME" or freq == "D":  # avoid day one
        return data.resample(freq).mean()[1:].pct_change().dropna()
    else:
        return data.resample(freq).mean().pct_change().dropna()
