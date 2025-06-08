from collections import Counter, defaultdict

import numpy as np
import pandas as pd


class PortfolioAnalytics:
    def __init__(
        self,
        portfolio_value_history,
        trades_history=None,
        trades_status=None,
        product_data=None,
        holdings_history=None,
    ):
        self.portfolio_value_history = portfolio_value_history
        self.trades_history = trades_history
        self.trades_status = trades_status
        self.product_data = product_data
        self.holdings_history = holdings_history

    def performance(self, rf=0.02, bmk_returns=0.1):
        portfolio_value = pd.Series(self.portfolio_value_history)
        portfolio_value.index = pd.to_datetime(portfolio_value.index)
        portfolio_value.sort_index(inplace=True)

        # returns - fill gaps to avoid losing data
        # First fill missing dates with forward fill to ensure continuity
        full_date_range = pd.date_range(
            start=portfolio_value.index.min(), end=portfolio_value.index.max(), freq="D"
        )
        portfolio_value_filled = portfolio_value.reindex(full_date_range).ffill()

        daily_returns = portfolio_value_filled.pct_change().dropna()
        monthly_returns = portfolio_value_filled.resample("ME").last().pct_change().dropna()
        quarterly_returns = portfolio_value_filled.resample("QE").last().pct_change().dropna()
        annual_returns = portfolio_value_filled.resample("YE").last().pct_change().dropna()

        # annualized return
        values = list(self.portfolio_value_history.values())
        total_return = (
            (values[-1] - values[0]) / values[0] if len(values) > 1 and values[0] != 0 else 0
        )
        annualized_return = (1 + total_return) ** (252 / len(values)) - 1 if len(values) > 1 else 0

        # Volatility
        annualized_volatility = daily_returns.std() * np.sqrt(252)
        monthly_volatility = monthly_returns.std() * np.sqrt(12)
        quarterly_volatility = quarterly_returns.std() * np.sqrt(4)
        annual_volatility = annual_returns.std()

        # Sharpe Ratios
        overall_sharpe_ratio = (
            (annualized_return - rf) / annualized_volatility if annualized_volatility != 0 else 0
        )
        annual_sharpe_ratios = {}
        for year in daily_returns.index.year.unique():
            year_returns = daily_returns[daily_returns.index.year == year]
            if len(year_returns) > 30:
                year_annual_return = (1 + year_returns.mean()) ** 252 - 1
                year_annual_vol = year_returns.std() * np.sqrt(252)
                if year_annual_vol != 0:
                    annual_sharpe_ratios[year] = (year_annual_return - rf) / year_annual_vol

        monthly_sharpe_ratios = {}
        for month in monthly_returns.index.month.unique():
            month_returns = monthly_returns[monthly_returns.index.month == month]
            if len(month_returns) > 3:
                month_annual_return = (1 + month_returns.mean()) ** 12 - 1
                month_annual_vol = month_returns.std() * np.sqrt(12)
                if month_annual_vol != 0:
                    monthly_sharpe_ratios[month] = (month_annual_return - rf) / month_annual_vol

        quarterly_sharpe_ratios = {}
        for quarter in quarterly_returns.index.quarter.unique():
            quarter_returns = quarterly_returns[quarterly_returns.index.quarter == quarter]
            if len(quarter_returns) > 1:
                quarter_annual_return = (1 + quarter_returns.mean()) ** 4 - 1
                quarter_annual_vol = quarter_returns.std() * np.sqrt(4)
                if quarter_annual_vol != 0:
                    quarterly_sharpe_ratios[quarter] = (
                        quarter_annual_return - rf
                    ) / quarter_annual_vol

        # Win Rate
        positive_days = (daily_returns > 0).sum()
        total_days = len(daily_returns)
        win_rate = positive_days / total_days if total_days > 0 else 0
        avg_win = daily_returns[daily_returns > 0].mean() if positive_days > 0 else 0
        avg_loss = (
            daily_returns[daily_returns < 0].mean() if (total_days - positive_days) > 0 else 0
        )
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else np.inf

        monthly_returns.index = monthly_returns.index.strftime("%Y-%m")
        quarterly_returns.index = quarterly_returns.index.to_period("Q").astype(str)
        annual_returns.index = annual_returns.index.strftime("%Y")

        return {
            # Returns
            "total_return": total_return,
            "annualized_return": annualized_return,
            "monthly_returns": monthly_returns,
            "quarterly_returns": quarterly_returns,
            "annual_returns": annual_returns,
            "daily_returns": daily_returns,
            # Risk
            "annualized_volatility": annualized_volatility,
            "monthly_volatility": monthly_volatility,
            "quarterly_volatility": quarterly_volatility,
            "annual_volatility": annual_volatility,
            # Risk-Adjusted Returns
            "overall_sharpe_ratio": overall_sharpe_ratio,
            "annual_sharpe_ratios": pd.Series(annual_sharpe_ratios),
            "monthly_sharpe_ratios": pd.Series(monthly_sharpe_ratios),
            "quarterly_sharpe_ratios": pd.Series(quarterly_sharpe_ratios),
            # Others
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
        }

    def holdings(self):
        total_unique_holdings = set(
            holding for holdings in self.trades_history.values() for holding in holdings
        )
        filtered_product_data = self.product_data[
            self.product_data.ticker.isin(total_unique_holdings)
        ]
        dates = list(self.trades_history.keys())

        # Sector
        sector_ts = []
        sectors = filtered_product_data.sector.unique()
        for holdings in self.holdings_history.values():
            prd = filtered_product_data[filtered_product_data.ticker.isin(holdings)]
            sector_counts = prd.groupby("sector").size()
            sectors_dict = {sector: sector_counts.get(sector, 0) for sector in sectors}
            sector_ts.append(sectors_dict)

        # Trading activity
        trades_ts = []
        for trades in self.trades_history.values():
            counts = Counter(trades.values())
            trades_dict = {"buy": counts.get(1, 0), "sell": counts.get(-1, 0)}
            trades_ts.append(trades_dict)

        ticker_trades = defaultdict(list)
        for trades in self.trades_history.values():
            for ticker in total_unique_holdings:
                ticker_trades[ticker].append(trades.get(ticker, 0))

        duration_by_ticker = []
        trades_by_ticker = []

        for ticker in total_unique_holdings:
            trade_signals = ticker_trades[ticker]
            duration = _longest_interval_state_machine(trade_signals)
            duration_by_ticker.append({"ticker": ticker, "duration": duration})

            trades_by_ticker.append(
                {
                    "ticker": ticker,
                    "buy": trade_signals.count(1),
                    "sell": trade_signals.count(-1),
                }
            )
        trades_status_count = Counter(self.trades_status.values())
        return {
            "holdings_count": {
                d: len(np.unique(holdings)) for d, holdings in self.holdings_history.items()
            },
            "cancelled_trades_count": trades_status_count[0],
            "no_trades_count": trades_status_count[1],
            "successful_trades_count": trades_status_count[2],
            "sector_ts": sector_ts,
            "trades_ts": trades_ts,
            "duration_by_ticker": duration_by_ticker,
            "trades_by_ticker": trades_by_ticker,
            "dates": dates,
        }

    def advanced_duration_analysis(self):
        trades_details = self.get_trades_details(self.portfolio)
        # more duration analysis
        pass


