from collections import Counter, defaultdict

import numpy as np
import pandas as pd

from portfolio.metrics_calculator import calculate_ir, calculate_sharpe, get_return
from portfolio.portfolio import ExitReason


class PortfolioAnalytics:
    def __init__(
        self,
        portfolio,
        rf=0.02,
        bmk_returns=0.1,  # we need to source a real bmk
        trading_dates=None,
    ):
        self.portfolio = portfolio

        self.product_data = portfolio.product_data
        self.rf = rf
        self.bmk_returns = bmk_returns
        self.trading_dates = trading_dates

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
    def __init__(self, portfolio, rf=0.02, bmk_returns=0.1, trading_dates=None):
        super().__init__(portfolio, rf, bmk_returns, trading_dates)

        self.cashflow_stats_ts, self.ticker_level_records_ts = (
            self._process_trades_data()
        )
        # self.cashflow_history = self._calculate_cashflow()
        # self.transaction_cost_history = self._calculate_cost()
        # self.pnl_details_history = self._calculate_daily_pnl()
        # self.pnl_history = self._calculate_pnl()
        # self.pnl_by_ticker = self._process_ticker_level_trades_data()
        # self.ticker_analysis = self._process_ticker_level_trades_data()

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

    def ticker_metrics(self):
        holdings_by_ticker = defaultdict(dict)
        for date, holdings in self.portfolio.holdings_history.items():
            for ticker, position in holdings.items():
                holdings_by_ticker[ticker][date] = position
        return holdings_by_ticker

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
        for ticker, trades in self.ticker_level_records_ts.items():
            df = pd.DataFrame(trades).T
            ticker_metrics.append(
                {
                    "ticker": ticker,
                    "buy": df["total_long_trades"].sum(),
                    "sell": len(df),
                    "duration": df["holding_period"].mean(),
                    "return": df["return"].mean(),
                    "profit": df["profit"].mean(),
                    "stop_loss_count": df[
                        df["exit_reason"] == ExitReason.STOP_LOSS
                    ].shape[0],
                    
                }
            )
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
        }

    def sector_metrics(self):
        total_unique_holdings = set(
            holding
            for holdings in self.portfolio.holdings_history.values()
            for holding in holdings
        )
        filtered_product_data = self.product_data[
            self.product_data.ticker.isin(total_unique_holdings)
        ]
        # Sector
        sector_ts = []
        sectors = filtered_product_data.sector.unique()
        for holdings in self.portfolio.holdings_history.values():
            prd = filtered_product_data[filtered_product_data.ticker.isin(holdings)]
            sector_counts = prd.groupby("sector").size()
            sectors_dict = {sector: sector_counts.get(sector, 0) for sector in sectors}
            sector_ts.append(sectors_dict)

        return {
            "sector_ts": sector_ts,
        }

    def _get_cashflow_curve(self) -> dict:
        transaction_costs_ts = {
            d: k["transaction_costs"] for d, k in self.cashflow_stats_ts.items()
        }
        sell_proceeds_ts = {
            d: k["sell_proceeds"] for d, k in self.cashflow_stats_ts.items()
        }
        purchase_proceeds_ts = {
            d: k["purchase_proceeds"] for d, k in self.cashflow_stats_ts.items()
        }
        return {
            "transaction_costs_ts": transaction_costs_ts,
            "sell_proceeds_ts": sell_proceeds_ts,
            "purchase_proceeds_ts": purchase_proceeds_ts,
        }

    def _get_pnl_curve(self) -> dict:
        realized_gain_sell_ts = {
            d: k["realized_gain_sell"] for d, k in self.cashflow_stats_ts.items()
        }
        realized_loss_sell_ts = {
            d: k["realized_loss_sell"] for d, k in self.cashflow_stats_ts.items()
        }
        realized_gain_stop_loss_ts = {
            d: k["realized_gain_stop_loss"] for d, k in self.cashflow_stats_ts.items()
        }
        realized_loss_stop_loss_ts = {
            d: k["realized_loss_stop_loss"] for d, k in self.cashflow_stats_ts.items()
        }
        return {
            "realized_gain_sell_ts": realized_gain_sell_ts,
            "realized_loss_sell_ts": realized_loss_sell_ts,
            "realized_gain_stop_loss_ts": realized_gain_stop_loss_ts,
            "realized_loss_stop_loss_ts": realized_loss_stop_loss_ts,
        }

    def _process_trades_data(self):
        all_positions = []
        all_transactions = []

        for date in self.trading_dates:
            for ticker, sell_record in self.portfolio.sell_history.get(
                date, {}
            ).items():
                closed_positions = self.portfolio.closed_positions.get(date, {}).get(
                    ticker, []
                )
                if not closed_positions:
                    raise ValueError(
                        f"Ticker {ticker} has no closed positions on date {date} but has sell record"
                    )

                for pos in closed_positions:
                    all_positions.append(
                        {
                            "date": pd.to_datetime(date),
                            "ticker": ticker,
                            "entry_date": pd.to_datetime(pos.entry_date),
                            "entry_price": pos.entry_price,
                            "entry_shares": pos.entry_shares,
                            "exit_date": pd.to_datetime(pos.exit_date),
                            "exit_price": pos.exit_price,
                            "exit_shares": pos.exit_shares,
                            "exit_reason": pos.exit_reason,
                        }
                    )

                stop_loss_sell = self.portfolio.stop_loss_history.get(date, {}).get(
                    ticker, {}
                )
                all_transactions.append(
                    {
                        "date": pd.to_datetime(date),
                        "ticker": ticker,
                        "transaction_costs": sell_record["transaction_costs"]
                        + stop_loss_sell.get("transaction_costs", 0),
                        "sell_proceeds": sell_record["sell_proceeds"]
                        + stop_loss_sell.get("sell_proceeds", 0),
                        "purchase_proceeds": 0,
                    }
                )

            for ticker, buy_record in self.portfolio.buy_history.get(date, {}).items():
                all_transactions.append(
                    {
                        "date": pd.to_datetime(date),
                        "ticker": ticker,
                        "transaction_costs": buy_record["transaction_costs"],
                        "sell_proceeds": 0,
                        "purchase_proceeds": buy_record["purchase_proceeds"],
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
                if row["exit_reason"] == ExitReason.SELL:
                    return max(pnl, 0), min(pnl, 0), 0, 0
                elif row["exit_reason"] == ExitReason.STOP_LOSS:
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
                        "entry_shares": "sum",
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
                    }
                )
                .reset_index()
            )

            grouped["holding_period"] = (
                grouped["exit_date"] - grouped["entry_date"]
            ).dt.days

            daily_pnl = grouped.groupby("date").agg(
                {
                    "realized_gain_sell": "sum",
                    "realized_loss_sell": "sum",
                    "realized_gain_stop_loss": "sum",
                    "realized_loss_stop_loss": "sum",
                    "realized_return": "sum",
                }
            )

            ticker_level_records_ts = defaultdict(dict)
            for _, row in grouped.iterrows():
                ticker_level_records_ts[row["ticker"]][row["date"]] = {
                    "holding_start_date": row["entry_date"],
                    "holding_end_date": row["exit_date"],
                    "holding_period": row["holding_period"],
                    "cost_basis": row["entry_price"],
                    "total_long_trades": 1,
                    "profit": row["realized_return"],
                    "return": row["realized_return_pct"],
                    "exit_reason": row["exit_reason"],
                }

        if not transactions_df.empty:
            cashflow_stats = (
                transactions_df.groupby("date")
                .agg(
                    {
                        "transaction_costs": "sum",
                        "sell_proceeds": "sum",
                        "purchase_proceeds": "sum",
                    }
                )
                .to_dict("index")
            )

            cashflow_stats_ts = defaultdict(
                lambda: {
                    "profit": 0,
                    "transaction_costs": 0,
                    "sell_proceeds": 0,
                    "purchase_proceeds": 0,
                    "realized_gain_sell": 0,
                    "realized_loss_sell": 0,
                    "realized_gain_stop_loss": 0,
                    "realized_loss_stop_loss": 0,
                }
            )

            for date, stats in cashflow_stats.items():
                cashflow_stats_ts[date].update(stats)
                if date in daily_pnl.index:
                    pnl_stats = daily_pnl.loc[date]
                    cashflow_stats_ts[date].update(
                        {
                            "profit": pnl_stats["realized_return"],
                            "realized_gain_sell": pnl_stats["realized_gain_sell"],
                            "realized_loss_sell": pnl_stats["realized_loss_sell"],
                            "realized_gain_stop_loss": pnl_stats[
                                "realized_gain_stop_loss"
                            ],
                            "realized_loss_stop_loss": pnl_stats[
                                "realized_loss_stop_loss"
                            ],
                        }
                    )
        return cashflow_stats_ts, ticker_level_records_ts"
