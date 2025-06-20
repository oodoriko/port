from collections import defaultdict

import numpy as np
import pandas as pd

from portfolio.metrics_calculator import calculate_ir, calculate_sharpe, get_return
from portfolio.portfolio import TransactionType


class PortfolioAnalytics:
    def __init__(
        self,
        portfolio,
        rf=0.02,
        bmk_returns=0.1,  # we need to source a real bmk
        actual_trading_dates=None,
    ):
        self.portfolio = portfolio

        self.product_data = portfolio.product_data
        self.rf = rf
        self.bmk_returns = bmk_returns
        self.actual_trading_dates = actual_trading_dates
        self.portfolio_value_curve, self.capital_curve, self.holdings_curve = (
            self.get_curves()
        )

    def get_curves(self):
        portfolio_value_curve = self.portfolio.portfolio_value_curve
        capital_curve = self.portfolio.capital_curve
        holdings_curve = {  # unique ticker per day
            d: len(holdings) for d, holdings in self.portfolio.holdings_history.items()
        }
        return portfolio_value_curve, capital_curve, holdings_curve

    def performance_metrics(self):
        portfolio_value = pd.Series(self.portfolio.portfolio_value_curve)
        portfolio_value.index = pd.to_datetime(portfolio_value.index)
        portfolio_value.sort_index(inplace=True)

        total_return, annualized_return = get_return(portfolio_value, annualized=True)
        daily_returns = get_return(portfolio_value)
        annualized_sharpe = calculate_sharpe(daily_returns, self.rf, annualized=True)
        annualized_ir = calculate_ir(daily_returns, self.bmk_returns, annualized=True)

        return {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "daily_returns": daily_returns,
            "annualized_sharpe": annualized_sharpe,
            "annualized_ir": annualized_ir,
            "portfolio_value_curve": portfolio_value,
        }


