from collections import Counter, defaultdict

import numpy as np
import pandas as pd

from portfolio.metrics_calculator import calculate_ir, calculate_sharpe, get_return


class PortfolioAnalytics:
    def __init__(
        self,
        portfolio,
        start_date,
        end_date,
        rf=0.02,
        bmk_returns=0.1,  # we need to source a real bmk
    ):
        self.portfolio = portfolio
        self.portfolio_value = portfolio.portfolio_value
        self.benchmark = portfolio.benchmark
        self.portfolio_setup = portfolio.setup
        self.universe = portfolio.universe
        self.product_data = portfolio.product_data
        self.open_prices = portfolio.open_prices
        self.close_prices = portfolio.close_prices
        self.volumes = portfolio.volumes
        self.start_date = start_date
        self.end_date = end_date
        self.rf = rf
        self.bmk_returns = bmk_returns
        self.portfolio_value, self.portfolio_value_history = (
            self._calculate_portfolio_value()
        )

    def holdings_metrics(self):
        return {
            d: len(holdings) for d, holdings in self.portfolio.holdings_history.items()
        }

    def _calculate_portfolio_value(self) -> float:
        portfolio_value_history = {}
        for date, tickers in self.portfolio.holdings_history.items():
            value = self.close_prices.loc[date, tickers.keys()]
            portfolio_value_history[date] = value.sum()
        portfolio_value = pd.Series(portfolio_value_history)
        portfolio_value.index = pd.to_datetime(portfolio_value.index)
        portfolio_value.sort_index(inplace=True)
        return portfolio_value, portfolio_value_history

    def performance_metrics(self, rf=0.02, bmk_returns=0.1):
        portfolio_value = pd.Series(self.portfolio_value_history)
        portfolio_value.index = pd.to_datetime(portfolio_value.index)
        portfolio_value.sort_index(inplace=True)

        total_return, annualized_return = get_return(portfolio_value, annualized=True)
        daily_returns = get_return(portfolio_value)
        annualized_sharpe = calculate_sharpe(daily_returns, rf, annualized=True)
        annualized_ir = calculate_ir(daily_returns, bmk_returns, annualized=True)

        return {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "daily_returns": daily_returns,
            "annualized_sharpe": annualized_sharpe,
            "annualized_ir": annualized_ir,
        }