class AdvancedPortfolioAnalytics:
    def __init__():
        pass

    def get_trades_details(self, portfolio) -> dict:
        # more advance analysis, time consuming, not run unless needed
        price = portfolio.open_prices
        trades = portfolio.trades_history
        trades_df = pd.DataFrame(trades).T
        trades_df, price_df = trades_df.align(price, join="left", fill_value=0)
        trades_amount = trades_df * price_df
        trades_details = trades_amount.apply(lambda x: _get_trades_details(x)).to_dict()
        return trades_details


def _get_trades_details(trades: pd.Series) -> list[dict]:
    cum_cost = 0
    buy_count = 0
    earliest_trade_date = None
    trades_details = []
    for t, price in trades.items():
        if price < 0:  # a sell trade -> a buy and hold and sell trade is completed
            if cum_cost == 0 or earliest_trade_date is None or buy_count == 0:
                print(f"{trades.name} has a short trade on {t.date()}")
                continue
            duration = (t - earliest_trade_date).days
            avg_cost = cum_cost / buy_count
            profit = -1 * price - avg_cost
            trades_details.append(
                {
                    "holding_start_date": earliest_trade_date.date(),
                    "holding_period": duration,
                    "avg_cost": avg_cost,
                    "sell_price": price,
                    "sell_date": t.date(),
                    "profit": profit,
                    "total_long_trades": buy_count,
                }
            )
            cum_cost = 0
            earliest_trade_date = None
            buy_count = 0
        elif price > 0:
            if earliest_trade_date is None:
                earliest_trade_date = t
            buy_count += 1
            cum_cost += price
    return trades_details


def _longest_interval_state_machine(arr):
    """Calculate longest holding interval using state machine approach"""
    max_length = 0

    # Check intervals from -1 to 1
    for i in range(len(arr)):
        if arr[i] == -1:
            # Look for next 1, allowing 0s and 1s in between
            for j in range(i + 1, len(arr)):
                if arr[j] == 1:
                    # Check if no -1s between i and j
                    between = arr[i + 1 : j]
                    if all(x != -1 for x in between):
                        length = j - i + 1
                        if length > max_length:
                            max_length = length
                    break  # Found next 1, stop looking
                elif arr[j] == -1:
                    break  # Found another -1, this interval is invalid

    # Check intervals from 1 to end of array
    for i in range(len(arr)):
        if arr[i] == 1:
            # Check if we can go to end without hitting -1
            remaining = arr[i:]
            if -1 not in remaining:
                length = len(remaining)
                if length > max_length:
                    max_length = length
            else:
                # Find next -1 to see how long we can hold
                next_sell = i + remaining.index(-1)
                length = next_sell - i
                if length > max_length:
                    max_length = length

    return max_length
