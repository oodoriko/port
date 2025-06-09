from collections import Counter, defaultdict

import numpy as np
import pandas as pd

from reporting.metrics_calculator import calculate_ir, calculate_sharpe, get_return


class PortfolioAnalytics:
    def __init__(
        self,
        portfolio,
        start_date,
        end_date,
        rf=0.02,
        bmk_returns=0.1,
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
        self.pnl_details_history = None

        self.portfolio_value_history = self.calculate_portfolio_value()
        self.cashflow_history = self.calculate_cashflow()
        self.transaction_cost_history = self.calculate_cost()
        self.pnl_history = self.calculate_pnl()
        self.pnl_details_history = self.calculate_daily_pnl()
        self.ticker_analysis = self.process_ticker_level_trades_data()

    def process_ticker_level_trades_data(self):
        if self.pnl_details_history is None:
            self.pnl_details_history = self.calculate_daily_pnl()

        pnl_by_ticker = defaultdict(dict)
        for date, pnls in self.pnl_details_history.items():
            for pnl in pnls:
                for ticker, pnl_detail in pnl.items():
                    pnl_by_ticker[ticker][date] = pnl_detail

        ticker_analysis = {}
        for ticker, pnls in pnl_by_ticker.items():
            average_holding_period = np.mean([pnl["holding_period"] for pnl in pnls.values()])
            average_return = np.mean([pnl["return"] for pnl in pnls.values()])
            average_profit = np.mean([pnl["profit"] for pnl in pnls.values()])
            total_long_trades = np.sum([pnl["total_long_trades"] for pnl in pnls.values()])
            total_short_trade = len(pnls)
            ticker_analysis[ticker] = {
                "average_holding_period": average_holding_period,
                "average_return": average_return,
                "average_profit": average_profit,
                "total_long_trades": total_long_trades,
                "total_short_trade": total_short_trade,
            }
        return ticker_analysis

    def calculate_cashflow(self):
        cashflow_history = {}
        for date, tickers_shares in self.portfolio.transaction_history.items():
            prices = self.open_prices.loc[date, tickers_shares.keys()]
            cf = np.sum(-1 * prices * list(tickers_shares.values()))
            cashflow_history[date] = cf
        return cashflow_history

    def calculate_pnl(self) -> dict:
        if self.pnl_details_history is None:
            self.pnl_details_history = self.calculate_daily_pnl()

        pnl_dollar = {}
        pnl_return = {}
        for date, pnls in self.pnl_details_history.items():
            pnl_dollar[date] = sum([pnl["profit"] for d in pnls for pnl in d.values()])
            pnl_return[date] = np.mean([pnl["return"] for d in pnls for pnl in d.values()])
        return pnl_dollar, pnl_return

    def calculate_portfolio_value(self) -> float:
        portfolio_value_history = {}  # -> need to add portfolio value at the beginning
        for date, tickers in self.portfolio.holdings_history.items():
            value = self.close_prices.loc[date, tickers.keys()]
            portfolio_value_history[date] = value.sum()
        return portfolio_value_history

    def calculate_cost(self):
        transaction_cost_history = {}
        for date, tickers_shares in self.portfolio.transaction_history.items():
            total_cost = self.portfolio.cost.calculate_transaction_costs(
                tickers_shares,
                volume=self.volumes.loc[date, tickers_shares.keys()],
                price=self.open_prices.loc[date, tickers_shares.keys()],
            )
            transaction_cost_history[date] = total_cost
        return transaction_cost_history

    def calculate_daily_pnl(self) -> dict:
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
                        existing_holding.get("cost_basis", 0) * existing_shares + buy_cost
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
                    profit = (price - existing_holding.get("cost_basis")) * abs(shares)
                    daily_pnl.append(
                        {
                            ticker: {
                                "holding_start_date": existing_holding.get(
                                    "holding_start_date", date
                                ),
                                "holding_period": pd.Timedelta(
                                    date - existing_holding.get("holding_start_date", date),
                                    unit="days",
                                ).days,
                                "cost_basis": existing_holding.get("cost_basis"),
                                "sell_price": price,
                                "profit": profit,
                                "total_long_trades": existing_holding.get("total_long"),
                                "return": profit / buy_cost,
                            }
                        }
                    )
                    del intermediate_holdings[ticker]
            pnl_details_history[date] = daily_pnl
        return pnl_details_history

    def holdings_metrics(self):
        return {d: len(holdings) for d, holdings in self.portfolio.holdings_history.items()}

    def performance_metrics(self, rf=0.02, bmk_returns=0.1):
        portfolio_value = pd.Series(self.portfolio_value_history)
        portfolio_value.index = pd.to_datetime(portfolio_value.index)
        portfolio_value.sort_index(inplace=True)

        total_return, annualized_return = get_return(portfolio_value, annualized=True)
        daily_returns = get_return(portfolio_value)
        monthly_returns = get_return(portfolio_value, freq="ME")
        quarterly_returns = get_return(portfolio_value, freq="QE")
        annual_returns = get_return(portfolio_value, freq="YE")

        # Sharpe Ratios -> ALL ARE BASED ON DAILY RETURNS
        annualized_sharpe = calculate_sharpe(daily_returns, rf, annualized=True)
        annual_sharpe = calculate_sharpe(daily_returns, freq="YE", rf=rf)
        monthly_sharpe = calculate_sharpe(daily_returns, freq="ME", rf=rf)  # min 10 days per month
        quarterly_sharpe = calculate_sharpe(daily_returns, freq="QE", rf=rf)

        # Information Ratios -> ALL ARE BASED ON DAILY RETURNS
        annualized_ir = calculate_ir(daily_returns, bmk_returns, annualized=True)
        annual_ir = calculate_ir(daily_returns, bmk_returns, freq="YE")
        monthly_ir = calculate_ir(daily_returns, bmk_returns, freq="ME")  # min 10 days per month
        quarterly_ir = calculate_ir(daily_returns, bmk_returns, freq="QE")

        # Win Rate metrics
        positive_days = (daily_returns > 0).sum()
        negative_days = (daily_returns < 0).sum()
        total_days = len(daily_returns)

        win_rate = positive_days / total_days if total_days > 0 else 0
        avg_win = daily_returns[daily_returns > 0].mean() if positive_days > 0 else 0
        avg_loss = abs(daily_returns[daily_returns < 0].mean()) if negative_days > 0 else 0

        # Correct profit factor calculation
        total_gains = daily_returns[daily_returns > 0].sum()
        total_losses = abs(daily_returns[daily_returns < 0].sum())
        profit_factor = total_gains / total_losses if total_losses != 0 else np.inf


        return {
            # Returns
            "total_return": total_return,
            "annualized_return": annualized_return,
            "monthly_returns": monthly_returns,
            "quarterly_returns": quarterly_returns,
            "annual_returns": annual_returns,
            "daily_returns": daily_returns,
            # Risk-Adjusted Returns
            "annualized_sharpe": annualized_sharpe,
            "annual_sharpe": annual_sharpe,
            "monthly_sharpe": monthly_sharpe,
            "quarterly_sharpe": quarterly_sharpe,
            # Information Ratios
            "annualized_ir": annualized_ir,
            "annual_ir": annual_ir,
            "monthly_ir": monthly_ir,
            "quarterly_ir": quarterly_ir,
            # Others
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
        }

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
        trades_by_ticker = pd.DataFrame([
            {
                "ticker": ticker,
                "buy": v["total_long_trades"],
                "sell": v["total_short_trade"],
                "duration": v["average_holding_period"],
                "return": v["average_return"],
                "profit": v["average_profit"],
            }
            for ticker, v in self.ticker_analysis.items()
        ])
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
            holding for holdings in self.portfolio.holdings_history.values() for holding in holdings
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
