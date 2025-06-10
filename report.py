import io
import os
from datetime import datetime
from io import BytesIO

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from reporting.portfolio_analytics import PortfolioAnalytics
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

        # Extract data from analytics
        self.extract_portfolio_data()
        self.calculate_metrics()

        # Initialize styles
        self.title_page_title_style = self.style_utility.create_title_page_title_style()
        self.section_title_style = self.style_utility.create_section_title_style()
        self.normal_style = self.style_utility.create_normal_style()
        self.footer_info_style = self.style_utility.create_footer_info_style()
        self.section_header_style = self.style_utility.create_section_header_style()
        self.base_table_title_style = self.style_utility.create_base_table_title_style()

    def extract_portfolio_data(self):
        """Extract key data from portfolio analytics"""
        self.portfolio_value_history = self.analytics.portfolio_value_history
        self.dates = list(self.portfolio_value_history.keys())

        if self.dates:
            self.start_date = min(self.dates)
            self.end_date = max(self.dates)
            self.start_date_str = pd.to_datetime(self.start_date).strftime("%Y-%m-%d")
            self.end_date_str = pd.to_datetime(self.end_date).strftime("%Y-%m-%d")
        else:
            self.start_date = "N/A"
            self.end_date = "N/A"
            self.start_date_str = "N/A"
            self.end_date_str = "N/A"

        # Get benchmark info
        benchmark_text = (
            self.portfolio.benchmark.value
            if hasattr(self.portfolio.benchmark, "value")
            else str(self.portfolio.benchmark)
        )
        self.benchmark_text = benchmark_text

        # Get portfolio configuration
        config_data = {}
        for k, v in self.portfolio.setup.items():
            # Handle empty initial holdings
            if k == "initial_holdings" and (v == {} or not v):
                config_data[k] = "None"
            else:
                config_data[k] = v

        # Get constraints information
        if hasattr(self.portfolio, "constraints") and self.portfolio.constraints:
            constraints_list = self.portfolio.constraints.list_constraints()
            for constraint_key, constraint_value in constraints_list.items():
                config_data[constraint_key] = constraint_value
        self.portfolio_config = config_data

    def calculate_metrics(self):
        """Calculate key performance metrics"""
        self.metrics = self.analytics.performance_metrics(
            rf=self.analytics.rf, bmk_returns=self.analytics.bmk_returns
        )
        self.holdings_summary = self.analytics.holdings_metrics()
        self.sector_summary = self.analytics.sector_metrics()

    def create_key_performance_data(self) -> dict[str, float]:
        """Create performance metrics for display"""
        performance_data = {
            "Total Return": f"{self.metrics['total_return']:.2%}",
            "Annualized Return": f"{self.metrics['annualized_return']:.2%}",
            "Sharpe Ratio": f"{self.metrics['annualized_sharpe']:.2f}",
            "Information Ratio": f"{self.metrics['annualized_ir']:.2f}",
            "Win Rate": f"{self.metrics['win_rate']:.2%}",
            "Daily Avg Win": f"{self.metrics['avg_win']:.2%}",
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

    def create_portfolio_overview_page_performance(self) -> BytesIO:
        # Convert portfolio value history to pandas Series for left axis
        portfolio_value = pd.Series(self.portfolio_value_history)
        portfolio_value.index = pd.to_datetime(portfolio_value.index)
        portfolio_value = portfolio_value.sort_index()
        monthly_portfolio_value = portfolio_value.resample("ME").last()

        # Convert to dictionary format for generic function
        portfolio_value_dict = {
            date.strftime("%Y-%m-%d"): value
            for date, value in monthly_portfolio_value.items()
        }

        # Calculate monthly returns for right axis
        monthly_returns = monthly_portfolio_value.pct_change().dropna()
        monthly_returns_dict = {
            date.strftime("%Y-%m-%d"): value * 100  # Convert to percentage
            for date, value in monthly_returns.items()
        }

        # Get holdings count for bar chart
        holdings_series = pd.Series(self.holdings_summary)
        holdings_series.index = pd.to_datetime(holdings_series.index)
        holdings_series = holdings_series.sort_index()
        monthly_holdings = holdings_series.resample("ME").mean()
        holdings_dict = {
            date.strftime("%Y-%m-%d"): value for date, value in monthly_holdings.items()
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
            interval=max(1, len(monthly_portfolio_value) // 12),
            graph_type="M",
            # Bar chart parameters
            bar_data_dict=holdings_dict,
            bar_label="Holdings Count",
            bar_color="lightgray",
            right_axis_zero_line=True,  # Add zero line for returns
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

    def create_monthly_sharpe_ir_chart(self) -> BytesIO:
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
        )

    def create_top_return_tables(self) -> tuple[Table, Table]:
        """Create tables for top 10 highest and lowest average return tickers"""
        # Get trading metrics to access trades_by_ticker
        trading_metrics = self.analytics.trading_metrics()
        trades_by_ticker = trading_metrics["trades_by_ticker"]

        if trades_by_ticker.empty:
            return None, None

        # Common custom styles for smaller padding
        custom_padding_styles = [
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
        ]

        # Top 10 highest average returns
        top_returns = trades_by_ticker.nlargest(10, "return")[["ticker", "return"]]
        highest_data = [["Ticker", "Avg Return"]]
        for _, row in top_returns.iterrows():
            return_pct = f"{row['return']:.2%}" if pd.notna(row["return"]) else "N/A"
            highest_data.append([str(row["ticker"]), return_pct])

        highest_table = self.styling.create_styled_table(
            data=highest_data,
            column_widths=[1.8 * inch, 1.8 * inch],
            header_color=Colors.SLATE_BLUE,
            custom_styles=custom_padding_styles,
        )

        # Top 10 lowest average returns
        lowest_returns = trades_by_ticker.nsmallest(10, "return")[["ticker", "return"]]
        lowest_data = [["Ticker", "Avg Return"]]
        for _, row in lowest_returns.iterrows():
            return_pct = f"{row['return']:.2%}" if pd.notna(row["return"]) else "N/A"
            lowest_data.append([str(row["ticker"]), return_pct])

        lowest_table = self.styling.create_styled_table(
            data=lowest_data,
            column_widths=[1.8 * inch, 1.8 * inch],
            header_color=Colors.EMERALD,
            custom_styles=custom_padding_styles,
        )

        return highest_table, lowest_table

    def create_holdings_summary_table(self) -> Table:
        """Create holdings summary table with professional styling"""
        if not self.holdings_summary:
            return None

        holdings_dates = list(self.holdings_summary.keys())
        holdings_counts = list(self.holdings_summary.values())
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
        # Get duration data from trading metrics
        trading_metrics = self.analytics.trading_metrics()
        trades_by_ticker = trading_metrics["trades_by_ticker"]

        if trades_by_ticker.empty:
            return None

        durations = trades_by_ticker["duration"].dropna()

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
            if len(self.holdings_summary) // 365 <= 2
            else (
                3
                if len(self.holdings_summary) // 365 > 2
                and len(self.holdings_summary) // 365 <= 5
                else 4
            )
        )

        return self.styling.create_generic_dual_axis_chart(
            data_dict_left=self.holdings_summary,
            left_y_label="Number of Holdings",
            left_color=Colors.CHART_NAVY,
            left_linewidth=1,
            figsize=(10, 6),
            resample_freq=None,
            no_data_message="No holdings data available",
            normal_style=self.normal_style,
            show_crisis_periods=True,
            interval=interval,
            graph_type="D",
        )

    def create_top_duration_tables(self) -> tuple[Table, Table]:
        """Create tables for top 10 longest and shortest durations with professional styling"""
        if (
            not hasattr(self.analytics, "ticker_analysis")
            or not self.analytics.ticker_analysis
        ):
            return None, None

        duration_data = []
        for ticker, data in self.analytics.ticker_analysis.items():
            duration_data.append(
                {
                    "ticker": ticker,
                    "duration": data.get("average_holding_period", 0),
                    "return": data.get("average_return", 0),
                    "profit": data.get("average_profit", 0),
                }
            )

        if not duration_data:
            return None, None

        duration_df = pd.DataFrame(duration_data)

        # Top 10 longest durations
        longest_durations = duration_df.nlargest(10, "duration")[["ticker", "duration"]]
        longest_data = [["Ticker", "Duration (Days)"]]
        for _, row in longest_durations.iterrows():
            longest_data.append([str(row["ticker"]), f"{row['duration']:.1f}"])

        longest_table = self.styling.create_styled_table(
            data=longest_data,
            column_widths=[1.8 * inch, 1.8 * inch],
            header_color=Colors.SLATE_BLUE,
            custom_styles=[
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ],
        )

        # Top 10 shortest durations
        shortest_durations = duration_df.nsmallest(10, "duration")[
            ["ticker", "duration"]
        ]
        shortest_data = [["Ticker", "Duration (Days)"]]
        for _, row in shortest_durations.iterrows():
            shortest_data.append([str(row["ticker"]), f"{row['duration']:.1f}"])

        shortest_table = self.styling.create_styled_table(
            data=shortest_data,
            column_widths=[1.8 * inch, 1.8 * inch],
            header_color=Colors.EMERALD,
            custom_styles=[
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ],
        )

        return longest_table, shortest_table

    def create_trading_analysis_summary_table(self) -> Table:
        """Create Trading Analysis Summary table with key trading metrics"""
        try:
            # Get trading metrics from analytics
            trading_metrics = self.analytics.trading_metrics()
            trades_ts = trading_metrics["trades_ts"]
            trades_by_ticker = trading_metrics["trades_by_ticker"]

            # Convert trades_ts to DataFrame for analysis
            if isinstance(trades_ts, dict):
                trades_df = pd.DataFrame(list(trades_ts.values()))
            else:
                trades_df = pd.DataFrame(trades_ts) if trades_ts else pd.DataFrame()

            # Calculate basic metrics
            total_trading_days = len(trades_df) if not trades_df.empty else 0
            avg_buy_trades_per_day = (
                trades_df["buy"].mean()
                if not trades_df.empty and "buy" in trades_df.columns
                else 0
            )
            avg_sell_trades_per_day = (
                trades_df["sell"].mean()
                if not trades_df.empty and "sell" in trades_df.columns
                else 0
            )

            # Calculate sell trade returns
            pnl = np.array(
                [
                    list(trade.values())[0]["return"]
                    for daily_trades in self.analytics.pnl_details_history.values()
                    for trade in daily_trades
                ]
            )
            positive_return_sell_trades = len(pnl[pnl > 0]) / len(pnl)
            avg_return_all_sell_trades = pnl.mean()

            # Calculate trading status percentages
            cancelled_trades_count = trading_metrics.get("cancelled_trades_count", 0)
            no_trades_count = trading_metrics.get("no_trades_count", 0)
            successful_trades_count = trading_metrics.get("successful_trades_count", 0)
            total_trade_attempts = (
                cancelled_trades_count + no_trades_count + successful_trades_count
            )

            cancelled_trade_pct = (
                cancelled_trades_count / total_trade_attempts
                if total_trade_attempts > 0
                else 0
            )
            no_trade_pct = (
                no_trades_count / total_trade_attempts
                if total_trade_attempts > 0
                else 0
            )

            # Create table data
            summary_data = [
                ["Trading Summary Metric", "Value"],
                ["Total Trading Days", f"{total_trading_days}"],
                ["Average Buy Trades per Day", f"{avg_buy_trades_per_day:.2f}"],
                ["Average Sell Trades per Day", f"{avg_sell_trades_per_day:.2f}"],
                [
                    "Sell Trades with Positive Return",
                    f"{positive_return_sell_trades:.2%}",
                ],
                [
                    "Average Return of All Sell Trades",
                    f"{avg_return_all_sell_trades:.2%}",
                ],
                ["Cancelled Trade %", f"{cancelled_trade_pct:.2%}"],
                ["No Trade %", f"{no_trade_pct:.2%}"],
            ]

            return self.styling.create_styled_table(
                data=summary_data,
                column_widths=[4.0 * inch, 2.5 * inch],
                header_color=Colors.SLATE_BLUE,
            )
        except Exception as e:
            # If there's any error, create a simple error message table
            error_data = [
                ["Trading Summary Metric", "Value"],
                ["Error", f"Could not generate trading summary: {str(e)}"],
                ["Total Trading Days", "N/A"],
                ["Average Buy Trades per Day", "N/A"],
                ["Average Sell Trades per Day", "N/A"],
                ["Sell Trades with Positive Return", "N/A"],
                ["Average Return of All Sell Trades", "N/A"],
                ["Cancelled Trade %", "N/A"],
                ["No Trade %", "N/A"],
            ]
            return self.styling.create_styled_table(
                data=error_data,
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
        """Create trading activity bar chart with buy/sell bars and second chart with total/net trades lines"""
        plt.style.use("default")
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(10, 7.5), gridspec_kw={"height_ratios": [2, 1]}, sharex=True
        )

        try:
            # Get trading metrics from analytics
            trading_metrics = self.analytics.trading_metrics()
            trades_ts = trading_metrics["trades_ts"]

            if trades_ts:
                # Convert trades_ts to DataFrame for analysis
                if isinstance(trades_ts, dict):
                    trades_df = pd.DataFrame(list(trades_ts.values()))
                    trades_df.index = pd.to_datetime(list(trades_ts.keys()))
                else:
                    trades_df = pd.DataFrame(trades_ts)
                    # Use holdings history dates as index
                    holdings_dates = list(self.analytics.holdings_metrics().keys())
                    trades_df.index = pd.to_datetime(holdings_dates[: len(trades_df)])

                trades_df = trades_df.sort_index()

                trades_df["buy"] = pd.to_numeric(
                    trades_df["buy"], errors="coerce"
                ).fillna(0)
                trades_df["sell"] = pd.to_numeric(
                    trades_df["sell"], errors="coerce"
                ).fillna(0)
                trades_df["net_trades"] = trades_df["buy"] - trades_df["sell"]
                trades_df["total_trades"] = trades_df["buy"] + trades_df["sell"]

                # Calculate interval for chart formatting
                interval = (
                    1
                    if len(trades_df) // 365 <= 2
                    else (
                        3
                        if len(trades_df) // 365 > 2 and len(trades_df) // 365 <= 5
                        else 4
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

                if title:
                    ax1.set_title(title, fontsize=14, fontweight="bold")
                ax1.set_ylabel("Number of Trades (Buy +, Sell -)")
                ax1.grid(True, alpha=0.3)
                ax1.axhline(y=0, color="black", linestyle="-", alpha=0.5)
                ax1.legend(loc="upper left")

                # Bottom chart - Total trades and net trades as lines
                ax2.plot(
                    trades_df.index,
                    trades_df["total_trades"],
                    color=Colors.CHART_NAVY,
                    linewidth=1,
                    label="Total Trades",
                    alpha=0.8,
                )
                ax2.plot(
                    trades_df.index,
                    trades_df["net_trades"],
                    color=Colors.CHART_GREEN,
                    linewidth=1,
                    label="Net Trades (Buy - Sell)",
                    alpha=0.8,
                )

                ax2.set_ylabel("Number of Trades")
                if (
                    graph_type in ["D", "M"]
                    and len(trades_df.resample("M").last()) <= 1
                ):
                    ax2.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
                    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
                elif graph_type == "Q" and len(trades_df.resample("Q").last()) <= 1:
                    ax2.xaxis.set_major_locator(
                        mdates.QuarterLocator(interval=interval)
                    )
                    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
                elif graph_type == "Y" and len(trades_df.resample("Y").last()) <= 1:
                    ax2.xaxis.set_major_locator(mdates.YearLocator(interval=interval))
                    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%q"))
                else:
                    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=interval))
                    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
                ax2.grid(True, alpha=0.3)
                ax2.axhline(y=0, color="black", linestyle="-", alpha=0.5)
                ax2.legend(loc="upper left")

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
        except Exception as e:
            # Error handling - show error message on chart
            ax1.text(
                0.5,
                0.5,
                f"Error generating trading chart: {str(e)}",
                transform=ax1.transAxes,
                ha="center",
                va="center",
            )
            if title:
                ax1.set_title(title, fontsize=14, fontweight="bold")
            ax2.text(
                0.5,
                0.5,
                "Error generating trading data",
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
        """Create cashflow over time chart with cashflow/transaction costs in top panel and net cashflow in bottom panel"""
        plt.style.use("default")
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(10, 7.5), gridspec_kw={"height_ratios": [2, 1]}, sharex=True
        )

        try:
            # Get cashflow and transaction cost data from analytics
            cashflow_history = self.analytics.cashflow_history
            transaction_cost_history = self.analytics.transaction_cost_history

            if cashflow_history and transaction_cost_history:
                # Convert to DataFrame for analysis
                cashflow_df = pd.Series(cashflow_history)
                transaction_cost_df = pd.Series(transaction_cost_history)

                # Ensure both have the same index
                common_dates = cashflow_df.index.intersection(transaction_cost_df.index)
                cashflow_df = cashflow_df[common_dates]
                transaction_cost_df = transaction_cost_df[common_dates]

                # Convert index to datetime
                cashflow_df.index = pd.to_datetime(cashflow_df.index)
                transaction_cost_df.index = pd.to_datetime(transaction_cost_df.index)

                # Sort by date
                cashflow_df = cashflow_df.sort_index()
                transaction_cost_df = transaction_cost_df.sort_index()

                # Calculate net cashflow (cashflow - transaction costs, since costs are typically positive)
                net_cashflow = cashflow_df - transaction_cost_df

                # Calculate interval for chart formatting
                interval = (
                    1
                    if len(cashflow_df) // 365 <= 2
                    else (
                        3
                        if len(cashflow_df) // 365 > 2 and len(cashflow_df) // 365 <= 5
                        else 4
                    )
                )

                # Resample if needed based on graph_type
                if graph_type == "M" and len(cashflow_df.resample("M").last()) <= 1:
                    cashflow_df = cashflow_df.resample("D").last()
                    transaction_cost_df = transaction_cost_df.resample("D").last()
                    net_cashflow = net_cashflow.resample("D").last()
                elif graph_type == "Q" and len(cashflow_df.resample("Q").last()) <= 1:
                    cashflow_df = cashflow_df.resample("M").last()
                    transaction_cost_df = transaction_cost_df.resample("M").last()
                    net_cashflow = net_cashflow.resample("M").last()
                elif graph_type == "Y" and len(cashflow_df.resample("Y").last()) <= 1:
                    cashflow_df = cashflow_df.resample("Q").last()
                    transaction_cost_df = transaction_cost_df.resample("Q").last()
                    net_cashflow = net_cashflow.resample("Q").last()

                # Main chart - Cashflow and Transaction Cost lines
                ax1.plot(
                    cashflow_df.index,
                    cashflow_df.values,
                    color=Colors.CHART_NAVY,
                    linewidth=1,
                    label="Cashflow",
                    alpha=0.8,
                )
                ax1.plot(
                    transaction_cost_df.index,
                    transaction_cost_df.values,
                    color=Colors.CHART_RED,
                    linewidth=1,
                    label="Transaction Costs",
                    alpha=0.8,
                )

                if title:
                    ax1.set_title(title, fontsize=14, fontweight="bold")
                ax1.set_ylabel("Amount ($)")
                ax1.grid(True, alpha=0.3)
                ax1.axhline(y=0, color="black", linestyle="-", alpha=0.5)
                ax1.legend(loc="upper left")

                # Bottom chart - Net Cashflow
                ax2.plot(
                    net_cashflow.index,
                    net_cashflow.values,
                    color=Colors.CHART_GREEN,
                    linewidth=1,
                    label="Net Cashflow (Cashflow - Transaction Costs)",
                    alpha=0.8,
                )

                ax2.set_ylabel("Net Cashflow ($)")
                if (
                    graph_type in ["D", "M"]
                    and len(cashflow_df.resample("M").last()) <= 1
                ):
                    ax2.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
                    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
                elif graph_type == "Q" and len(cashflow_df.resample("Q").last()) <= 1:
                    ax2.xaxis.set_major_locator(
                        mdates.QuarterLocator(interval=interval)
                    )
                    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
                elif graph_type == "Y" and len(cashflow_df.resample("Y").last()) <= 1:
                    ax2.xaxis.set_major_locator(mdates.YearLocator(interval=interval))
                    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%q"))
                else:
                    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=interval))
                    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
                ax2.grid(True, alpha=0.3)
                ax2.axhline(y=0, color="black", linestyle="-", alpha=0.5)
                ax2.legend(loc="upper left")

                plt.xticks(rotation=45)
            else:
                # No cashflow data available
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
        except Exception as e:
            # Error handling - show error message on chart
            ax1.text(
                0.5,
                0.5,
                f"Error generating cashflow chart: {str(e)}",
                transform=ax1.transAxes,
                ha="center",
                va="center",
            )
            if title:
                ax1.set_title(title, fontsize=14, fontweight="bold")
            ax2.text(
                0.5,
                0.5,
                "Error generating cashflow data",
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
        if self.sector_summary["sector_ts"] and self.holdings_summary:
            # Create dataframe from sector time series
            holdings_dates = list(self.holdings_summary.keys())
            sector_df = pd.DataFrame(self.sector_summary["sector_ts"])
            sector_df.index = pd.to_datetime(holdings_dates)
            sector_df = sector_df.sort_index()

            # Handle case with only one data point - add more points for better visualization
            if len(sector_df) <= 2:
                if len(sector_df) == 1:
                    single_date = sector_df.index[0]
                    single_row = sector_df.iloc[0].copy()
                else:
                    # If we have 2 points, use the most recent one
                    single_date = sector_df.index[-1]
                    single_row = sector_df.iloc[-1].copy()

                # Create additional dates: create a wider range for better x-axis
                # Use 3 months before, original date, and 3 months after for better spacing
                earlier_date1 = single_date - pd.DateOffset(months=3)
                earlier_date2 = single_date - pd.DateOffset(months=1)
                later_date1 = single_date + pd.DateOffset(months=1)
                later_date2 = single_date + pd.DateOffset(months=3)

                # Create new dataframe with replicated data
                extended_data = []
                extended_dates = [
                    earlier_date1,
                    earlier_date2,
                    single_date,
                    later_date1,
                    later_date2,
                ]

                for _ in range(5):
                    extended_data.append(single_row.to_dict())

                sector_df = pd.DataFrame(extended_data, index=extended_dates)
                sector_df = sector_df.sort_index()

            sector_pct_df = (
                sector_df.div(sector_df[sector_df.columns].sum(axis=1), axis=0) * 100
            )
            sector_pct_df = sector_pct_df.fillna(0)

            # Calculate appropriate interval - for extended single-point data, use 1
            chart_interval = 1 if len(sector_df) <= 5 else max(1, len(sector_df) // 12)

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
        if self.sector_summary["sector_ts"]:
            # Calculate average sector composition
            sector_df = pd.DataFrame(self.sector_summary["sector_ts"])
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
            # Get duration data from trading metrics
            trading_metrics = self.analytics.trading_metrics()
            trades_by_ticker = trading_metrics["trades_by_ticker"]

            if not trades_by_ticker.empty and hasattr(self.portfolio, "product_data"):
                # Merge duration data with sector information
                duration_df = trades_by_ticker[["ticker", "duration"]].dropna()
                duration_df = duration_df.merge(
                    self.portfolio.product_data[["ticker", "sector"]],
                    on="ticker",
                    how="left",
                )

                if len(duration_df) > 0:
                    # Create data dictionary for generic boxplot
                    sectors = duration_df["sector"].dropna().unique()
                    sector_data_dict = {
                        sector: duration_df[duration_df["sector"] == sector][
                            "duration"
                        ].tolist()
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
            # Get return data from trading metrics
            trading_metrics = self.analytics.trading_metrics()
            trades_by_ticker = trading_metrics["trades_by_ticker"]

            if not trades_by_ticker.empty and hasattr(self.portfolio, "product_data"):
                # Merge return data with sector information
                return_df = trades_by_ticker[["ticker", "return"]].dropna()
                return_df = return_df.merge(
                    self.portfolio.product_data[["ticker", "sector"]],
                    on="ticker",
                    how="left",
                )

                if len(return_df) > 0:
                    # Create data dictionary for generic boxplot
                    sectors = return_df["sector"].dropna().unique()
                    sector_data_dict = {
                        sector: (
                            return_df[return_df["sector"] == sector]["return"] * 100
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
            # Get return and duration data from trading metrics
            trading_metrics = self.analytics.trading_metrics()
            trades_by_ticker = trading_metrics["trades_by_ticker"]

            if not trades_by_ticker.empty and hasattr(self.portfolio, "product_data"):
                # Merge trading data with sector information
                scatter_df = trades_by_ticker[["ticker", "return", "duration"]].dropna()
                scatter_df = scatter_df.merge(
                    self.portfolio.product_data[["ticker", "sector"]],
                    on="ticker",
                    how="left",
                )

                if len(scatter_df) > 0:
                    # Convert returns to percentage
                    scatter_df["return_pct"] = scatter_df["return"] * 100

                    return self.styling.create_generic_scatter_plot(
                        data_df=scatter_df,
                        x_column="return_pct",
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
                        x_column="return_pct",
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
                    x_column="return_pct",
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
                x_column="return_pct",
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
        """Create tables for top 10 most bought, most sold, and most traded tickers"""
        if (
            not hasattr(self.analytics, "ticker_analysis")
            or not self.analytics.ticker_analysis
        ):
            return None, None, None

        # Prepare data for analysis
        trading_data = []
        for ticker, data in self.analytics.ticker_analysis.items():
            total_long = data.get("total_long_trades", 0)
            total_short = data.get(
                "total_short_trade", 0
            )  # Note: it's 'total_short_trade' not 'total_short_trades'
            total_trades = total_long + total_short

            trading_data.append(
                {
                    "ticker": ticker,
                    "total_long_trades": total_long,
                    "total_short_trades": total_short,
                    "total_trades": total_trades,
                    "avg_return": data.get("average_return", 0),
                    "avg_profit": data.get("average_profit", 0),
                }
            )

        if not trading_data:
            return None, None, None

        trading_df = pd.DataFrame(trading_data)

        # Top 10 Most Bought (by total_long_trades)
        most_bought = trading_df.nlargest(10, "total_long_trades")
        most_bought_data = [["Ticker", "Buy", "Avg Return"]]
        for _, row in most_bought.iterrows():
            most_bought_data.append(
                [
                    row["ticker"],
                    f"{int(row['total_long_trades'])}",
                    f"{row['avg_return']:.2%}",
                ]
            )

        # Top 10 Most Sold (by total_short_trades)
        most_sold = trading_df.nlargest(10, "total_short_trades")
        most_sold_data = [["Ticker", "Sell", "Avg Return"]]
        for _, row in most_sold.iterrows():
            most_sold_data.append(
                [
                    row["ticker"],
                    f"{int(row['total_short_trades'])}",
                    f"{row['avg_return']:.2%}",
                ]
            )

        # Top 10 Most Traded (by total_trades)
        most_traded = trading_df.nlargest(10, "total_trades")
        most_traded_data = [["Ticker", "Total", "Avg Return"]]
        for _, row in most_traded.iterrows():
            most_traded_data.append(
                [
                    row["ticker"],
                    f"{int(row['total_trades'])}",
                    f"{row['avg_return']:.2%}",
                ]
            )

        # Create the three tables with wider column widths
        most_bought_table = self.styling.create_styled_table(
            data=most_bought_data,
            column_widths=[1.3 * inch, 0.8 * inch, 1.1 * inch],
            header_color=Colors.SLATE_BLUE,
        )

        most_sold_table = self.styling.create_styled_table(
            data=most_sold_data,
            column_widths=[1.3 * inch, 0.8 * inch, 1.1 * inch],
            header_color=Colors.EMERALD,
        )

        most_traded_table = self.styling.create_styled_table(
            data=most_traded_data,
            column_widths=[1.3 * inch, 0.8 * inch, 1.1 * inch],
            header_color=Colors.CHART_RED,
        )

        return most_bought_table, most_sold_table, most_traded_table

    def generate_report(self, filename: str = None) -> str:
        """Generate the complete 5-page report"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"reports/portfolio_report_{timestamp}.pdf"

            # Ensure reports directory exists
        os.makedirs("reports", exist_ok=True)

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

        story = []

        # Page 1: Title Page
        title_page = self.create_title_page()
        story.extend(title_page)
        story.append(PageBreak())

        # Page 2: Portfolio Config and Metrics
        self.add_page_header(
            story, section_name="Portfolio Overview - Config and Key Metrics"
        )
        overview_page = self.create_portfolio_overview_page_config_and_metrics()
        story.extend(overview_page)
        story.append(PageBreak())

        # Page 3: Portfolio Overview - Performance
        self.add_page_header(story, section_name="Portfolio Overview - Performance")
        chart = self.create_portfolio_overview_page_performance()
        story.append(Image(chart, width=10 * inch, height=6 * inch))
        story.append(PageBreak())

        # RETURN ANALYSIS SECTION TITLE PAGE
        return_analysis_title = self.create_section_title_page("Return Analysis")
        story.extend(return_analysis_title)
        story.append(PageBreak())

        # Page 4: Return Analysis - Monthly Return Distribution
        self.add_page_header(
            story, section_name="Return Analysis - Monthly Return Distribution"
        )
        distribution_chart = self.create_monthly_return_distribution_chart()
        story.append(Image(distribution_chart, width=10 * inch, height=6 * inch))
        story.append(PageBreak())

        # Page 5: Return Analysis - Monthly Sharpe and IR
        self.add_page_header(
            story,
            section_name="Return Analysis - Monthly Sharpe and Information Ratios",
        )
        sharpe_ir_chart = self.create_monthly_sharpe_ir_chart()
        story.append(Image(sharpe_ir_chart, width=10 * inch, height=5.0 * inch))
        story.append(PageBreak())

        # Page 6: Return Analysis - Top 10 Returns by Tickers
        self.add_page_header(
            story, section_name="Return Analysis - Top 10 Returns by Tickers"
        )
        highest_table, lowest_table = self.create_top_return_tables()

        if highest_table and lowest_table:
            # Create titles for the return tables
            highest_title = self.styling.create_table_title(
                "Top 10 Highest Average Returns", Colors.SLATE_BLUE
            )
            lowest_title = self.styling.create_table_title(
                "Top 10 Lowest Average Returns", Colors.EMERALD
            )

            # Create containers with titles and tables
            highest_container = Table(
                [[highest_title], [Spacer(1, 8)], [highest_table]],
                colWidths=[3.6 * inch],
            )
            highest_container.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ]
                )
            )

            lowest_container = Table(
                [[lowest_title], [Spacer(1, 8)], [lowest_table]], colWidths=[3.6 * inch]
            )
            lowest_container.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ]
                )
            )

            # Add spacer between the two tables
            spacer_cell = Table([[Spacer(1, 1)]], colWidths=[2.0 * inch])
            return_tables_data = [[highest_container, spacer_cell, lowest_container]]
            combined_return_table = Table(
                return_tables_data, colWidths=[3.6 * inch, 2.0 * inch, 3.6 * inch]
            )
            combined_return_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            story.append(combined_return_table)

        story.append(PageBreak())

        # HOLDINGS ANALYSIS SECTION TITLE PAGE
        holdings_analysis_title = self.create_section_title_page("Holdings Analysis")
        story.extend(holdings_analysis_title)
        story.append(PageBreak())

        # Page 7: Holdings Analysis - Holdings Summary
        self.add_page_header(story, section_name="Holdings Analysis - Holdings Summary")

        # Holdings summary table
        holdings_table = self.create_holdings_summary_table()
        if holdings_table:
            story.append(holdings_table)
            story.append(Spacer(1, 20))  # Add space between tables

        # Duration summary table
        duration_summary_table = self.create_holding_duration_summary_table()
        if duration_summary_table:
            story.append(duration_summary_table)

        story.append(PageBreak())

        # Page 8: Holdings Analysis - Holdings Over Time
        self.add_page_header(
            story, section_name="Holdings Analysis - Holdings Over Time"
        )
        holdings_chart = self.create_holdings_analysis_chart()
        story.append(Image(holdings_chart, width=10 * inch, height=6 * inch))
        story.append(PageBreak())

        # Page 9: Holdings Analysis - Top 10 Duration Tables
        self.add_page_header(
            story, section_name="Holdings Analysis - Top 10 Duration by Tickers"
        )

        # Create top duration tables
        longest_table, shortest_table = self.create_top_duration_tables()

        if longest_table and shortest_table:
            # Create titles for the duration tables
            longest_title = self.styling.create_table_title(
                "Top 10 Longest Hold", Colors.SLATE_BLUE
            )
            shortest_title = self.styling.create_table_title(
                "Top 10 Shortest Hold", Colors.EMERALD
            )

            # Create containers with titles and tables
            style = TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ]
            )

            longest_container = Table(
                [[longest_title], [Spacer(1, 8)], [longest_table]],
                colWidths=[3.6 * inch],
            )
            longest_container.setStyle(style)

            shortest_container = Table(
                [[shortest_title], [Spacer(1, 8)], [shortest_table]],
                colWidths=[3.6 * inch],
            )
            shortest_container.setStyle(style)

            # Add spacer between the two tables
            spacer_cell = Table([[Spacer(1, 1)]], colWidths=[2.0 * inch])
            duration_tables_data = [
                [longest_container, spacer_cell, shortest_container]
            ]
            combined_duration_table = Table(
                duration_tables_data, colWidths=[3.6 * inch, 2.0 * inch, 3.6 * inch]
            )
            combined_duration_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            story.append(combined_duration_table)

        story.append(PageBreak())

        # TRADING ANALYSIS SECTION TITLE PAGE
        trading_analysis_title = self.create_section_title_page("Trading Analysis")
        story.extend(trading_analysis_title)
        story.append(PageBreak())

        # Page 10: Trading Analysis - Summary
        self.add_page_header(story, section_name="Trading Analysis - Summary")
        trading_summary_table = self.create_trading_analysis_summary_table()
        story.append(trading_summary_table)

        story.append(PageBreak())

        # Page 11: Trading Analysis - Trading Over Time
        self.add_page_header(story, section_name="Trading Analysis - Trading Over Time")
        trading_activity_chart = self.create_trading_activity_chart(graph_type="D")
        story.append(Image(trading_activity_chart, width=10 * inch, height=6.4 * inch))

        story.append(PageBreak())

        # Page 12: Trading Analysis - Cashflow Over Time
        self.add_page_header(
            story, section_name="Trading Analysis - Cashflow Over Time"
        )
        cashflow_chart = self.create_cashflow_over_time_chart(graph_type="D")
        story.append(Image(cashflow_chart, width=10 * inch, height=6.4 * inch))

        # Page 13: Trading Analysis - Top 10 Most Traded
        self.add_page_header(
            story, section_name="Trading Analysis - Top 10 Most Traded"
        )
        most_bought_table, most_sold_table, most_traded_table = (
            self.create_top_traded_tables()
        )

        if most_bought_table and most_sold_table and most_traded_table:
            # Create titles for the top traded tables
            most_bought_title = self.styling.create_table_title(
                "Top 10 Most Bought Tickers", Colors.SLATE_BLUE
            )
            most_sold_title = self.styling.create_table_title(
                "Top 10 Most Sold Tickers", Colors.EMERALD
            )
            most_traded_title = self.styling.create_table_title(
                "Top 10 Most Traded Tickers", Colors.CHART_RED
            )

            # Create containers with titles and tables
            style = TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ]
            )

            most_bought_container = Table(
                [[most_bought_title], [Spacer(1, 8)], [most_bought_table]],
                colWidths=[3.6 * inch],
            )
            most_bought_container.setStyle(style)

            most_sold_container = Table(
                [[most_sold_title], [Spacer(1, 8)], [most_sold_table]],
                colWidths=[3.6 * inch],
            )
            most_sold_container.setStyle(style)

            most_traded_container = Table(
                [[most_traded_title], [Spacer(1, 8)], [most_traded_table]],
                colWidths=[3.6 * inch],
            )
            most_traded_container.setStyle(style)

            # Layout: All three tables horizontally
            spacer_cell = Table([[Spacer(1, 1)]], colWidths=[0.3 * inch])

            # Single row: All three tables side by side
            all_tables_data = [
                [
                    most_bought_container,
                    spacer_cell,
                    most_sold_container,
                    spacer_cell,
                    most_traded_container,
                ]
            ]
            all_tables_table = Table(
                all_tables_data,
                colWidths=[3.6 * inch, 0.3 * inch, 3.6 * inch, 0.3 * inch, 3.6 * inch],
            )
            all_tables_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            story.append(all_tables_table)

        story.append(PageBreak())

        # SECTOR ANALYSIS SECTION TITLE PAGE
        sector_analysis_title = self.create_section_title_page("Sector Analysis")
        story.extend(sector_analysis_title)
        story.append(PageBreak())

        # Page 14: Sector Analysis - Sector exposure over time
        self.add_page_header(
            story, section_name="Sector Analysis - Sector Exposure Over Time"
        )
        sector_exposure_chart = self.create_sector_exposure_chart()
        story.append(Image(sector_exposure_chart, width=10 * inch, height=6 * inch))
        story.append(PageBreak())

        # Page 15: Sector Analysis - Average composition
        self.add_page_header(
            story, section_name="Sector Analysis - Average Composition"
        )
        sector_composition_chart = self.create_sector_composition_pie()
        story.append(Image(sector_composition_chart, width=10 * inch, height=6 * inch))
        story.append(PageBreak())

        # Page 16: Sector Analysis - Exposure versus holding
        self.add_page_header(
            story, section_name="Sector Analysis - Exposure Versus Holding"
        )
        sector_duration_chart = self.create_sector_duration_boxplot()
        story.append(Image(sector_duration_chart, width=10 * inch, height=6 * inch))
        story.append(PageBreak())

        # Page 17: Sector Analysis - Sector vs Return
        self.add_page_header(story, section_name="Sector Analysis - Sector vs Return")
        sector_return_chart = self.create_sector_return_boxplot()
        story.append(Image(sector_return_chart, width=10 * inch, height=6 * inch))
        story.append(PageBreak())

        # Page 18: Sector Analysis - Return vs Duration Scatter
        self.add_page_header(story, section_name="Sector Analysis - Return vs Duration")
        return_duration_scatter = self.create_return_duration_scatter()
        story.append(Image(return_duration_scatter, width=10 * inch, height=6 * inch))
        story.append(PageBreak())

        # Build PDF with page numbers
        doc.build(story)
        print(f"Report saved to: {filename}")
        return filename


def generate_simple_report(
    analytics,
    start_date,
    end_date,
    rf=0.05,
    bmk_returns=0.1,
    filename=None,
    dpi=300,
) -> str:
    # Create report generator and generate report
    generator = SimpleReportGenerator(analytics, dpi=dpi)
    return generator.generate_report(filename=filename)