class AdvancedPortfolioAnalytics(PortfolioAnalytics):
    def __init__(self, portfolio, start_date, end_date, rf=0.02, bmk_returns=0.1):
        super().__init__(portfolio, start_date, end_date, rf, bmk_returns)

        self.cashflow_history = self._calculate_cashflow()
        self.transaction_cost_history = self._calculate_cost()
        self.pnl_details_history = self._calculate_daily_pnl()
        self.pnl_history = self._calculate_pnl()
        self.pnl_by_ticker = self._process_ticker_level_trades_data()
        self.ticker_analysis = self._process_ticker_level_trades_data()

    def performance_metrics(self, rf=0.02, bmk_returns=0.1):
        result = super().performance_metrics(rf, bmk_returns)

        # Use the daily_returns from the parent class result
        daily_returns = result["daily_returns"]

        monthly_returns = get_return(self.portfolio_value, freq="ME")
        quarterly_returns = get_return(self.portfolio_value, freq="QE")
        annual_returns = get_return(self.portfolio_value, freq="YE")

        monthly_sharpe = calculate_sharpe(
            daily_returns, freq="ME", rf=rf
        )  # min 10 days per month
        quarterly_sharpe = calculate_sharpe(daily_returns, freq="QE", rf=rf)

        monthly_ir = calculate_ir(
            daily_returns, bmk_returns, freq="ME"
        )  # min 10 days per month
        quarterly_ir = calculate_ir(daily_returns, bmk_returns, freq="QE")

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
        for date, trades in self.portfolio.transaction_history.items():
            trades_arr = np.array(list(trades.values()))
            long_trades = (trades_arr > 0).sum()
            short_trades = (trades_arr < 0).sum()
            trades_ts[date] = {
                "buy": long_trades,
                "sell": short_trades,
            }
        trades_by_ticker = pd.DataFrame(
            [
                {
                    "ticker": ticker,
                    "buy": v["total_long_trades"],
                    "sell": v["total_short_trade"],
                    "duration": v["average_holding_period"],
                    "return": v["average_return"],
                    "profit": v["average_profit"],
                }
                for ticker, v in self.ticker_analysis.items()
            ]
        )
        trading_status_count = Counter(self.portfolio.trading_status.values())

        return {
            "trades_ts": trades_ts,  # {date: {buy: int, sell: int}}
            "trades_by_ticker": trades_by_ticker,
            "cancelled_trades_count": trading_status_count.get(-1, 0),
            "no_trades_count": trading_status_count.get(0, 0),
            "successful_trades_count": trading_status_count.get(1, 0),
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

    def _process_ticker_level_trades_data(self):
        if self.pnl_details_history is None:
            self.pnl_details_history = self._calculate_daily_pnl()

        pnl_by_ticker = defaultdict(dict)
        for date, pnls in self.pnl_details_history.items():
            for pnl in pnls:
                for ticker, pnl_detail in pnl.items():
                    pnl_by_ticker[ticker][date] = pnl_detail

        ticker_analysis = {}
        for ticker, pnls in pnl_by_ticker.items():
            average_holding_period = np.mean(
                [pnl["holding_period"] for pnl in pnls.values()]
            )

            # Handle potential NaN/inf values in returns
            returns = [pnl["return"] for pnl in pnls.values()]
            valid_returns = [r for r in returns if np.isfinite(r)]
            average_return = np.mean(valid_returns) if valid_returns else 0.0

            average_profit = np.mean([pnl["profit"] for pnl in pnls.values()])
            total_long_trades = np.sum(
                [pnl["total_long_trades"] for pnl in pnls.values()]
            )
            total_short_trade = len(pnls)
            ticker_analysis[ticker] = {
                "average_holding_period": average_holding_period,
                "average_return": average_return,
                "average_profit": average_profit,
                "total_long_trades": total_long_trades,
                "total_short_trade": total_short_trade,
            }
        return ticker_analysis

    def _calculate_cashflow(self):
        cashflow_history = {}
        for date, tickers_shares in self.portfolio.transaction_history.items():
            prices = self.open_prices.loc[date, tickers_shares.keys()]
            cf = np.sum(-1 * prices * list(tickers_shares.values()))
            cashflow_history[date] = cf
        return cashflow_history

    def _calculate_pnl(self) -> dict:
        if self.pnl_details_history is None:
            self.pnl_details_history = self._calculate_daily_pnl()

        pnl_dollar = {}
        pnl_return = {}
        for date, pnls in self.pnl_details_history.items():
            pnl_dollar[date] = sum([pnl["profit"] for d in pnls for pnl in d.values()])

            # Handle potential NaN/inf values in daily returns
            daily_returns = [pnl["return"] for d in pnls for pnl in d.values()]
            valid_daily_returns = [r for r in daily_returns if np.isfinite(r)]
            pnl_return[date] = (
                np.mean(valid_daily_returns) if valid_daily_returns else 0.0
            )
        return pnl_dollar, pnl_return

    def _calculate_cost(self):
        transaction_cost_history = {}
        for date, tickers_shares in self.portfolio.transaction_history.items():
            total_cost = self.portfolio.cost.calculate_transaction_costs(
                tickers_shares,
                volume=self.volumes.loc[date, tickers_shares.keys()],
                price=self.open_prices.loc[date, tickers_shares.keys()],
            )
            transaction_cost_history[date] = total_cost
        return transaction_cost_history

    def _calculate_daily_pnl(self) -> dict:
        """pnl is only calculated when there is a sell trade, adding holdings alone doesn't generate pnl"""
        pnl_details_history = {}
        intermediate_holdings = {}
        for date, tickers_shares in self.portfolio.transaction_history.items():
            prices = self.open_prices.loc[date, tickers_shares.keys()]
            daily_pnl = []
            for ticker, shares in tickers_shares.items():
                existing_holding = intermediate_holdings.get(ticker, {})
                existing_shares = existing_holding.get("shares_hold", 0)
                price = prices[ticker]
                if shares > 0:  # buy trade
                    buy_cost = shares * price
                    new_cost_basis = (
                        existing_holding.get("cost_basis", 0) * existing_shares
                        + buy_cost
                    ) / (existing_shares + shares)
                    intermediate_holdings[ticker] = {
                        "holding_start_date": (
                            date
                            if len(existing_holding) == 0
                            else existing_holding.get("holding_start_date", date)
                        ),
                        "cost_basis": new_cost_basis,
                        "shares_hold": existing_shares + shares,
                        "total_long": existing_holding.get("total_long", 0) + 1,
                    }
                elif shares < 0:  # sell trade
                    if len(existing_holding) == 0:
                        continue

                    cost_basis = existing_holding.get("cost_basis", 0)
                    profit = (price - cost_basis) * abs(shares)

                    # Calculate return properly: (sell_price - cost_basis) / cost_basis
                    # Handle division by zero
                    if cost_basis != 0:
                        return_pct = (price - cost_basis) / cost_basis
                    else:
                        return_pct = 0.0  # or handle as appropriate for your logic

                    daily_pnl.append(
                        {
                            ticker: {
                                "holding_start_date": existing_holding.get(
                                    "holding_start_date", date
                                ),
                                "holding_period": pd.Timedelta(
                                    date
                                    - existing_holding.get("holding_start_date", date),
                                    unit="days",
                                ).days,
                                "cost_basis": cost_basis,
                                "sell_price": price,
                                "profit": profit,
                                "total_long_trades": existing_holding.get(
                                    "total_long", 0
                                )
                                + 1,
                                "return": return_pct,
                            }
                        }
                    )
                    del intermediate_holdings[ticker]
            pnl_details_history[date] = daily_pnl
        return pnl_details_history
