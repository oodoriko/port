import io
import os
from datetime import datetime
from io import BytesIO

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from reporting.report_styling import Colors, ReportStyling, StyleUtility


class SimpleReportGenerator:
    def __init__(self, portfolio_analytics, dpi=300):
        self.analytics = portfolio_analytics
        self.portfolio = portfolio_analytics.portfolio
        self.portfolio_name = self.portfolio.name or "Unnamed Portfolio"
        self.dpi = dpi
        self.run_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Initialize styling
        self.styles = getSampleStyleSheet()
        self.styling = ReportStyling(dpi=self.dpi)
        self.style_utility = StyleUtility()

        # order matters!
        self.get_metrics()
        self.extract_portfolio_data()
        self._cache_portfolio_data()

        # Initialize styles
        self.title_page_title_style = self.style_utility.create_title_page_title_style()
        self.section_title_style = self.style_utility.create_section_title_style()
        self.normal_style = self.style_utility.create_normal_style()
        self.footer_info_style = self.style_utility.create_footer_info_style()
        self.section_header_style = self.style_utility.create_section_header_style()
        self.base_table_title_style = self.style_utility.create_base_table_title_style()

    def _cache_portfolio_data(self):
        """Cache processed portfolio data to avoid redundant processing"""
        # Cache portfolio value as pandas Series (used in multiple charts)
        self.portfolio_value_series = pd.Series(self.curves["portfolio_value_curve"])
        self.portfolio_value_series.index = pd.to_datetime(
            self.portfolio_value_series.index
        )
        self.portfolio_value_series = self.portfolio_value_series.sort_index()

        # Cache monthly resampled data
        self.monthly_portfolio_value = self.portfolio_value_series.resample("ME").last()
        self.monthly_returns = self.monthly_portfolio_value.pct_change().dropna()

        # Cache holdings data as pandas Series
        self.holdings_series = pd.Series(self.curves["holdings_curve"])
        self.holdings_series.index = pd.to_datetime(self.holdings_series.index)
        self.holdings_series = self.holdings_series.sort_index()
        self.monthly_holdings = self.holdings_series.resample("ME").mean()

    def extract_portfolio_data(self):
        self.dates = list(self.curves["portfolio_value_curve"].keys())

        self.start_date = min(self.dates)
        self.end_date = max(self.dates)
        self.start_date_str = pd.to_datetime(self.start_date).strftime("%Y-%m-%d")
        self.end_date_str = pd.to_datetime(self.end_date).strftime("%Y-%m-%d")
        self.benchmark_text = self.portfolio.benchmark

        config_data = {}
        for k, v in self.portfolio.setup.items():
            if k == "initial_holdings" and (v == {} or not v):
                config_data[k] = "None"
            elif k in ["excluded_sectors", "included_countries"]:
                config_data[k] = ", ".join([s.value for s in v])
            else:
                config_data[k] = v

        config_data.update(self.portfolio.constraints.get_constraints())
        self.portfolio_config = config_data

    def get_metrics(self):
        self.curves = {}

        self.curves.update(self.analytics.get_cashflow_curve())
        self.curves.update(self.analytics.get_pnl_curve())
        self.curves["portfolio_value_curve"] = self.analytics.portfolio_value_curve
        self.curves["capital_curve"] = self.analytics.capital_curve
        self.curves["holdings_curve"] = self.analytics.holdings_curve

        self.metrics = self.analytics.performance_metrics()
        self.signal_metrics = self.analytics.signal_metrics_ts()

        sector_metrics = self.analytics.sector_metrics()
        self.sector_ts = sector_metrics["sector_ts"]
        self.sector_trading_data = sector_metrics["sector_trading_data"]
        del sector_metrics

        trading_metrics = self.analytics.trading_metrics()
        self.trades_by_ticker = trading_metrics["trades_by_ticker"]
        self.curves["trades_ts"] = trading_metrics["trades_ts"]
        self.no_signal_days = trading_metrics["no_signal_days"]
        self.sell_trades_metrics = trading_metrics["sell_trades_metrics"]
        self.stop_loss_trades_metrics = trading_metrics["stop_loss_trades_metrics"]
        self.max_drawdown_trades_metrics = trading_metrics[
            "max_drawdown_trades_metrics"
        ]
        del trading_metrics

        self.contribution_metrics = self.analytics.contribution_metrics()

    def create_key_performance_data(self) -> dict[str, float]:
        """Create performance metrics for display"""
        performance_data = {
            "Total Return": f"{self.metrics['total_return']:.2%}",
            "Annualized Return": f"{self.metrics['annualized_return']:.2%}",
            "Sharpe Ratio": f"{self.metrics['annualized_sharpe']:.2f}",
            "Information Ratio": f"{self.metrics['annualized_ir']:.2f}",
            "Win Rate": f"{self.metrics['win_rate']:.2%}",
            "Daily Avg Win": f"{self.metrics['avg_win']:.2%}",
            "Benchmark Return": f"{self.analytics.bmk_returns:.2f}",
            "Risk-Free Rate": f"{self.analytics.rf:.2f}",
        }
        return performance_data

    def create_portfolio_info_footer(self) -> Paragraph:
        """Create portfolio info footer for each page"""
        period = f"{self.start_date_str} to {self.end_date_str}"
        info_text = f"{self.portfolio_name} | Benchmark: {self.benchmark_text} | Run Date: {self.run_date} | Period: {period}"
        return Paragraph(info_text, self.footer_info_style)

    def create_title_page(self, report_name: str = None) -> list:
        """Create the title page (Page 1)"""
        story = []
        story.append(Spacer(1, 2.5 * inch))
        story.append(
            Paragraph(report_name or self.portfolio_name, self.title_page_title_style)
        )

        info_style = ParagraphStyle(
            "TitlePageInfo",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=16,
            spaceAfter=20,
            spaceBefore=10,
            textColor=Colors.CHARCOAL,
            alignment=TA_CENTER,
            leading=20,
        )

        story.append(Paragraph(f"<b>Benchmark:</b> {self.benchmark_text}", info_style))
        story.append(
            Paragraph(
                f"<b>Analysis Period:</b> {self.start_date_str} to {self.end_date_str}",
                info_style,
            )
        )
        story.append(Paragraph(f"<b>Report Runtime:</b> {self.run_date}", info_style))
        return story

    def create_section_title_page(self, section_name: str) -> list:
        """Create a section title page"""
        story = []
        story.append(Spacer(1, 3 * inch))
        story.append(Paragraph(section_name, self.section_title_style))
        return story

    def create_portfolio_overview_page_config_and_metrics(self) -> list:
        """Create portfolio setup and key metrics page (Page 2)"""
        story = []

        config_data = self.portfolio_config
        performance_data = self.create_key_performance_data()

        config_elements = self.styling.create_formatted_list(
            config_data, "Portfolio Configuration"
        )
        performance_elements = self.styling.create_formatted_list(
            performance_data, "Key Performance Metrics"
        )

        # Calculate equal column widths for balanced layout
        total_width = landscape(A4)[0] - 1.5 * inch  # Account for page margins
        section_width = total_width * 0.45  # 45% each for config and performance

        # Create the main combined table with two columns
        max_rows = max(len(config_elements), len(performance_elements))
        combined_data = []

        for i in range(max_rows):
            config_item = config_elements[i] if i < len(config_elements) else ""
            performance_item = (
                performance_elements[i] if i < len(performance_elements) else ""
            )
            combined_data.append([config_item, performance_item])

        combined_table = Table(combined_data, colWidths=[section_width, section_width])
        combined_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    (
                        "LINEAFTER",
                        (0, 0),
                        (0, -1),
                        2,
                        Colors.SLATE_BLUE,
                    ),  # Vertical divider line
                    ("LEFTPADDING", (0, 0), (-1, -1), 20),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 20),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )

        story.append(combined_table)
        return story

    def create_portfolio_overview_page_performance(self, **kwargs):
        # Use cached portfolio value data
        portfolio_value_dict = {
            date.strftime("%Y-%m-%d"): value
            for date, value in self.monthly_portfolio_value.items()
        }

        # Use cached monthly returns data
        monthly_returns_dict = {
            date.strftime("%Y-%m-%d"): value * 100  # Convert to percentage
            for date, value in self.monthly_returns.items()
        }

        # Use cached holdings data
        holdings_dict = {
            date.strftime("%Y-%m-%d"): value
            for date, value in self.monthly_holdings.items()
        }

        # Use the enhanced generic dual axis function
        return self.styling.create_generic_dual_axis_chart(
            data_dict_left=portfolio_value_dict,
            data_dict_right=monthly_returns_dict,
            left_y_label="Portfolio Value ($)",
            right_y_label="Monthly Returns (%)",
            right_linestyle="--",
            right_color=Colors.CHART_RED,
            figsize=(12, 8),
            resample_freq="M",
            no_data_message="No portfolio performance data available",
            normal_style=self.normal_style,
            show_crisis_periods=True,
            interval=max(1, len(self.monthly_portfolio_value) // 12),
            graph_type="M",
            # Bar chart parameters
            bar_data_dict=holdings_dict,
            bar_label="Holdings Count",
            bar_color="lightgray",
            right_axis_zero_line=True,  # Add zero line for returns
            **kwargs,
        )

    def create_monthly_return_distribution_chart(self) -> BytesIO:
        """Create monthly return distribution chart using existing styling"""
        return self.styling.create_generic_distribution_chart(
            metrics=self.metrics,
            data_key="monthly_returns",
            bins=20,
            color=Colors.CHART_GOLD,
            median_color=Colors.CHART_DEEP_BLUE,
            normal_style=self.normal_style,
        )

    def create_monthly_sharpe_ir_chart(self, **kwargs):
        """Create monthly Sharpe and Information Ratio dual axis chart"""

        # Prepare monthly Sharpe data - assuming pandas Series with date index
        monthly_sharpe_dict = {}
        if (
            "monthly_sharpe" in self.metrics
            and self.metrics["monthly_sharpe"] is not None
            and len(self.metrics["monthly_sharpe"]) > 0
        ):
            sharpe_series = self.metrics["monthly_sharpe"]
            # Convert pandas Series to dictionary with string dates
            for date_idx, value in sharpe_series.items():
                date_str = date_idx.strftime("%Y-%m-%d")
                monthly_sharpe_dict[date_str] = value

        # Prepare monthly IR data - assuming pandas Series with date index
        monthly_ir_dict = {}
        if (
            "monthly_ir" in self.metrics
            and self.metrics["monthly_ir"] is not None
            and len(self.metrics["monthly_ir"]) > 0
        ):
            ir_series = self.metrics["monthly_ir"]
            # Convert pandas Series to dictionary with string dates
            for date_idx, value in ir_series.items():
                date_str = date_idx.strftime("%Y-%m-%d")
                monthly_ir_dict[date_str] = value

        # Calculate smart interval based on data length to avoid overcrowded x-axis
        data_length = max(len(monthly_sharpe_dict), len(monthly_ir_dict))
        if data_length <= 12:  # 1 year or less
            interval = 1
        elif data_length <= 36:  # 3 years or less
            interval = 3
        elif data_length <= 60:  # 5 years or less
            interval = 6
        else:  # More than 5 years
            interval = 12

        return self.styling.create_generic_dual_axis_chart(
            data_dict_left=monthly_sharpe_dict,
            data_dict_right=monthly_ir_dict,
            left_y_label="Sharpe Ratio",
            right_y_label="Information Ratio",
            left_color="black",
            right_color="red",
            right_linestyle=":",
            figsize=(10, 5.5),  # Reduced height to accommodate legend below
            resample_freq="M",
            no_data_message="No monthly Sharpe/IR data available",
            normal_style=self.normal_style,
            show_crisis_periods=True,
            interval=interval,
            graph_type="M",
            **kwargs,
        )

    def create_top_return_tables(self) -> tuple[Table, Table]:
        """Create tables for top 10 highest and lowest average return tickers"""
        # Use cached trading data
        if self.trades_by_ticker.empty:
            return None, None

        # Top 10 highest average returns
        top_returns = self.trades_by_ticker.nlargest(10, "return")[
            ["ticker", "return", "return_net_of_cost"]
        ]
        highest_data = [["Ticker", "Avg\nReturn", "Avg Return\nafter cost"]]
        for _, row in top_returns.iterrows():
            return_pct = f"{row['return']:.2%}" if pd.notna(row["return"]) else "N/A"
            return_net_of_cost_pct = (
                f"{row['return_net_of_cost']:.2%}"
                if pd.notna(row["return_net_of_cost"])
                else "N/A"
            )
            highest_data.append(
                [str(row["ticker"]), return_pct, return_net_of_cost_pct]
            )

        highest_table = self.styling.create_styled_table(
            data=highest_data,
            column_widths=[1.8 * inch, 1.8 * inch, 1.8 * inch],
            header_color=Colors.SLATE_BLUE,
            custom_styles=[
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ],
        )

        # Top 10 lowest average returns
        lowest_returns = self.trades_by_ticker.nsmallest(10, "return")[
            ["ticker", "return", "return_net_of_cost"]
        ]
        lowest_data = [["Ticker", "Avg\nReturn", "Avg Return\nafter cost"]]
        for _, row in lowest_returns.iterrows():
            return_pct = f"{row['return']:.2%}" if pd.notna(row["return"]) else "N/A"
            return_net_of_cost_pct = (
                f"{row['return_net_of_cost']:.2%}"
                if pd.notna(row["return_net_of_cost"])
                else "N/A"
            )
            lowest_data.append([str(row["ticker"]), return_pct, return_net_of_cost_pct])

        lowest_table = self.styling.create_styled_table(
            data=lowest_data,
            column_widths=[1.8 * inch, 1.8 * inch, 1.8 * inch],
            header_color=Colors.EMERALD,
            custom_styles=[
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ],
        )

        return highest_table, lowest_table

    def create_holdings_summary_table(self) -> Table:
        """Create holdings summary table with professional styling"""
        if not self.curves["holdings_curve"]:
            return None

        holdings_dates = list(self.curves["holdings_curve"].keys())
        holdings_counts = list(self.curves["holdings_curve"].values())
        holdings_counts_arr = np.array(holdings_counts)
        non_zero_mask = holdings_counts_arr > 0

        if np.any(non_zero_mask):
            min_holdings_idx = np.argmin(
                np.where(non_zero_mask, holdings_counts_arr, np.inf)
            )
            min_holdings = holdings_counts[min_holdings_idx]
            min_date = holdings_dates[min_holdings_idx]
        else:
            min_holdings = min(holdings_counts)
            min_date = holdings_dates[holdings_counts.index(min_holdings)]

        # Find max and min
        avg_holdings = sum(holdings_counts) / len(holdings_counts)
        max_holdings = max(holdings_counts)
        max_date = holdings_dates[holdings_counts.index(max_holdings)]

        summary_data = [
            ["Metric", "Value", "Date"],
            [
                "Maximum Holdings",
                f"{max_holdings}",
                str(pd.to_datetime(max_date).date()),
            ],
            [
                "Minimum Non-zero Holdings",
                f"{min_holdings}",
                str(pd.to_datetime(min_date).date()),
            ],
            ["Average Holdings", f"{avg_holdings:.1f}", "Daily"],
            ["Universe Size", f"{len(self.portfolio.universe)}", ""],
        ]

        return self.styling.create_styled_table(
            data=summary_data,
            column_widths=[2.2 * inch, 1.8 * inch, 2.5 * inch],
            header_color=Colors.SLATE_BLUE,
        )

    def create_holding_duration_summary_table(self) -> Table:
        """Create holding duration summary table with professional styling"""
        durations = self.trades_by_ticker["duration"].dropna()

        if len(durations) == 0:
            return None

        max_duration = durations.max()
        min_duration = durations.min()
        avg_duration = durations.mean()

        duration_data = [
            ["Duration Metric", "Days", ""],
            ["Maximum Duration", f"{max_duration:.1f}", ""],
            ["Minimum Duration", f"{min_duration:.1f}", ""],
            ["Average Duration", f"{avg_duration:.1f}", ""],
        ]

        return self.styling.create_styled_table(
            data=duration_data,
            column_widths=[2.2 * inch, 1.8 * inch, 2.5 * inch],
            header_color=Colors.SLATE_BLUE,
        )

    def create_holdings_analysis_chart(self) -> BytesIO:
        """Create holdings over time chart with maximum possible holdings reference line"""
        # Calculate interval for chart formatting
        interval = (
            1
            if len(self.curves["holdings_curve"]) // 365 <= 2
            else (
                3
                if len(self.curves["holdings_curve"]) // 365 > 2
                and len(self.curves["holdings_curve"]) // 365 <= 5
                else 4
            )
        )

        return self.styling.create_generic_line_chart(
            data_dict=self.curves["holdings_curve"],
            title="Holdings Over Time",
            color=Colors.CHART_NAVY,
            linewidth=1,
            resample_freq=None,
            no_data_message="No holdings data available",
            normal_style=self.normal_style,
            show_crisis_periods=True,
            interval=interval,
            graph_type="D",
            y_label="Number of Holdings",
        )

    def create_top_duration_tables(self) -> tuple[Table, Table]:
        duration_df = self.trades_by_ticker
        longest_durations = duration_df.nlargest(10, "duration")[
            ["ticker", "duration", "return", "return_net_of_cost"]
        ]
        longest_data = [["Ticker", "Duration (Days)", "Return", "Return after cost"]]
        for _, row in longest_durations.iterrows():
            longest_data.append(
                [
                    str(row["ticker"]),
                    f"{row['duration']:.1f}",
                    f"{row['return']:.2%}",
                    f"{row['return_net_of_cost']:.2%}",
                ]
            )

        longest_table = self.styling.create_styled_table(
            data=longest_data,
            column_widths=[1 * inch, 1 * inch, 1.8 * inch, 1.8 * inch],
            header_color=Colors.SLATE_BLUE,
            custom_styles=[
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ],
        )

        # Top 10 shortest durations
        shortest_durations = duration_df.nsmallest(10, "duration")[
            ["ticker", "duration", "return", "return_net_of_cost"]
        ]
        shortest_data = [["Ticker", "Duration (Days)", "Return", "Return after cost"]]
        for _, row in shortest_durations.iterrows():
            shortest_data.append(
                [
                    str(row["ticker"]),
                    f"{row['duration']:.1f}",
                    f"{row['return']:.2%}",
                    f"{row['return_net_of_cost']:.2%}",
                ]
            )

        shortest_table = self.styling.create_styled_table(
            data=shortest_data,
            column_widths=[1 * inch, 1 * inch, 1.8 * inch, 1.8 * inch],
            header_color=Colors.EMERALD,
            custom_styles=[
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ],
        )

        return longest_table, shortest_table

    def create_trading_analysis_summary_table(self) -> Table:
        trades_ts = self.curves["trades_ts"]
        trades_df = pd.DataFrame(list(trades_ts.values()))

        total_trading_days = len(trades_df)
        avg_buy_trades_per_day = trades_df["buy"].mean()
        avg_sell_trades_per_day = trades_df["sell"].mean()
        avg_no_short_day = trades_df["no_short"].mean()
        avg_insufficient_capital_per_day = trades_df["insufficient_capital"].mean()
        avg_stop_loss_per_day = trades_df["stop_loss"].mean()

        total_sell_trades = sum(
            [len(trades) for trades in self.sell_trades_metrics.values()]
        )
        positive_return_sell_trades = (
            len(
                [
                    trade["return"]
                    for trades in self.sell_trades_metrics.values()
                    for trade in trades
                    if trade["return"] > 0
                ]
            )
            / total_sell_trades
        )
        positive_return_after_cost_sell_trades = (
            len(
                [
                    trade["return_net_of_cost"]
                    for trades in self.sell_trades_metrics.values()
                    for trade in trades
                    if trade["return_net_of_cost"] > 0
                ]
            )
            / total_sell_trades
        )
        avg_return_all_sell_trades = np.mean(
            [
                trade["return"]
                for trades in self.sell_trades_metrics.values()
                for trade in trades
            ]
        )
        avg_return_after_cost_all_sell_trades = np.mean(
            [
                trade["return_net_of_cost"]
                for trades in self.sell_trades_metrics.values()
                for trade in trades
            ]
        )

        no_signal_days = self.no_signal_days

        # Create table data
        summary_data = [
            ["Trading Summary Metric", "Value"],
            ["Total Trading Days", f"{total_trading_days}"],
            ["Average Buy per Day", f"{avg_buy_trades_per_day:.2f}"],
            ["Average Sell per Day", f"{avg_sell_trades_per_day:.2f}"],
            ["Average Short Signal per Day", f"{avg_no_short_day:.2f}"],
            [
                "Average Insufficient Capital Trades per Day",
                f"{avg_insufficient_capital_per_day:.2f}",
            ],
            ["Average Stop Loss per Day", f"{avg_stop_loss_per_day:.2f}"],
            [
                "% of Sell Trades with Profit",
                f"{positive_return_sell_trades:.2%}",
            ],
            [
                "% of Sell Trades with Profit After Costs",
                f"{positive_return_after_cost_sell_trades:.2%}",
            ],
            [
                "Average Return per Sell Trade",
                f"{avg_return_all_sell_trades:.2%}",
            ],
            [
                "Average Return per Sell Trade After Costs",
                f"{avg_return_after_cost_all_sell_trades:.2%}",
            ],
            ["No Signal Days %", f"{no_signal_days}"],
        ]

        return self.styling.create_styled_table(
            data=summary_data,
            column_widths=[4.0 * inch, 2.5 * inch],
            header_color=Colors.SLATE_BLUE,
        )

    def add_page_header(self, story: list, section_name: str = None) -> None:
        """Add page header with section name"""
        if section_name:
            story.append(Paragraph(section_name, self.section_header_style))
            story.append(Spacer(1, 20))

    def create_trading_activity_chart(
        self, title: str = None, graph_type: str = "D"
    ) -> BytesIO:
        plt.style.use("default")
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(10, 7.5), gridspec_kw={"height_ratios": [2, 1]}, sharex=True
        )
        trades_ts = self.curves["trades_ts"]

        if trades_ts:
            if isinstance(trades_ts, dict):
                trades_df = pd.DataFrame(list(trades_ts.values()))
                trades_df.index = pd.to_datetime(list(trades_ts.keys()))
            else:
                trades_df = pd.DataFrame(trades_ts)
                holdings_dates = list(self.analytics.trading_dates)
                trades_df.index = pd.to_datetime(holdings_dates[: len(trades_df)])

            trades_df = trades_df.sort_index()

            trades_df["buy"] = pd.to_numeric(trades_df["buy"], errors="coerce").fillna(
                0
            )
            trades_df["sell"] = pd.to_numeric(
                trades_df["sell"], errors="coerce"
            ).fillna(0)
            trades_df["insufficient_capital"] = pd.to_numeric(
                trades_df["insufficient_capital"], errors="coerce"
            ).fillna(0)
            trades_df["stop_loss"] = pd.to_numeric(
                trades_df["stop_loss"], errors="coerce"
            ).fillna(0)
            trades_df["no_short"] = pd.to_numeric(
                trades_df["no_short"], errors="coerce"
            ).fillna(0)

            interval = (
                1
                if len(trades_df) // 365 <= 2
                else (
                    3 if len(trades_df) // 365 > 2 and len(trades_df) // 365 <= 5 else 4
                )
            )

            if graph_type == "M" and len(trades_df.resample("M").last()) <= 1:
                trades_df = trades_df.resample("D").last()
            elif graph_type == "Q" and len(trades_df.resample("Q").last()) <= 1:
                trades_df = trades_df.resample("M").last()
            elif graph_type == "Y" and len(trades_df.resample("Y").last()) <= 1:
                trades_df = trades_df.resample("Q").last()

            # Main chart - Buy/Sell bars only
            bar_width = 0.8
            ax1.bar(
                trades_df.index,
                trades_df["buy"],
                alpha=0.7,
                label="Buy Trades",
                color="green",
                width=bar_width,
            )
            ax1.bar(
                trades_df.index,
                -trades_df["sell"],
                alpha=0.7,
                label="Sell Trades",
                color="red",
                width=bar_width,
            )
            ax1.bar(
                trades_df.index,
                -trades_df["stop_loss"],
                alpha=0.7,
                label="Stop Loss Trades",
                color="blue",
                width=bar_width,
            )

            if title:
                ax1.set_title(title, fontsize=14, fontweight="bold")
            ax1.set_ylabel("Number of Trades")
            ax1.grid(True, alpha=0.3)
            ax1.axhline(y=0, color="black", linestyle="-", alpha=0.5)
            ax1.legend(
                loc="upper left",
                framealpha=0.8,  # Make legend background more transparent
                frameon=True,
                fancybox=True,
                shadow=False,
                facecolor="white",
                edgecolor="gray",
            )

            # Bottom chart - Total trades and net trades as lines
            ax2.plot(
                trades_df.index,
                trades_df["insufficient_capital"],
                color=Colors.CHART_NAVY,
                linewidth=1,
                label="Insufficient Capital Trigger",
                alpha=0.8,
            )
            ax2.plot(
                trades_df.index,
                trades_df["no_short"],
                color=Colors.CHART_GREEN,
                linewidth=1,
                label="No Short Trigger",
                alpha=0.8,
            )

            ax2.set_ylabel("Number of Cancelled Trades")
            if graph_type in ["D", "M"] and len(trades_df.resample("M").last()) <= 1:
                ax2.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
                ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            elif graph_type == "Q" and len(trades_df.resample("Q").last()) <= 1:
                ax2.xaxis.set_major_locator(mdates.QuarterLocator(interval=interval))
                ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
            elif graph_type == "Y" and len(trades_df.resample("Y").last()) <= 1:
                ax2.xaxis.set_major_locator(mdates.YearLocator(interval=interval))
                ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%q"))
            else:
                ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=interval))
                ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
            ax2.grid(True, alpha=0.3)
            ax2.axhline(y=0, color="black", linestyle="-", alpha=0.5)
            ax2.legend(
                loc="upper left",
                framealpha=0.8,  # Make legend background more transparent
                frameon=True,
                fancybox=True,
                shadow=False,
                facecolor="white",
                edgecolor="gray",
            )

            plt.xticks(rotation=45)
        else:
            # No trading data available
            ax1.text(
                0.5,
                0.5,
                "No trading data available",
                transform=ax1.transAxes,
                ha="center",
                va="center",
            )
            if title:
                ax1.set_title(title, fontsize=14, fontweight="bold")
            ax2.text(
                0.5,
                0.5,
                "No trading data available",
                transform=ax2.transAxes,
                ha="center",
                va="center",
            )
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=self.dpi, bbox_inches="tight")
        buf.seek(0)
        plt.close()

        return buf

    def create_cashflow_over_time_chart(
        self, title: str = None, graph_type: str = "D"
    ) -> BytesIO:
        plt.style.use("default")
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(10, 7.5), gridspec_kw={"height_ratios": [2, 1]}, sharex=True
        )
        buy_proceeds_history = self.curves["buy_proceeds_ts"]
        sell_proceeds_history = self.curves["sell_proceeds_ts"]
        transaction_cost_history = self.curves["transaction_costs_ts"]

        if buy_proceeds_history and sell_proceeds_history and transaction_cost_history:
            buy_proceeds_df = pd.Series(buy_proceeds_history)
            sell_proceeds_df = pd.Series(sell_proceeds_history)
            transaction_cost_df = pd.Series(transaction_cost_history)
            buy_proceeds_df.index = pd.to_datetime(buy_proceeds_df.index)
            sell_proceeds_df.index = pd.to_datetime(sell_proceeds_df.index)
            transaction_cost_df.index = pd.to_datetime(transaction_cost_df.index)

            buy_proceeds_df = buy_proceeds_df.sort_index()
            sell_proceeds_df = sell_proceeds_df.sort_index()
            transaction_cost_df = transaction_cost_df.sort_index()

            net_cashflow = sell_proceeds_df - buy_proceeds_df - transaction_cost_df

            interval = (
                1
                if len(buy_proceeds_df) // 365 <= 2
                else (
                    3
                    if len(buy_proceeds_df) // 365 > 2
                    and len(buy_proceeds_df) // 365 <= 5
                    else 4
                )
            )

            if graph_type == "M" and len(buy_proceeds_df.resample("M").last()) <= 1:
                buy_proceeds_df = buy_proceeds_df.resample("D").last()
                sell_proceeds_df = sell_proceeds_df.resample("D").last()
                transaction_cost_df = transaction_cost_df.resample("D").last()
                net_cashflow = net_cashflow.resample("D").last()
            elif graph_type == "Q" and len(buy_proceeds_df.resample("Q").last()) <= 1:
                buy_proceeds_df = buy_proceeds_df.resample("M").last()
                sell_proceeds_df = sell_proceeds_df.resample("M").last()
                transaction_cost_df = transaction_cost_df.resample("M").last()
                net_cashflow = net_cashflow.resample("M").last()
            elif graph_type == "Y" and len(buy_proceeds_df.resample("Y").last()) <= 1:
                buy_proceeds_df = buy_proceeds_df.resample("Q").last()
                sell_proceeds_df = sell_proceeds_df.resample("Q").last()
                transaction_cost_df = transaction_cost_df.resample("Q").last()
                net_cashflow = net_cashflow.resample("Q").last()

            ax1.plot(
                buy_proceeds_df.index,
                buy_proceeds_df.values * -1,
                color=Colors.CHART_NAVY,
                linewidth=1,
                label="Buy Proceeds",
                alpha=0.8,
            )
            ax1.plot(
                sell_proceeds_df.index,
                sell_proceeds_df.values,
                color=Colors.CHART_RED,
                linewidth=1,
                label="Sell Proceeds",
                alpha=0.8,
            )

            if title:
                ax1.set_title(title, fontsize=14, fontweight="bold")
            ax1.set_ylabel("Amount ($)")
            ax1.grid(True, alpha=0.3)
            ax1.axhline(y=0, color="black", linestyle="-", alpha=0.5)
            ax1.legend(
                loc="upper left",
                framealpha=0.8,  # Make legend background more transparent
                frameon=True,
                fancybox=True,
                shadow=False,
                facecolor="white",
                edgecolor="gray",
            )

            # Bottom chart - Net Cashflow
            ax2.plot(
                transaction_cost_df.index,
                transaction_cost_df.values * -1,
                color=Colors.CHART_RED,
                linewidth=1,
                label="Transaction Costs",
                alpha=0.8,
            )
            ax2.plot(
                net_cashflow.index,
                net_cashflow.values,
                color=Colors.CHART_GREEN,
                linewidth=1,
                label="Net Cashflow (Net proceeds - Transaction Costs)",
                alpha=0.8,
            )

            ax2.set_ylabel("Net Cashflow ($)")
            if graph_type in ["D", "M"] and len(net_cashflow.resample("M").last()) <= 1:
                ax2.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
                ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            elif graph_type == "Q" and len(net_cashflow.resample("Q").last()) <= 1:
                ax2.xaxis.set_major_locator(mdates.QuarterLocator(interval=interval))
                ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
            elif graph_type == "Y" and len(net_cashflow.resample("Y").last()) <= 1:
                ax2.xaxis.set_major_locator(mdates.YearLocator(interval=interval))
                ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%q"))
            else:
                ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=interval))
                ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
            ax2.grid(True, alpha=0.3)
            ax2.axhline(y=0, color="black", linestyle="-", alpha=0.5)
            ax2.legend(
                loc="upper left",
                framealpha=0.8,  # Make legend background more transparent
                frameon=True,
                fancybox=True,
                shadow=False,
                facecolor="white",
                edgecolor="gray",
            )

            plt.xticks(rotation=45)
        else:
            ax1.text(
                0.5,
                0.5,
                "No cashflow data available",
                transform=ax1.transAxes,
                ha="center",
                va="center",
            )
            if title:
                ax1.set_title(title, fontsize=14, fontweight="bold")
            ax2.text(
                0.5,
                0.5,
                "No cashflow data available",
                transform=ax2.transAxes,
                ha="center",
                va="center",
            )

        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=self.dpi, bbox_inches="tight")
        buf.seek(0)
        plt.close()

        return buf

    def create_pnl_over_time_chart(
        self, title: str = None, graph_type: str = "D"
    ) -> BytesIO:
        plt.style.use("default")
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(10, 7.5), gridspec_kw={"height_ratios": [2, 1]}, sharex=True
        )

        # Get PnL data from curves
        realized_gain_sell = pd.Series(self.curves["realized_gain_sell_ts"])
        realized_loss_sell = pd.Series(self.curves["realized_loss_sell_ts"])
        realized_gain_stop_loss = pd.Series(self.curves["realized_gain_stop_loss_ts"])
        realized_loss_stop_loss = pd.Series(self.curves["realized_loss_stop_loss_ts"])
        realized_return = pd.Series(self.curves["realized_return_ts"])
        realized_return_pct = pd.Series(self.curves["realized_return_pct_ts"])
        realized_return_net_of_cost = pd.Series(
            self.curves["realized_return_net_of_cost_ts"]
        )
        realized_return_net_of_cost_pct = pd.Series(
            self.curves["realized_return_net_of_cost_pct_ts"]
        )

        if not realized_gain_sell.empty:
            # Convert indices to datetime
            realized_gain_sell.index = pd.to_datetime(realized_gain_sell.index)
            realized_loss_sell.index = pd.to_datetime(realized_loss_sell.index)
            realized_gain_stop_loss.index = pd.to_datetime(
                realized_gain_stop_loss.index
            )
            realized_loss_stop_loss.index = pd.to_datetime(
                realized_loss_stop_loss.index
            )
            realized_return.index = pd.to_datetime(realized_return.index)
            realized_return_pct.index = pd.to_datetime(realized_return_pct.index)
            realized_return_net_of_cost.index = pd.to_datetime(
                realized_return_net_of_cost.index
            )
            realized_return_net_of_cost_pct.index = pd.to_datetime(
                realized_return_net_of_cost_pct.index
            )

            # Sort all series by index
            realized_gain_sell = realized_gain_sell.sort_index()
            realized_loss_sell = realized_loss_sell.sort_index()
            realized_gain_stop_loss = realized_gain_stop_loss.sort_index()
            realized_loss_stop_loss = realized_loss_stop_loss.sort_index()
            realized_return = realized_return.sort_index()
            realized_return_pct = realized_return_pct.sort_index()
            realized_return_net_of_cost = realized_return_net_of_cost.sort_index()
            realized_return_net_of_cost_pct = (
                realized_return_net_of_cost_pct.sort_index()
            )

            interval = (
                1
                if len(realized_gain_sell) // 365 <= 2
                else (
                    3
                    if len(realized_gain_sell) // 365 > 2
                    and len(realized_gain_sell) // 365 <= 5
                    else 4
                )
            )

            # Resample data based on graph type
            if graph_type == "M" and len(realized_gain_sell.resample("M").last()) <= 1:
                realized_gain_sell = realized_gain_sell.resample("D").last()
                realized_loss_sell = realized_loss_sell.resample("D").last()
                realized_gain_stop_loss = realized_gain_stop_loss.resample("D").last()
                realized_loss_stop_loss = realized_loss_stop_loss.resample("D").last()
                realized_return = realized_return.resample("D").last()
                realized_return_pct = realized_return_pct.resample("D").last()
                realized_return_net_of_cost = realized_return_net_of_cost.resample(
                    "D"
                ).last()
                realized_return_net_of_cost_pct = (
                    realized_return_net_of_cost_pct.resample("D").last()
                )
            elif (
                graph_type == "Q" and len(realized_gain_sell.resample("Q").last()) <= 1
            ):
                realized_gain_sell = realized_gain_sell.resample("M").last()
                realized_loss_sell = realized_loss_sell.resample("M").last()
                realized_gain_stop_loss = realized_gain_stop_loss.resample("M").last()
                realized_loss_stop_loss = realized_loss_stop_loss.resample("M").last()
                realized_return = realized_return.resample("M").last()
                realized_return_pct = realized_return_pct.resample("M").last()
                realized_return_net_of_cost = realized_return_net_of_cost.resample(
                    "M"
                ).last()
                realized_return_net_of_cost_pct = (
                    realized_return_net_of_cost_pct.resample("M").last()
                )
            elif (
                graph_type == "Y" and len(realized_gain_sell.resample("Y").last()) <= 1
            ):
                realized_gain_sell = realized_gain_sell.resample("Q").last()
                realized_loss_sell = realized_loss_sell.resample("Q").last()
                realized_gain_stop_loss = realized_gain_stop_loss.resample("Q").last()
                realized_loss_stop_loss = realized_loss_stop_loss.resample("Q").last()
                realized_return = realized_return.resample("Q").last()
                realized_return_pct = realized_return_pct.resample("Q").last()
                realized_return_net_of_cost = realized_return_net_of_cost.resample(
                    "Q"
                ).last()
                realized_return_net_of_cost_pct = (
                    realized_return_net_of_cost_pct.resample("Q").last()
                )

            # Plot PnL components on top chart
            ax1.plot(
                realized_gain_sell.index,
                realized_gain_sell.values,
                color=Colors.CHART_GREEN,
                linewidth=1,
                label="Realized Gain (Sell)",
                alpha=0.8,
            )
            ax1.plot(
                realized_loss_sell.index,
                realized_loss_sell.values,
                color=Colors.CHART_RED,
                linewidth=1,
                label="Realized Loss (Sell)",
                alpha=0.8,
            )
            ax1.plot(
                realized_gain_stop_loss.index,
                realized_gain_stop_loss.values,
                color=Colors.CHART_NAVY,
                linewidth=1,
                label="Realized Gain (Stop Loss)",
                alpha=0.8,
            )
            ax1.plot(
                realized_loss_stop_loss.index,
                realized_loss_stop_loss.values,
                color=Colors.CHART_GOLD,
                linewidth=1,
                label="Realized Loss (Stop Loss)",
                alpha=0.8,
            )

            if title:
                ax1.set_title(title, fontsize=14, fontweight="bold")
            ax1.set_ylabel("PnL Components ($)")
            ax1.grid(True, alpha=0.3)
            ax1.axhline(y=0, color="black", linestyle="-", alpha=0.5)
            ax1.legend(
                loc="upper left",
                framealpha=0.8,
                frameon=True,
                fancybox=True,
                shadow=False,
                facecolor="white",
                edgecolor="gray",
            )

            # Plot returns on bottom chart
            ax2.plot(
                realized_return.index,
                realized_return.values,
                color=Colors.CHART_NAVY,
                linewidth=1,
                label="Realized Return",
                alpha=0.8,
            )
            ax2.plot(
                realized_return_net_of_cost.index,
                realized_return_net_of_cost.values,
                color=Colors.CHART_RED,
                linewidth=1,
                label="Realized Return (Net of Cost)",
                alpha=0.8,
            )
            ax2.plot(
                realized_return_pct.index,
                realized_return_pct.values * 100,  # Convert to percentage
                color=Colors.CHART_GREEN,
                linewidth=1,
                label="Realized Return %",
                alpha=0.8,
            )
            ax2.plot(
                realized_return_net_of_cost_pct.index,
                realized_return_net_of_cost_pct.values * 100,  # Convert to percentage
                color=Colors.CHART_GOLD,
                linewidth=1,
                label="Realized Return % (Net of Cost)",
                alpha=0.8,
            )

            ax2.set_ylabel("Returns")
            if (
                graph_type in ["D", "M"]
                and len(realized_return.resample("M").last()) <= 1
            ):
                ax2.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
                ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            elif graph_type == "Q" and len(realized_return.resample("Q").last()) <= 1:
                ax2.xaxis.set_major_locator(mdates.QuarterLocator(interval=interval))
                ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
            elif graph_type == "Y" and len(realized_return.resample("Y").last()) <= 1:
                ax2.xaxis.set_major_locator(mdates.YearLocator(interval=interval))
                ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%q"))
            else:
                ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=interval))
                ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
            ax2.grid(True, alpha=0.3)
            ax2.axhline(y=0, color="black", linestyle="-", alpha=0.5)
            ax2.legend(
                loc="upper left",
                framealpha=0.8,
                frameon=True,
                fancybox=True,
                shadow=False,
                facecolor="white",
                edgecolor="gray",
            )

            plt.xticks(rotation=45)
        else:
            ax1.text(
                0.5,
                0.5,
                "No PnL data available",
                transform=ax1.transAxes,
                ha="center",
                va="center",
            )
            if title:
                ax1.set_title(title, fontsize=14, fontweight="bold")
            ax2.text(
                0.5,
                0.5,
                "No PnL data available",
                transform=ax2.transAxes,
                ha="center",
                va="center",
            )

        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=self.dpi, bbox_inches="tight")
        buf.seek(0)
        plt.close()

        return buf

    def create_sector_exposure_chart(self, title: str = None) -> BytesIO:
        """Create multiline plot showing sector percentage over time with professional styling"""
        if self.sector_ts and self.curves["holdings_curve"]:
            # Create dataframe from sector time series
            holdings_dates = list(self.curves["holdings_curve"].keys())
            sector_df = pd.DataFrame(self.sector_ts)
            sector_df.index = pd.to_datetime(holdings_dates)
            sector_df = sector_df.sort_index()

            sector_pct_df = (
                sector_df.div(sector_df[sector_df.columns].sum(axis=1), axis=0) * 100
            )
            sector_pct_df = sector_pct_df.fillna(0)

            # Calculate appropriate interval
            chart_interval = max(1, len(sector_df) // 12)

            return self.styling.create_generic_multiline_chart(
                data_df=sector_pct_df,
                title=title,
                figsize=(10, 5),
                y_label="Percentage of Portfolio (%)",
                interval=chart_interval,
                date_format="%Y-%m",
                legend_position="top",
                legend_ncol=3,
                no_data_message="No sector data available",
                normal_style=self.normal_style,
            )
        else:
            return self.styling.create_generic_multiline_chart(
                data_df=None,
                title=title,
                figsize=(10, 5),
                y_label="Percentage of Portfolio (%)",
                interval=1,
                date_format="%Y-%m",
                legend_position="top",
                legend_ncol=3,
                no_data_message="No sector data available",
                normal_style=self.normal_style,
            )

    def create_sector_composition_pie(self, title: str = None) -> BytesIO:
        """Create pie chart of average sector composition with legend"""
        if self.sector_ts:
            # Calculate average sector composition
            sector_df = pd.DataFrame(self.sector_ts)
            avg_sector = sector_df.mean()
            avg_sector_dict = avg_sector.to_dict()

            return self.styling.create_generic_pie_chart(
                data_dict=avg_sector_dict,
                title=title,
                figsize=(10, 7),
                fontsize=11,
                no_data_message="No sector data available",
                normal_style=self.normal_style,
            )
        else:
            return self.styling.create_generic_pie_chart(
                data_dict={},
                title=title,
                figsize=(10, 7),
                fontsize=11,
                no_data_message="No sector data available",
                normal_style=self.normal_style,
            )

    def create_sector_duration_boxplot(self, title: str = None) -> BytesIO:
        """Create box plot showing duration distribution by sector"""
        try:
            # Use cached sector-trading data
            if (
                self.sector_trading_data is not None
                and len(self.sector_trading_data) > 0
            ):
                # Create data dictionary for generic boxplot
                sectors = self.sector_trading_data["sector"].dropna().unique()
                sector_data_dict = {
                    sector: self.sector_trading_data[
                        self.sector_trading_data["sector"] == sector
                    ]["duration"].tolist()
                    for sector in sectors
                }

                return self.styling.create_generic_boxplot(
                    data_dict=sector_data_dict,
                    title=title,
                    figsize=(10, 6),
                    y_label="Duration (Days)",
                    no_data_message="No sector-duration mapping available",
                    normal_style=self.normal_style,
                )
            else:
                return self.styling.create_generic_boxplot(
                    data_dict={},
                    title=title,
                    figsize=(10, 6),
                    y_label="Duration (Days)",
                    no_data_message="No duration or sector data available",
                    normal_style=self.normal_style,
                )
        except Exception as e:
            # Return empty boxplot on error
            return self.styling.create_generic_boxplot(
                data_dict={},
                title=title,
                figsize=(10, 6),
                y_label="Duration (Days)",
                no_data_message=f"Error generating sector duration chart: {str(e)}",
                normal_style=self.normal_style,
            )

    def create_sector_return_boxplot(self, title: str = None) -> BytesIO:
        """Create box plot showing return distribution by sector"""
        try:
            # Use cached sector-trading data
            if (
                self.sector_trading_data is not None
                and len(self.sector_trading_data) > 0
            ):
                # Create data dictionary for generic boxplot
                sectors = self.sector_trading_data["sector"].dropna().unique()
                sector_data_dict = {
                    sector: (
                        self.sector_trading_data[
                            self.sector_trading_data["sector"] == sector
                        ]["return"]
                        * 100
                    ).tolist()  # Convert to percentage
                    for sector in sectors
                }

                return self.styling.create_generic_boxplot(
                    data_dict=sector_data_dict,
                    title=title,
                    figsize=(10, 6),
                    y_label="Return (%)",
                    no_data_message="No sector-return mapping available",
                    normal_style=self.normal_style,
                )
            else:
                return self.styling.create_generic_boxplot(
                    data_dict={},
                    title=title,
                    figsize=(10, 6),
                    y_label="Return (%)",
                    no_data_message="No return or sector data available",
                    normal_style=self.normal_style,
                )
        except Exception as e:
            # Return empty boxplot on error
            return self.styling.create_generic_boxplot(
                data_dict={},
                title=title,
                figsize=(10, 6),
                y_label="Return (%)",
                no_data_message=f"Error generating sector return chart: {str(e)}",
                normal_style=self.normal_style,
            )

    def create_return_duration_scatter(self, title: str = None) -> BytesIO:
        """Create scatter plot with return vs duration, colored by sector"""
        try:
            if (
                self.sector_trading_data is not None
                and len(self.sector_trading_data) > 0
            ):
                return self.styling.create_generic_scatter_plot(
                    data_df=self.sector_trading_data,
                    x_column="return",
                    y_column="duration",
                    color_column="sector",
                    title=title,
                    x_label="Return (%)",
                    y_label="Duration (Days)",
                    figsize=(10, 6),
                    no_data_message="No return-duration-sector data available",
                    normal_style=self.normal_style,
                )
            else:
                return self.styling.create_generic_scatter_plot(
                    data_df=None,
                    x_column="return",
                    y_column="duration",
                    color_column="sector",
                    title=title,
                    x_label="Return (%)",
                    y_label="Duration (Days)",
                    figsize=(10, 6),
                    no_data_message="No return-duration-sector data available",
                    normal_style=self.normal_style,
                )
        except Exception as e:
            # Return empty scatter plot on error
            return self.styling.create_generic_scatter_plot(
                data_df=None,
                x_column="return",
                y_column="duration",
                color_column="sector",
                title=title,
                x_label="Return (%)",
                y_label="Duration (Days)",
                figsize=(10, 6),
                no_data_message=f"Error generating return-duration scatter plot: {str(e)}",
                normal_style=self.normal_style,
            )

    def create_top_traded_tables(self) -> tuple[Table, Table, Table]:
        # Top 10 Most Bought (by total_long_trades)
        most_bought = self.trades_by_ticker.nlargest(10, "buy")
        most_bought_data = [["Ticker", "Buy", "Avg\nReturn", "Avg Return\nafter cost"]]
        for _, row in most_bought.iterrows():
            most_bought_data.append(
                [
                    row["ticker"],
                    f"{int(row['buy'])}",
                    f"{row['return']:.2%}",
                    f"{row['return_net_of_cost']:.2%}",
                ]
            )

        # Top 10 Most Sold (by total_short_trades)
        most_sold = self.trades_by_ticker.nlargest(10, "sell")
        most_sold_data = [["Ticker", "Sell", "Avg\nReturn", "Avg Return\nafter cost"]]
        for _, row in most_sold.iterrows():
            most_sold_data.append(
                [
                    row["ticker"],
                    f"{int(row['sell'])}",
                    f"{row['return']:.2%}",
                    f"{row['return_net_of_cost']:.2%}",
                ]
            )

        # Top 10 Most Traded (by total_trades)
        most_traded = self.trades_by_ticker.nlargest(10, "total_trades")
        most_traded_data = [
            ["Ticker", "Total", "Avg\nReturn", "Avg Return\nafter cost"]
        ]
        for _, row in most_traded.iterrows():
            most_traded_data.append(
                [
                    row["ticker"],
                    f"{int(row['total_trades'])}",
                    f"{row['return']:.2%}",
                    f"{row['return_net_of_cost']:.2%}",
                ]
            )

        # Create the three tables with wider column widths and adjusted styling
        most_bought_table = self.styling.create_styled_table(
            data=most_bought_data,
            column_widths=[0.8 * inch, 0.5 * inch, 1.1 * inch, 1.4 * inch],
            header_color=Colors.SLATE_BLUE,
            custom_styles=[
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ],
        )

        most_sold_table = self.styling.create_styled_table(
            data=most_sold_data,
            column_widths=[0.8 * inch, 0.5 * inch, 1.1 * inch, 1.4 * inch],
            header_color=Colors.EMERALD,
            custom_styles=[
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ],
        )

        most_traded_table = self.styling.create_styled_table(
            data=most_traded_data,
            column_widths=[0.8 * inch, 0.5 * inch, 1.1 * inch, 1.4 * inch],
            header_color=Colors.CHART_RED,
            custom_styles=[
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ],
        )

        return most_bought_table, most_sold_table, most_traded_table

    def create_capital_contribution_table(self) -> Table:
        """Create capital contribution table with metrics and values"""
        capital_data = self.contribution_metrics["capital_contribution"]

        # Calculate net profit % on total capital invested
        net_profit_pct = (
            (
                capital_data["final_portfolio_value"]
                - capital_data["total_capital_injected"]
            )
            / capital_data["total_capital_injected"]
            * 100
        )

        capital_rows = [
            ["Metric", "Value"],  # Header row
            ["Initial Capital", f"${capital_data['initial_capital']:,.2f}"],
            [
                "Total Capital Injected",
                f"${capital_data['total_capital_injected']:,.2f}",
            ],
            ["Final Portfolio Value", f"${capital_data['final_portfolio_value']:,.2f}"],
            ["Total Return", f"${capital_data['total_return']:,.2f}"],
            [
                "Net Profit % on Total Capital",
                f"{net_profit_pct:.2f}%",
            ],
            [
                "Capital Contribution to Return",
                f"{capital_data['capital_contribution_pct']*100:.2f}%",
            ],
            [
                "Trading Contribution to Return",
                f"{capital_data['trading_contribution_pct']*100:.2f}%",
            ],
            [
                "Total Return %",
                f"{(capital_data['total_return']/capital_data['initial_capital'])*100:.2f}%",
            ],
        ]
        capital_table = Table(capital_rows, colWidths=[300, 200])
        capital_table.setStyle(
            TableStyle(
                [
                    # Header row styling
                    ("BACKGROUND", (0, 0), (-1, 0), Colors.SLATE_BLUE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), Colors.WHITE),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("TOPPADDING", (0, 0), (-1, 0), 12),
                    # Data rows styling
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
                    ("TOPPADDING", (0, 1), (-1, -1), 8),
                    # Grid styling
                    ("GRID", (0, 0), (-1, -1), 1, Colors.MEDIUM_GRAY),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    # Alternating row colors
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [Colors.WHITE, Colors.LIGHT_GRAY],
                    ),
                ]
            )
        )

        # Add title above the table
        capital_title = self.styling.create_table_title(
            "Capital Contribution", Colors.SLATE_BLUE
        )
        capital_container = Table(
            [[capital_title], [Spacer(1, 5)], [capital_table]], colWidths=[500]
        )
        capital_container.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )

        return capital_container

    def create_trading_contribution_table(self) -> Table:
        """Create trading contribution table comparing stop loss vs regular sell trades"""
        trading_data = self.contribution_metrics["trading_activity"]
        trading_rows = [
            ["Metric", "Stop Loss Trades", "Regular Sell Trades"],
            [
                "Number of Trades",
                f"{trading_data['stop_loss']['count']:,}",
                f"{trading_data['regular_sell']['count']:,}",
            ],
            [
                "Average Proceeds per Trade",
                f"${trading_data['stop_loss']['avg_proceeds']:,.2f}",
                f"${trading_data['regular_sell']['avg_proceeds']:,.2f}",
            ],
            [
                "Total Proceeds",
                f"${trading_data['stop_loss']['total_proceeds']:,.2f}",
                f"${trading_data['regular_sell']['total_proceeds']:,.2f}",
            ],
            [
                "% of Total Exits",
                f"{trading_data['stop_loss']['pct_of_exits']*100:.1f}%",
                f"{trading_data['regular_sell']['pct_of_exits']*100:.1f}%",
            ],
            [
                "Contribution to Return",
                f"{trading_data['stop_loss']['contribution_to_return']*100:.2f}%",
                f"{trading_data['regular_sell']['contribution_to_return']*100:.2f}%",
            ],
        ]
        trading_table = Table(trading_rows, colWidths=[200, 150, 150])
        trading_table.setStyle(
            TableStyle(
                [
                    # Header row styling
                    ("BACKGROUND", (0, 0), (-1, 0), Colors.SLATE_BLUE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), Colors.WHITE),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("TOPPADDING", (0, 0), (-1, 0), 12),
                    # Data rows styling
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
                    ("TOPPADDING", (0, 1), (-1, -1), 8),
                    # Grid styling
                    ("GRID", (0, 0), (-1, -1), 1, Colors.MEDIUM_GRAY),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    # Alternating row colors
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [Colors.WHITE, Colors.LIGHT_GRAY],
                    ),
                ]
            )
        )

        # Add title above the table
        trading_title = self.styling.create_table_title(
            "Trading Contribution", Colors.SLATE_BLUE
        )
        trading_container = Table(
            [[trading_title], [Spacer(1, 5)], [trading_table]], colWidths=[500]
        )
        trading_container.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )

        return trading_container

    def generate_report(self, filename: str = None, story: list = None) -> str:
        """Generate the complete 5-page report"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"outputs/backtest/portfolio_report_{timestamp}.pdf"
        elif not filename.endswith(".pdf"):
            filename = f"outputs/backtest/{filename}.pdf"
        else:
            filename = f"outputs/backtest/{filename}"

        os.makedirs("outputs/backtest", exist_ok=True)

        # Add page number function (define before using it)
        def add_page_number(canvas, doc):
            """Add page number and footer with portfolio info to each page"""
            # Skip footer and page number on first page (title page)
            if doc.page == 1:
                return

            canvas.saveState()

            # Draw footer divider line
            from reporting.report_styling import Colors

            canvas.setStrokeColor(Colors.MEDIUM_GRAY)
            canvas.setLineWidth(0.5)
            canvas.line(
                0.75 * inch, 0.7 * inch, landscape(A4)[0] - 0.75 * inch, 0.7 * inch
            )

            # Add portfolio info in footer
            period = f"{self.start_date_str} to {self.end_date_str}"
            footer_text = f"{self.portfolio_name} | Benchmark: {self.benchmark_text} | Period: {period} | Report Runtime: {self.run_date} "

            canvas.setFont("Helvetica", 9)
            canvas.setFillColor(Colors.CHARCOAL)
            canvas.drawString(0.75 * inch, 0.5 * inch, footer_text)

            # Add page number (just the number)
            canvas.drawRightString(
                landscape(A4)[0] - 0.75 * inch, 0.5 * inch, f"{doc.page}"
            )
            canvas.restoreState()

        # Create document with same setup as old report
        from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate

        doc = BaseDocTemplate(
            filename,
            pagesize=landscape(A4),
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.4 * inch,
            bottomMargin=0.75 * inch,
        )

        frame = Frame(
            0.75 * inch,
            0.75 * inch,
            landscape(A4)[0] - 1.5 * inch,
            landscape(A4)[1] - 1.15 * inch,
            id="normal",
        )

        template = PageTemplate(id="normal", frames=frame, onPage=add_page_number)
        doc.addPageTemplates([template])

        # Build PDF with page numbers
        doc.build(story)
        print(f"Report saved to: {filename}")
        return filename


def generate_simple_report(
    analytics,
    filename=None,
    dpi=300,
) -> str:
    # Create report generator and generate report
    generator = SimpleReportGenerator(analytics, dpi=dpi)
    return generator.generate_report(filename=filename)