class AdvancedPortfolioAnalytics(PortfolioAnalytics):
    def __init__(self, portfolio, rf=0.02, bmk_returns=0.1, actual_trading_dates=None):
        super().__init__(portfolio, rf, bmk_returns, actual_trading_dates)

        self.cashflow_stats_ts, self.ticker_level_records_ts, self.daily_pnl_ts = (
            self._process_trades_data()
        )

    def signal_metrics_ts(self):
        signal_counts = defaultdict(int)
        for date, signals in self.portfolio.signals_history.items():
            executed_trading_plan = self.portfolio.executed_plan_history[date]

            executed_arr = np.array(list(executed_trading_plan.values()))
            signal_arr = np.array(list(signals.values()))

            total_signal = (signal_arr != 0).sum()
            executed = ((executed_arr == "1") & (signal_arr == 1)) | (
                (executed_arr == "-1") & (signal_arr == -1)
            ).sum()
            no_sell = (executed_arr == "No short sell (or stop loss triggered)").sum()
            insufficient_capital = (executed_arr == "Insufficient capital").sum()
            max_drawdown = (executed_arr == "max_drawdown").sum()
            no_signal = (signal_arr == 0).sum()
            signal_counts[date] = {
                "total_signal": total_signal,
                "executed": executed,
                "no_sell": no_sell,
                "insufficient_capital": insufficient_capital,
                "max_drawdown": max_drawdown,
                "no_signal": no_signal,
            }
        return signal_counts

    def performance_metrics(self):
        result = super().performance_metrics()

        daily_returns = result["daily_returns"]

        monthly_returns = get_return(result["portfolio_value_curve"], freq="ME")
        quarterly_returns = get_return(result["portfolio_value_curve"], freq="QE")
        annual_returns = get_return(result["portfolio_value_curve"], freq="YE")

        monthly_sharpe = calculate_sharpe(
            daily_returns, freq="ME", rf=self.rf
        )  # min 10 days per month
        quarterly_sharpe = calculate_sharpe(daily_returns, freq="QE", rf=self.rf)

        monthly_ir = calculate_ir(
            daily_returns, self.bmk_returns, freq="ME"
        )  # min 10 days per month
        quarterly_ir = calculate_ir(daily_returns, self.bmk_returns, freq="QE")

        # Win Rate metrics
        positive_days = (daily_returns > 0).sum()
        negative_days = (daily_returns < 0).sum()
        total_days = len(daily_returns)

        win_rate = positive_days / total_days if total_days > 0 else 0
        avg_win = daily_returns[daily_returns > 0].mean() if positive_days > 0 else 0
        avg_loss = (
            abs(daily_returns[daily_returns < 0].mean()) if negative_days > 0 else 0
        )

        # Correct profit factor calculation
        total_gains = daily_returns[daily_returns > 0].sum()
        total_losses = abs(daily_returns[daily_returns < 0].sum())
        profit_factor = total_gains / total_losses if total_losses != 0 else np.inf

        # Update the result dictionary and return it
        result.update(
            {
                "monthly_returns": monthly_returns,
                "quarterly_returns": quarterly_returns,
                "annual_returns": annual_returns,
                "monthly_sharpe": monthly_sharpe,
                "quarterly_sharpe": quarterly_sharpe,
                "monthly_ir": monthly_ir,
                "quarterly_ir": quarterly_ir,
                "win_rate": win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "profit_factor": profit_factor,
            }
        )

        return result

    def trading_metrics(self):
        trades_ts = {}
        for date, trades in self.portfolio.executed_plan_history.items():
            trades_arr = np.array(list(trades.values()))
            trades_ts[date] = {
                "buy": (trades_arr == 1).sum(),
                "sell": (trades_arr == -1).sum(),
                "insufficient_capital": (trades_arr == "Insufficient capital").sum(),
                "max_drawdown": (trades_arr == "Max drawdown").sum(),
                "stop_loss": (trades_arr == "Stop loss").sum(),
                "no_short": (trades_arr == "No short sell").sum(),
            }
        ticker_metrics = []
        sell_trades_metrics = defaultdict(list)
        stop_loss_trades_metrics = defaultdict(list)
        max_drawdown_trades_metrics = defaultdict(list)

        for ticker, trades in self.ticker_level_records_ts.items():
            df = pd.DataFrame(trades).T
            ticker_metrics.append(
                {
                    "ticker": ticker,
                    "buy": df["total_long_trades"].sum(),
                    "sell": len(df),
                    "duration": df["holding_period"].mean(),
                    "return": df["return"].mean(),
                    "return_net_of_cost": df["return_net_of_cost"].mean(),
                    "profit": df["profit"].mean(),
                    "profit_net_of_cost": df["profit_net_of_cost"].mean(),
                    "stop_loss_count": df[
                        df["exit_reason"] == TransactionType.STOP_LOSS.value
                    ].shape[0],
                    "total_trades": len(df) + df["total_long_trades"].sum(),
                }
            )
            for date, trade in trades.items():
                if trade["exit_reason"] == "sell":
                    sell_trades_metrics[date].append(trade)
                elif trade["exit_reason"] == "stop_loss":
                    stop_loss_trades_metrics[date].append(trade)
                elif trade["exit_reason"] == "max_drawdown":
                    max_drawdown_trades_metrics[date].append(trade)
        trades_by_ticker = pd.DataFrame(ticker_metrics)
        no_signal_days = sum(
            [
                (np.array(signals.values()) == 0).all()
                for signals in self.portfolio.signals_history.values()
            ]
        )

        return {
            "trades_ts": trades_ts,  # {date: {buy: int, sell: int, ...}
            "trades_by_ticker": trades_by_ticker,
            "no_signal_days": no_signal_days,
            "sell_trades_metrics": sell_trades_metrics,
            "stop_loss_trades_metrics": stop_loss_trades_metrics,
            "max_drawdown_trades_metrics": max_drawdown_trades_metrics,
        }

    def sector_metrics(self):
        trades_by_ticker = self.trading_metrics()["trades_by_ticker"]
        prd_data = trades_by_ticker.merge(self.product_data, on="ticker", how="left")
        prd_data.set_index("ticker", inplace=True)

        # Sector
        sector_ts = []
        sectors = prd_data.sector.unique()
        for holdings in self.portfolio.holdings_history.values():
            prd = prd_data.loc[holdings.keys()]
            sector_counts = prd.groupby("sector").size()
            sectors_dict = {sector: sector_counts.get(sector, 0) for sector in sectors}
            sector_ts.append(sectors_dict)

        return {
            "sector_ts": sector_ts,
            "sector_trading_data": prd_data,
        }

    def get_cashflow_curve(self) -> dict:
        transaction_costs_ts = {
            d: k["costs"] for d, k in self.cashflow_stats_ts.items()
        }
        buy_proceeds_ts = {
            d: k["buy_proceeds"] for d, k in self.cashflow_stats_ts.items()
        }
        sell_proceeds_ts = {
            d: k["sell_proceeds"] for d, k in self.cashflow_stats_ts.items()
        }
        return {
            "transaction_costs_ts": transaction_costs_ts,
            "buy_proceeds_ts": buy_proceeds_ts,
            "sell_proceeds_ts": sell_proceeds_ts,
        }

    def get_pnl_curve(self) -> dict:
        realized_gain_sell_ts = {
            d: k["realized_gain_sell"] for d, k in self.daily_pnl_ts.items()
        }
        realized_loss_sell_ts = {
            d: k["realized_loss_sell"] for d, k in self.daily_pnl_ts.items()
        }
        realized_gain_stop_loss_ts = {
            d: k["realized_gain_stop_loss"] for d, k in self.daily_pnl_ts.items()
        }
        realized_loss_stop_loss_ts = {
            d: k["realized_loss_stop_loss"] for d, k in self.daily_pnl_ts.items()
        }
        realized_return_ts = {
            d: k["realized_return"] for d, k in self.daily_pnl_ts.items()
        }
        realized_return_net_of_cost_ts = {
            d: k["realized_return_net_of_cost"] for d, k in self.daily_pnl_ts.items()
        }
        realized_return_pct_ts = {
            d: k["realized_return_pct"] for d, k in self.daily_pnl_ts.items()
        }
        realized_return_net_of_cost_pct_ts = {
            d: k["realized_return_net_of_cost_pct"]
            for d, k in self.daily_pnl_ts.items()
        }
        return {
            "realized_gain_sell_ts": realized_gain_sell_ts,
            "realized_loss_sell_ts": realized_loss_sell_ts,
            "realized_gain_stop_loss_ts": realized_gain_stop_loss_ts,
            "realized_loss_stop_loss_ts": realized_loss_stop_loss_ts,
            "realized_return_ts": realized_return_ts,
            "realized_return_net_of_cost_ts": realized_return_net_of_cost_ts,
            "realized_return_pct_ts": realized_return_pct_ts,
            "realized_return_net_of_cost_pct_ts": realized_return_net_of_cost_pct_ts,
        }

    def _process_trades_data(self):
        all_positions = []
        all_transactions = []

        # first flatten the data structure for positions and transactions
        # a position represents a single long event, whereas transaction represents a single
        # sell event that may have sell more than one positions e.g. a ticker is bought twice then sold all
        for date in self.actual_trading_dates:
            for ticker, sell_record in self.portfolio.sell_history.get(
                date, {}
            ).items():
                closed_positions = self.portfolio.closed_positions.get(date, {}).get(
                    ticker
                )
                if not closed_positions:
                    raise ValueError(
                        f"Ticker {ticker} has no closed positions on date {date} but has sell record"
                    )

                # Count number of positions closed in this sell event
                total_positions_closed = len(closed_positions)

                for pos in closed_positions:
                    position_data = {
                        "date": pd.to_datetime(date),
                        "ticker": ticker,
                        "entry_date": pd.to_datetime(pos.entry_date),
                        "entry_price": pos.entry_price,
                        "entry_shares": pos.entry_shares,
                        "exit_date": pd.to_datetime(pos.exit_date),
                        "exit_price": pos.exit_price,
                        "exit_shares": pos.exit_shares,
                        "exit_reason": pos.exit_reason.value,
                        "total_positions_in_cycle": total_positions_closed,  # Add this to track positions per cycle
                    }
                    # Calculate holding period for each position individually
                    position_data["holding_period"] = (
                        position_data["exit_date"] - position_data["entry_date"]
                    ).days
                    all_positions.append(position_data)

                stop_loss_sell = self.portfolio.stop_loss_history.get(date, {}).get(
                    ticker
                )
                if stop_loss_sell:
                    all_transactions.append(
                        {
                            "date": pd.to_datetime(date),
                            "ticker": ticker,
                            "costs": stop_loss_sell.get("costs"),
                            "proceeds": stop_loss_sell.get("proceeds"),
                            "type": TransactionType.STOP_LOSS.value,
                        }
                    )
                all_transactions.append(
                    {
                        "date": pd.to_datetime(date),
                        "ticker": ticker,
                        "costs": sell_record.get("costs"),
                        "proceeds": sell_record.get("proceeds"),
                        "type": TransactionType.SELL.value,
                    }
                )

            for ticker, buy_record in self.portfolio.buy_history.get(date, {}).items():
                all_transactions.append(
                    {
                        "date": pd.to_datetime(date),
                        "ticker": ticker,
                        "costs": buy_record["costs"],
                        "proceeds": buy_record["proceeds"],
                        "type": TransactionType.BUY.value,
                    }
                )

        positions_df = pd.DataFrame(all_positions)
        transactions_df = pd.DataFrame(all_transactions)

        if not positions_df.empty:
            positions_df["realized_return"] = (
                positions_df["exit_price"] - positions_df["entry_price"]
            ) * positions_df["exit_shares"]
            positions_df["realized_return_pct"] = (
                positions_df["exit_price"] - positions_df["entry_price"]
            ) / positions_df["entry_price"]

            def categorize_pnl(row):
                pnl = row["realized_return"]
                if row["exit_reason"] == TransactionType.SELL.value:
                    return max(pnl, 0), min(pnl, 0), 0, 0
                elif row["exit_reason"] == TransactionType.STOP_LOSS.value:
                    return 0, 0, max(pnl, 0), min(pnl, 0)
                return 0, 0, 0, 0

            pnl_categories = positions_df.apply(
                categorize_pnl, axis=1, result_type="expand"
            )
            pnl_categories.columns = [
                "realized_gain_sell",
                "realized_loss_sell",
                "realized_gain_stop_loss",
                "realized_loss_stop_loss",
            ]
            positions_df = pd.concat([positions_df, pnl_categories], axis=1)

            grouped = (
                positions_df.groupby(["date", "ticker", "exit_reason"])
                .agg(
                    {
                        "entry_date": "min",
                        "exit_date": "max",
                        "exit_shares": "sum",
                        "realized_return": "sum",
                        "realized_return_pct": lambda x: (
                            x * positions_df.loc[x.index, "exit_shares"]
                        ).sum()
                        / positions_df.loc[x.index, "exit_shares"].sum(),
                        "entry_price": lambda x: (
                            x * positions_df.loc[x.index, "entry_shares"]
                        ).sum()
                        / positions_df.loc[x.index, "entry_shares"].sum(),
                        "realized_gain_sell": "sum",
                        "realized_loss_sell": "sum",
                        "realized_gain_stop_loss": "sum",
                        "realized_loss_stop_loss": "sum",
                        "holding_period": "mean",  # Average holding period for multiple positions
                        "total_positions_in_cycle": "first",  # Just take the first since they're all the same for a cycle
                    }
                )
                .reset_index()
            )

            # Merge costs for transaction costs calculation
            costs_df = (
                transactions_df[transactions_df.type == TransactionType.BUY.value]
                .merge(
                    grouped[["ticker", "entry_date", "exit_date"]],
                    right_on=["entry_date", "ticker"],
                    left_on=["date", "ticker"],
                    how="left",
                )
                .groupby(["ticker", "exit_date"])
                .agg({"costs": "sum"})
                .reset_index()
            ).merge(
                transactions_df[transactions_df.type != TransactionType.BUY.value],
                left_on=["ticker", "exit_date"],
                right_on=["ticker", "date"],
                how="inner",
            )
            costs_df["costs"] = costs_df.apply(lambda x: x.costs_x + x.costs_y, axis=1)

            grouped_costs = grouped.merge(
                costs_df[["ticker", "exit_date", "costs"]],
                left_on=["ticker", "exit_date"],
                right_on=["ticker", "exit_date"],
                how="left",
            )

            grouped_costs["realized_return_net_of_cost"] = (
                grouped_costs["realized_return"] - grouped_costs["costs"]
            )
            grouped_costs["realized_return_net_of_cost_pct"] = grouped_costs[
                "realized_return_net_of_cost"
            ] / (grouped_costs["entry_price"] * grouped_costs["exit_shares"])

            daily_pnl = grouped_costs.groupby("date").agg(
                {
                    "realized_gain_sell": "sum",
                    "realized_loss_sell": "sum",
                    "realized_gain_stop_loss": "sum",
                    "realized_loss_stop_loss": "sum",
                    "realized_return": "sum",
                    "realized_return_net_of_cost": "sum",
                    "realized_return_pct": "mean",
                    "realized_return_net_of_cost_pct": "mean",
                }
            )

            ticker_level_records_ts = defaultdict(dict)
            for _, row in grouped_costs.iterrows():
                ticker_level_records_ts[row["ticker"]][row["date"]] = {
                    "holding_start_date": row["entry_date"],
                    "holding_end_date": row["exit_date"],
                    "holding_period": row["holding_period"],
                    "cost_basis": row["entry_price"],
                    "total_long_trades": row[
                        "total_positions_in_cycle"
                    ],  # Use the count of positions closed in this cycle
                    "profit": row["realized_return"],
                    "return": row["realized_return_pct"],
                    "profit_net_of_cost": row["realized_return_net_of_cost"],
                    "return_net_of_cost": row["realized_return_net_of_cost_pct"],
                    "transaction_costs": row["costs"],
                    "exit_reason": row["exit_reason"],
                }

            daily_pnl_ts = daily_pnl.to_dict(orient="index")

            if not transactions_df.empty:
                cashflow_stats = (
                    transactions_df.groupby(["date", "type"])
                    .agg({"costs": "sum", "proceeds": "sum"})
                    .reset_index()
                    .to_dict(orient="records")
                )
                cashflow_stats_ts = defaultdict(
                    lambda: {
                        "costs": 0,
                        "sell_proceeds": 0,
                        "buy_proceeds": 0,
                    }
                )

                for entry in cashflow_stats:
                    if entry["type"] == TransactionType.BUY.value:
                        cashflow_stats_ts[entry["date"]]["buy_proceeds"] = entry[
                            "proceeds"
                        ]
                    elif entry["type"] == TransactionType.SELL.value:
                        cashflow_stats_ts[entry["date"]]["sell_proceeds"] = entry[
                            "proceeds"
                        ]
                    cashflow_stats_ts[entry["date"]]["costs"] = entry["costs"]

            return cashflow_stats_ts, ticker_level_records_ts, daily_pnl_ts

    def contribution_metrics(self):
        """Analyze capital injections and trading activity contributions"""
        # Get the capital curve which includes injections
        capital_curve = pd.Series(self.capital_curve)
        portfolio_value_curve = pd.Series(self.portfolio_value_curve)

        # Calculate total capital injected
        initial_capital = self.portfolio.setup["initial_capital"]
        monthly_injection = self.portfolio.setup["new_capital_growth_amt"]
        total_months = len(
            pd.date_range(
                start=capital_curve.index[0], end=capital_curve.index[-1], freq="M"
            )
        )
        total_capital_injected = initial_capital + (monthly_injection * total_months)

        # Calculate final portfolio value and total return
        final_portfolio_value = portfolio_value_curve.iloc[-1]

        # Use the same total return calculation as performance_metrics
        total_return, _ = get_return(portfolio_value_curve, annualized=True)
        total_return_amount = (
            total_return * initial_capital
        )  # Convert percentage to amount

        # Calculate return contributions
        total_return_pct = total_return
        capital_contribution_pct = (
            total_capital_injected - initial_capital
        ) / initial_capital
        trading_contribution_pct = total_return_pct - capital_contribution_pct

        # Analyze stop losses and regular sells
        stop_loss_history = self.portfolio.stop_loss_history
        regular_sell_history = self.portfolio.sell_history

        def analyze_transactions(history):
            if not history:
                return 0, 0, 0

            total_proceeds = 0
            total_cost = 0
            count = 0

            for transactions in history.values():
                for details in transactions.values():
                    if isinstance(details, dict) and "proceeds" in details:
                        total_proceeds += details["proceeds"]
                        total_cost += details["costs"]
                        count += 1

            avg_proceeds = total_proceeds / count if count > 0 else 0
            return total_proceeds, avg_proceeds, count

        sl_total, sl_avg, sl_count = analyze_transactions(stop_loss_history)
        sell_total, sell_avg, sell_count = analyze_transactions(regular_sell_history)
        total_exits = sl_count + sell_count
        total_trading_proceeds = sl_total + sell_total

        # Calculate trading contribution percentages
        if total_trading_proceeds > 0:
            stop_loss_contribution_pct = (
                sl_total / total_trading_proceeds
            ) * trading_contribution_pct
            regular_sell_contribution_pct = (
                sell_total / total_trading_proceeds
            ) * trading_contribution_pct
        else:
            stop_loss_contribution_pct = 0
            regular_sell_contribution_pct = 0

        return {
            "capital_contribution": {
                "initial_capital": initial_capital,
                "total_capital_injected": total_capital_injected,
                "final_portfolio_value": final_portfolio_value,
                "total_return": total_return_amount,
                "return_on_capital": total_return,  # This is now the same as performance_metrics
                "capital_contribution_pct": capital_contribution_pct,
                "trading_contribution_pct": trading_contribution_pct,
            },
            "trading_activity": {
                "stop_loss": {
                    "count": sl_count,
                    "avg_proceeds": sl_avg,
                    "total_proceeds": sl_total,
                    "pct_of_exits": (sl_count / total_exits if total_exits > 0 else 0),
                    "contribution_to_return": stop_loss_contribution_pct,
                },
                "regular_sell": {
                    "count": sell_count,
                    "avg_proceeds": sell_avg,
                    "total_proceeds": sell_total,
                    "pct_of_exits": (
                        sell_count / total_exits if total_exits > 0 else 0
                    ),
                    "contribution_to_return": regular_sell_contribution_pct,
                },
            },
        }
