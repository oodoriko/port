import io
import os
from collections import Counter
from datetime import datetime
from io import BytesIO

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .report_styling import Colors, ReportStyling, StyleUtility


class ReportGenerator:
    def __init__(
        self,
        portfolio,
        metrics,
        holdings_summary,
        dpi=1000,
        include_monthly=True,
        include_quarterly=True,
        include_annual=True,
    ):
        self.run_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.portfolio = portfolio
        self.portfolio_name = self.portfolio.name or "Unnamed Portfolio"
        self.dpi = dpi

        # Report generation options
        self.include_monthly = include_monthly
        self.include_quarterly = include_quarterly
        self.include_annual = include_annual

        self.metrics = metrics
        self.holdings_summary = holdings_summary
        self.styles = getSampleStyleSheet()
        self.styling = ReportStyling(dpi=self.dpi)
        self.style_utility = StyleUtility()
        self.extract_portfolio_data()

        # Initialize styles using utility
        self.title_page_title_style = self.style_utility.create_title_page_title_style()
        self.section_title_style = self.style_utility.create_section_title_style()
        self.normal_style = self.style_utility.create_normal_style()
        self.footer_info_style = self.style_utility.create_footer_info_style()
        self.section_header_style = self.style_utility.create_section_header_style()
        self.base_table_title_style = self.style_utility.create_base_table_title_style()
        self.divider_table_style = self.style_utility.create_divider_table_style()

        self.interval = (
            1
            if len(self.holdings_summary["holdings_count"]) // 365 <= 2
            else (
                3
                if len(self.holdings_summary["holdings_count"]) // 365 > 2
                and len(self.holdings_summary["holdings_count"]) // 365 <= 5
                else 4
            )
        )

    def extract_portfolio_data(self) -> None:
        self.dates = list(self.portfolio.portfolio_value_history.keys())
        if self.dates:
            self.start_date = min(self.dates)
            self.end_date = max(self.dates)
            # Format dates for display
            self.start_date_str = self.start_date.strftime("%Y-%m-%d")
            self.end_date_str = self.end_date.strftime("%Y-%m-%d")
        else:
            self.start_date = "N/A"
            self.end_date = "N/A"
            self.start_date_str = "N/A"
            self.end_date_str = "N/A"

        benchmark_text = (
            self.portfolio.benchmark.value
            if hasattr(self.portfolio.benchmark, "value")
            else str(self.portfolio.benchmark)
        )
        self.benchmark_text = benchmark_text
        config_data = {}

        for k, v in self.portfolio.setup.items():
            config_data[k] = v

        # Get constraints information
        if hasattr(self.portfolio, "constraints") and self.portfolio.constraints:
            constraints_list = self.portfolio.constraints.list_constraints()
            for constraint_key, constraint_value in constraints_list.items():
                config_data[constraint_key] = constraint_value
        self.portfolio_config = config_data

    def create_key_performance_data(self) -> dict[str, float]:
        performance_data = {
            "Total Return": self.metrics["total_return"],
            "Annualized Return": self.metrics["annualized_return"],
            "Overall Sharpe Ratio": self.metrics["overall_sharpe_ratio"],
            "Win Rate": self.metrics["win_rate"],
            "Daily Win Rate": self.metrics["avg_win"],
        }

        return performance_data

    def create_section_title_page(self, section_name: str) -> list[BaseDocTemplate]:
        story = []
        story.append(Spacer(1, 3 * inch))
        story.append(Paragraph(section_name, self.section_title_style))

        return story

    def create_table_title(self, title_text: str, color: str = None) -> Paragraph:
        """Create a table title paragraph with custom color"""
        return self.styling.create_table_title(
            title_text=title_text, color=color, base_title_style=self.base_table_title_style
        )

    def create_portfolio_info_footer(self) -> Paragraph:
        """Create portfolio info footer for each page"""
        period = f"{self.start_date_str} to {self.end_date_str}"
        info_text = f"{self.portfolio_name} | Benchmark: {self.benchmark_text} | Run Date: {self.run_date} | Period: {period}"
        return Paragraph(info_text, self.footer_info_style)

    def create_title_page(self, report_name: str = None) -> list[BaseDocTemplate]:
        story = []
        story.append(Spacer(1, 2.5 * inch))
        story.append(Paragraph(report_name or self.portfolio_name, self.title_page_title_style))

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
                f"<b>Analysis Period:</b> {self.start_date_str} to {self.end_date_str}", info_style
            )
        )
        story.append(Paragraph(f"<b>Report Runtime:</b> {self.run_date}", info_style))
        return story

    def create_portfolio_overview_page(self) -> list[BaseDocTemplate]:
        story = []

        config_data = self.portfolio_config
        performance_data = self.create_key_performance_data()

        config_elements = self.styling.create_formatted_list(config_data, "Portfolio Configuration")
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
            performance_item = performance_elements[i] if i < len(performance_elements) else ""
            combined_data.append([config_item, performance_item])

        combined_table = Table(combined_data, colWidths=[section_width, section_width])
        combined_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("LINEAFTER", (0, 0), (0, -1), 2, Colors.SLATE_BLUE),  # Vertical divider line
                    ("LEFTPADDING", (0, 0), (-1, -1), 20),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 20),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )

        story.append(Spacer(1, 0.5 * inch))  # Add top margin
        story.append(combined_table)

        return story

    def create_holdings_analysis_chart(self) -> BytesIO:
        return self.styling.create_generic_line_chart(
            data_dict=self.holdings_summary["holdings_count"],
            color=Colors.CHART_NAVY,
            resample_freq=None,
            date_format="%Y-%m",
            y_label="Number of Holdings",
            y_formatter=plt.FuncFormatter(lambda x, p: f"{x:,.0f}"),
            no_data_message="No holdings data available",
            interval=self.interval,
            normal_style=self.normal_style,
            graph_type="D",
        )

    def create_holdings_summary_table(self) -> Table:
        """Create holdings summary table with professional styling"""
        if not self.holdings_summary["holdings_count"]:
            return None

        holdings_dates = list(self.holdings_summary["holdings_count"].keys())
        holdings_counts = list(self.holdings_summary["holdings_count"].values())
        holdings_counts_arr = np.array(holdings_counts)
        non_zero_mask = holdings_counts_arr > 0

        if np.any(non_zero_mask):
            min_holdings_idx = np.argmin(np.where(non_zero_mask, holdings_counts_arr, np.inf))
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
            ["Maximum Holdings", f"{max_holdings}", str(max_date.date())],
            ["Minimum None-zero Holdings", f"{min_holdings}", str(min_date.date())],
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
        if not self.holdings_summary["duration_by_ticker"]:
            return None

        duration_df = pd.DataFrame(self.holdings_summary["duration_by_ticker"])
        durations = duration_df["duration"]

        max_duration = durations.max()
        min_duration = durations.min()
        avg_duration = durations.mean()

        duration_data = [
            ["Duration Metric", "Days"],
            ["Maximum Duration", f"{max_duration}"],
            ["Minimum Duration", f"{min_duration}"],
            ["Average Duration", f"{avg_duration:.1f}"],
        ]

        return self.styling.create_styled_table(
            data=duration_data,
            column_widths=[2.8 * inch, 2.2 * inch],
            header_color=Colors.NAVY_BLUE,
        )

    def create_top_duration_tables(self) -> tuple[Table, Table]:
        """Create tables for top longest and shortest hold tickers with professional styling"""
        if not self.holdings_summary["duration_by_ticker"]:
            return None, None

        duration_df = pd.DataFrame(self.holdings_summary["duration_by_ticker"])

        # Top 5 longest hold
        top_longest = duration_df.nlargest(5, "duration")[["ticker", "duration"]]
        longest_data = [["Ticker", "Duration (Days)"]]
        for _, row in top_longest.iterrows():
            longest_data.append([str(row["ticker"]), str(row["duration"])])

        longest_table = self.styling.create_styled_table(
            data=longest_data,
            column_widths=[1.7 * inch, 1.8 * inch],
            header_color=Colors.EMERALD,
            font_sizes={"header": 12, "body": 11},
            custom_styles=[
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ],
        )

        # Top 5 shortest hold
        top_shortest = duration_df.nsmallest(5, "duration")[["ticker", "duration"]]
        shortest_data = [["Ticker", "Duration (Days)"]]
        for _, row in top_shortest.iterrows():
            shortest_data.append([str(row["ticker"]), str(row["duration"])])

        shortest_table = self.styling.create_styled_table(
            data=shortest_data,
            column_widths=[1.7 * inch, 1.8 * inch],
            header_color=Colors.GOLD,
            font_sizes={"header": 12, "body": 11},
            custom_styles=[
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ],
        )

        return longest_table, shortest_table

    def create_daily_portfolio_value_chart(self) -> BytesIO:
        """Create daily portfolio value chart"""
        return self.styling.create_generic_line_chart(
            data_dict=self.portfolio.portfolio_value_history,
            color=Colors.CHART_NAVY,
            resample_freq=None,
            date_format="%Y-%m",
            y_label="Portfolio Value ($)",
            y_formatter=plt.FuncFormatter(lambda x, p: f"${x:,.0f}"),
            no_data_message="No portfolio value data available",
            interval=self.interval,
            normal_style=self.normal_style,
            graph_type="D",
        )

    def create_monthly_portfolio_value_chart(self) -> BytesIO:
        """Create monthly portfolio value chart"""
        return self.styling.create_generic_line_chart(
            data_dict=self.portfolio.portfolio_value_history,
            color=Colors.CHART_GREEN,
            resample_freq="M",
            date_format="%Y-%m",
            y_label="Portfolio Value ($)",
            y_formatter=plt.FuncFormatter(lambda x, p: f"${x:,.0f}"),
            no_data_message="No portfolio value data available",
            interval=self.interval,
            normal_style=self.normal_style,
            graph_type="M",
        )

    def create_annual_portfolio_value_chart(self) -> BytesIO:
        """Create annual portfolio value chart"""
        return self.styling.create_generic_line_chart(
            data_dict=self.portfolio.portfolio_value_history,
            color=Colors.CHART_GOLD,
            resample_freq="Y",
            date_format="%Y",
            y_label="Portfolio Value ($)",
            y_formatter=plt.FuncFormatter(lambda x, p: f"${x:,.0f}"),
            no_data_message="No portfolio value data available",
            interval=self.interval,
            normal_style=self.normal_style,
            graph_type="Y",
        )

    def create_daily_returns_chart(self) -> BytesIO:
        """Create daily returns chart"""
        return self.styling.create_generic_line_chart(
            metrics=self.metrics,
            data_key="daily_returns",
            color=Colors.CHART_NAVY,
            date_format="%Y-%m",
            y_label="Return (%)",
            add_zero_line=True,
            interval=self.interval,
            normal_style=self.normal_style,
            graph_type="D",
        )

    def create_monthly_returns_chart(self) -> BytesIO:
        """Create monthly returns chart"""
        return self.styling.create_generic_line_chart(
            metrics=self.metrics,
            data_key="monthly_returns",
            color=Colors.CHART_GREEN,
            date_format="%Y-%m",
            y_label="Return (%)",
            add_zero_line=True,
            interval=self.interval,
            normal_style=self.normal_style,
            graph_type="M",
        )

    def create_quarterly_returns_chart(self) -> BytesIO:
        """Create quarterly returns chart"""
        return self.styling.create_generic_line_chart(
            metrics=self.metrics,
            data_key="quarterly_returns",
            color=Colors.CHART_GOLD,
            date_format="%Y-%m",
            y_label="Return (%)",
            add_zero_line=True,
            interval=self.interval,
            normal_style=self.normal_style,
            graph_type="Q",
        )

    def create_annual_returns_chart(self) -> BytesIO:
        """Create annual returns chart"""
        return self.styling.create_generic_line_chart(
            metrics=self.metrics,
            data_key="annual_returns",
            color=Colors.CHART_RED,
            date_format="%Y",
            y_label="Return (%)",
            add_zero_line=True,
            interval=self.interval,
            normal_style=self.normal_style,
            graph_type="Y",
        )

    def create_daily_pnl_chart(self) -> BytesIO:
        """Create daily PnL chart showing both PnL and transaction costs"""
        if not self.portfolio.pnl_history:
            return self.styling.create_generic_line_chart(
                data_dict={},
                color=Colors.CHART_NAVY,
                resample_freq=None,
                date_format="%Y-%m",
                y_label="PnL ($)",
                y_formatter=plt.FuncFormatter(lambda x, p: f"${x:,.0f}"),
                no_data_message="No PnL data available",
                interval=self.interval,
                normal_style=self.normal_style,
                graph_type="D",
            )

        # Create DataFrame with both PnL and transaction costs
        dates = list(self.portfolio.pnl_history.keys())
        pnl_df = pd.DataFrame(
            {
                "Date": dates,
                "PnL": [self.portfolio.pnl_history.get(date, 0) for date in dates],
                "Transaction_Costs": [
                    -self.portfolio.transaction_cost_history.get(date, 0) for date in dates
                ],  # Negative to show as costs
                "Net_PnL": [
                    self.portfolio.pnl_history.get(date, 0)
                    - self.portfolio.transaction_cost_history.get(date, 0)
                    for date in dates
                ],
            }
        )
        pnl_df.set_index("Date", inplace=True)
        pnl_df.index = pd.to_datetime(pnl_df.index)
        pnl_df = pnl_df.sort_index()

        return self.styling.create_generic_multiline_chart(
            data_df=pnl_df,
            title="Daily PnL vs Transaction Costs",
            figsize=(10, 6),
            y_label="Amount ($)",
            interval=self.interval,
            date_format="%Y-%m",
            legend_position="upper right",
            legend_ncol=1,
            no_data_message="No PnL data available",
            normal_style=self.normal_style,
        )

    def create_monthly_pnl_chart(self) -> BytesIO:
        """Create monthly PnL chart showing both PnL and transaction costs"""
        if not self.portfolio.pnl_history:
            return self.styling.create_generic_line_chart(
                data_dict={},
                color=Colors.CHART_GREEN,
                resample_freq="M",
                date_format="%Y-%m",
                y_label="PnL ($)",
                y_formatter=plt.FuncFormatter(lambda x, p: f"${x:,.0f}"),
                no_data_message="No PnL data available",
                interval=self.interval,
                normal_style=self.normal_style,
                graph_type="M",
            )

        # Create DataFrame with both PnL and transaction costs
        dates = list(self.portfolio.pnl_history.keys())
        pnl_df = pd.DataFrame(
            {
                "Date": dates,
                "PnL": [self.portfolio.pnl_history.get(date, 0) for date in dates],
                "Transaction_Costs": [
                    -self.portfolio.transaction_cost_history.get(date, 0) for date in dates
                ],  # Negative to show as costs
                "Net_PnL": [
                    self.portfolio.pnl_history.get(date, 0)
                    - self.portfolio.transaction_cost_history.get(date, 0)
                    for date in dates
                ],
            }
        )
        pnl_df.set_index("Date", inplace=True)
        pnl_df.index = pd.to_datetime(pnl_df.index)
        pnl_df = pnl_df.sort_index()

        # Resample to monthly
        pnl_df_monthly = pnl_df.resample("ME").sum()

        return self.styling.create_generic_multiline_chart(
            data_df=pnl_df_monthly,
            title="Monthly PnL vs Transaction Costs",
            figsize=(10, 6),
            y_label="Amount ($)",
            interval=self.interval,
            date_format="%Y-%m",
            legend_position="upper right",
            legend_ncol=1,
            no_data_message="No PnL data available",
            normal_style=self.normal_style,
        )

    def create_annual_pnl_chart(self) -> BytesIO:
        """Create annual PnL chart showing both PnL and transaction costs"""
        if not self.portfolio.pnl_history:
            return self.styling.create_generic_line_chart(
                data_dict={},
                color=Colors.CHART_GOLD,
                resample_freq="Y",
                date_format="%Y",
                y_label="PnL ($)",
                y_formatter=plt.FuncFormatter(lambda x, p: f"${x:,.0f}"),
                no_data_message="No PnL data available",
                interval=self.interval,
                normal_style=self.normal_style,
                graph_type="Y",
            )

        # Create DataFrame with both PnL and transaction costs
        dates = list(self.portfolio.pnl_history.keys())
        pnl_df = pd.DataFrame(
            {
                "Date": dates,
                "PnL": [self.portfolio.pnl_history.get(date, 0) for date in dates],
                "Transaction_Costs": [
                    -self.portfolio.transaction_cost_history.get(date, 0) for date in dates
                ],  # Negative to show as costs
                "Net_PnL": [
                    self.portfolio.pnl_history.get(date, 0)
                    - self.portfolio.transaction_cost_history.get(date, 0)
                    for date in dates
                ],
            }
        )
        pnl_df.set_index("Date", inplace=True)
        pnl_df.index = pd.to_datetime(pnl_df.index)
        pnl_df = pnl_df.sort_index()

        # Resample to annual
        pnl_df_annual = pnl_df.resample("YE").sum()

        return self.styling.create_generic_multiline_chart(
            data_df=pnl_df_annual,
            title="Annual PnL vs Transaction Costs",
            figsize=(10, 6),
            y_label="Amount ($)",
            interval=self.interval,
            date_format="%Y",
            legend_position="upper right",
            legend_ncol=1,
            no_data_message="No PnL data available",
            normal_style=self.normal_style,
        )

    def create_daily_return_distribution_chart(self) -> BytesIO:
        """Create daily return distribution analysis with professional styling"""
        return self.styling.create_generic_distribution_chart(
            metrics=self.metrics,
            data_key="daily_returns",
            bins=50,
            color=Colors.CHART_NAVY,
            median_color=Colors.CHART_GOLD,
            normal_style=self.normal_style,
        )

    def create_monthly_return_distribution_chart(self) -> BytesIO:
        """Create monthly return distribution analysis with professional styling"""
        return self.styling.create_generic_distribution_chart(
            metrics=self.metrics,
            data_key="monthly_returns",
            bins=20,
            color=Colors.CHART_GOLD,
            median_color=Colors.CHART_DEEP_BLUE,
            normal_style=self.normal_style,
        )

    def create_sector_exposure_chart(self, title: str = None) -> BytesIO:
        """Create multiline plot showing sector percentage over time with professional styling"""
        if self.holdings_summary["sector_ts"] and self.holdings_summary["holdings_count"]:
            # Create dataframe from sector time series
            holdings_dates = list(self.holdings_summary["holdings_count"].keys())
            sector_df = pd.DataFrame(self.holdings_summary["sector_ts"])
            sector_df.index = pd.to_datetime(holdings_dates)
            sector_df = sector_df.sort_index()

            sector_pct_df = sector_df.div(sector_df[sector_df.columns].sum(axis=1), axis=0) * 100
            sector_pct_df = sector_pct_df.fillna(0)

            return self.styling.create_generic_multiline_chart(
                data_df=sector_pct_df,
                title=title,
                figsize=(10, 5),
                y_label="Percentage of Portfolio (%)",
                interval=self.interval,
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
                interval=self.interval,
                date_format="%Y-%m",
                legend_position="top",
                legend_ncol=3,
                no_data_message="No sector data available",
                normal_style=self.normal_style,
            )

    def create_sector_composition_pie(self, title: str = None) -> BytesIO:
        """Create pie chart of average sector composition with legend"""
        if self.holdings_summary["sector_ts"]:
            # Calculate average sector composition
            sector_df = pd.DataFrame(self.holdings_summary["sector_ts"])
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
        if self.holdings_summary["duration_by_ticker"] and self.holdings_summary["sector_ts"]:
            # Get duration data
            duration_df = pd.DataFrame(self.holdings_summary["duration_by_ticker"])
            duration_df = duration_df.merge(self.portfolio.product_data, on="ticker", how="left")

            if len(duration_df) > 0:
                # Create data dictionary for generic boxplot
                sectors = duration_df["sector"].unique()
                sector_data_dict = {
                    sector: duration_df[duration_df["sector"] == sector]["duration"].tolist()
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

    def create_trading_metrics_table(self) -> Table:
        trades_df = pd.DataFrame(self.holdings_summary["trades_ts"])
        trades_df["total"] = trades_df.sum(axis=1)
        trades_df[["buy_pct", "sell_pct"]] = trades_df[["buy", "sell"]].div(
            trades_df["total"], axis=0
        )
        trades_df.fillna(0, inplace=True)

        count = Counter(self.portfolio.trading_status.values())
        executed = count.get(1, 0)
        cancelled = count.get(0, 0)
        no_trades = count.get(2, 0)
        total_trading_days = executed + cancelled + no_trades

        trading_data = [
            ["Trading Metric", "Value"],
            ["Total Trading Days", f"{total_trading_days}"],
            ["Successful Trades", f"{executed}"],
            ["Cancelled Trades", f"{cancelled}"],
            ["No Trades", f"{no_trades}"],
            ["Avg. Buy Trades per day", f"{trades_df['buy'].mean():.1f}"],
            ["Avg. Sell Trades per day", f"{trades_df['sell'].mean():.1f}"],
            [
                "Trade Execution Rate",
                f"{executed / total_trading_days if total_trading_days > 0 else 0:.2%}",
            ],
            [
                "Cancelled Trade Rate",
                f"{cancelled / total_trading_days if total_trading_days > 0 else 0:.2%}",
            ],
            [
                "No Trade Rate",
                f"{no_trades / total_trading_days if total_trading_days > 0 else 0:.2%}",
            ],
        ]

        return self.styling.create_styled_table(
            data=trading_data,
            column_widths=[3.5 * inch, 2.5 * inch],
            header_color=Colors.SLATE_BLUE,
        )

    def create_trading_analysis_summary_table(self) -> Table:
        """Create Trading Analysis Summary table with key trading metrics"""
        try:
            # Extract trading metrics directly from portfolio analytics
            # This method assumes the portfolio has trading_metrics available
            if hasattr(self.portfolio, 'portfolio_analytics'):
                trading_metrics = self.portfolio.portfolio_analytics.trading_metrics()
                trades_ts = trading_metrics["trades_ts"]
                trades_by_ticker = trading_metrics["trades_by_ticker"]
            else:
                # Fallback to existing holdings_summary structure
                trades_ts = self.holdings_summary.get("trades_ts", {})
                trades_by_ticker = self.holdings_summary.get("trades_by_ticker", pd.DataFrame())
            
            # Convert trades_ts to DataFrame for analysis
            if isinstance(trades_ts, dict):
                trades_df = pd.DataFrame(list(trades_ts.values()))
            else:
                trades_df = pd.DataFrame(trades_ts) if trades_ts else pd.DataFrame()
            
            # Calculate basic metrics
            total_trading_days = len(trades_df) if not trades_df.empty else 0
            avg_buy_trades_per_day = trades_df["buy"].mean() if not trades_df.empty and "buy" in trades_df.columns else 0
            avg_sell_trades_per_day = trades_df["sell"].mean() if not trades_df.empty and "sell" in trades_df.columns else 0
            
            # Calculate sell trade returns
            if not trades_by_ticker.empty and "return" in trades_by_ticker.columns:
                positive_return_sell_trades = trades_by_ticker[trades_by_ticker["return"] > 0]["sell"].sum()
                avg_return_all_sell_trades = trades_by_ticker["return"].mean()
            else:
                positive_return_sell_trades = 0
                avg_return_all_sell_trades = 0
            
            # Create table data
            summary_data = [
                ["Trading Summary Metric", "Value"],
                ["Total Trading Days", f"{total_trading_days}"],
                ["Average Buy Trades per Day", f"{avg_buy_trades_per_day:.2f}"],
                ["Average Sell Trades per Day", f"{avg_sell_trades_per_day:.2f}"],
                ["Sell Trades with Positive Return", f"{positive_return_sell_trades}"],
                ["Average Return of All Sell Trades", f"{avg_return_all_sell_trades:.2%}"],
            ]

            return self.styling.create_styled_table(
                data=summary_data,
                column_widths=[4.0 * inch, 2.5 * inch],
                header_color=Colors.EMERALD,
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
            ]
            return self.styling.create_styled_table(
                data=error_data,
                column_widths=[4.0 * inch, 2.5 * inch],
                header_color=Colors.EMERALD,
            )

    def create_trading_activity_chart(self, title: str = None, graph_type: str = "D") -> BytesIO:
        """Create trading activity bar chart with buy/sell bars and second chart with total/net trades lines"""
        plt.style.use("default")
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(10, 7.5), gridspec_kw={"height_ratios": [2, 1]}, sharex=True
        )

        if self.holdings_summary["trades_ts"] and self.holdings_summary["holdings_count"]:
            holdings_dates = list(self.holdings_summary["holdings_count"].keys())
            trades_df = pd.DataFrame(self.holdings_summary["trades_ts"])
            trades_df.index = pd.to_datetime(holdings_dates)
            trades_df = trades_df.sort_index()

            trades_df["buy"] = pd.to_numeric(trades_df["buy"], errors="coerce").fillna(0)
            trades_df["sell"] = pd.to_numeric(trades_df["sell"], errors="coerce").fillna(0)
            trades_df["net_trades"] = trades_df["buy"] - trades_df["sell"]
            trades_df["total_trades"] = trades_df["buy"] + trades_df["sell"]

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
            if graph_type in ["D", "M"] and len(trades_df.resample("M").last()) <= 1:
                ax2.xaxis.set_major_locator(mdates.DayLocator(interval=self.interval))
                ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            elif graph_type == "Q" and len(trades_df.resample("Q").last()) <= 1:
                ax2.xaxis.set_major_locator(mdates.QuarterLocator(interval=self.interval))
                ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
            elif graph_type == "Y" and len(trades_df.resample("Y").last()) <= 1:
                ax2.xaxis.set_major_locator(mdates.YearLocator(interval=self.interval))
                ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%q"))
            else:
                ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=self.interval))
                ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
            ax2.grid(True, alpha=0.3)
            ax2.axhline(y=0, color="black", linestyle="-", alpha=0.5)
            ax2.legend(loc="upper left")

            plt.xticks(rotation=45)
        else:
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

    def create_top_tickers_tables(self) -> tuple[Table, Table, Table]:
        """Create tables for top bought, sold, and traded tickers"""
        if not self.holdings_summary["trades_by_ticker"]:
            return None, None, None

        trades_df = pd.DataFrame(self.holdings_summary["trades_by_ticker"])
        trades_df["total_trades"] = trades_df["buy"] + trades_df["sell"]

        # Common custom styles for smaller padding
        custom_padding_styles = [
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
        ]

        # Top 10 most bought
        top_bought = trades_df.nlargest(10, "buy")[["ticker", "buy"]]
        bought_data = [["Ticker", "Buy Trades"]]
        for _, row in top_bought.iterrows():
            bought_data.append([str(row["ticker"]), str(row["buy"])])

        bought_table = self.styling.create_styled_table(
            data=bought_data,
            column_widths=[1.4 * inch, 1.4 * inch],
            header_color=Colors.SLATE_BLUE,
            custom_styles=custom_padding_styles,
        )

        # Top 10 most sold
        top_sold = trades_df.nlargest(10, "sell")[["ticker", "sell"]]
        sold_data = [["Ticker", "Sell Trades"]]
        for _, row in top_sold.iterrows():
            sold_data.append([str(row["ticker"]), str(row["sell"])])

        sold_table = self.styling.create_styled_table(
            data=sold_data,
            column_widths=[1.4 * inch, 1.4 * inch],
            header_color=Colors.EMERALD,
            custom_styles=custom_padding_styles,
        )

        # Top 10 most traded (total)
        top_traded = trades_df.nlargest(10, "total_trades")[["ticker", "total_trades"]]
        traded_data = [["Ticker", "Total Trades"]]
        for _, row in top_traded.iterrows():
            traded_data.append([str(row["ticker"]), str(row["total_trades"])])

        traded_table = self.styling.create_styled_table(
            data=traded_data,
            column_widths=[1.4 * inch, 1.4 * inch],
            header_color=Colors.GOLD,
            custom_styles=custom_padding_styles,
        )

        return bought_table, sold_table, traded_table

    def add_page_header(self, story: list[BaseDocTemplate], section_name: str = None) -> None:
        """Add section header with divider line to each page"""
        if section_name:
            story.append(Paragraph(section_name, self.section_header_style))

            # Add divider line using a table
            divider_table = Table([[""]], colWidths=[landscape(A4)[0] - 1.5 * inch])
            divider_table.setStyle(self.divider_table_style)
            story.append(divider_table)
            story.append(Spacer(1, 10))  # Increase this to push next content further from divider

    def generate_report(self, filename: str = None) -> str:
        """Generate the restructured PDF report with landscape orientation and page numbers"""
        # Create reports directory if it doesn't exist
        if not os.path.exists("reports"):
            os.makedirs("reports")

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            portfolio_name = (
                self.portfolio.name.replace(" ", "_") if self.portfolio.name else "portfolio"
            )
            filename = f"reports/{portfolio_name}_custom_report_{timestamp}.pdf"
        elif not filename.startswith("reports/"):
            filename = f"reports/{filename}"

        # Create PDF document with landscape orientation and page numbering
        def add_page_number(canvas, doc):
            """Add page number and footer with portfolio info to each page"""
            # Skip footer and page number on first page (title page)
            if doc.page == 1:
                return

            canvas.saveState()

            # Draw footer divider line
            canvas.setStrokeColor(Colors.MEDIUM_GRAY)
            canvas.setLineWidth(0.5)
            canvas.line(0.75 * inch, 0.7 * inch, landscape(A4)[0] - 0.75 * inch, 0.7 * inch)

            # Add portfolio info in footer
            period = f"{self.start_date_str} to {self.end_date_str}"
            footer_text = f"{self.portfolio_name} | Benchmark: {self.benchmark_text} | Period: {period} | Report Runtime: {self.run_date} "

            canvas.setFont("Helvetica", 9)
            canvas.setFillColor(Colors.CHARCOAL)
            canvas.drawString(0.75 * inch, 0.5 * inch, footer_text)

            # Add page number (just the number)
            canvas.drawRightString(landscape(A4)[0] - 0.75 * inch, 0.5 * inch, f"{doc.page}")
            canvas.restoreState()

        doc = BaseDocTemplate(
            filename,
            pagesize=landscape(A4),
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.4 * inch,  # Reduced from 0.75 to 0.4
            bottomMargin=0.75 * inch,
        )

        frame = Frame(
            0.75 * inch,
            0.75 * inch,
            landscape(A4)[0] - 1.5 * inch,
            landscape(A4)[1] - 1.15 * inch,  # Reduced height to account for smaller top margin
            id="normal",
        )

        template = PageTemplate(id="normal", frames=frame, onPage=add_page_number)
        doc.addPageTemplates([template])

        story = []

        # TITLE PAGE
        # Page 1: Title Page with centered portfolio information
        title_page_content = self.create_title_page()
        story.extend(title_page_content)

        # PORTFOLIO OVERVIEW SECTION
        story.append(PageBreak())
        self.add_page_header(story, section_name="Portfolio Overview")
        portfolio_overview = self.create_portfolio_overview_page()
        story.extend(portfolio_overview)

        story.append(PageBreak())
        self.add_page_header(story, section_name="Portfolio Overview - Daily Portfolio Value")
        daily_portfolio_value_chart = self.create_daily_portfolio_value_chart()
        if daily_portfolio_value_chart:
            if isinstance(daily_portfolio_value_chart, BytesIO):
                story.append(Image(daily_portfolio_value_chart, width=10 * inch, height=6 * inch))
            else:
                story.append(daily_portfolio_value_chart)

        if self.include_monthly:
            story.append(PageBreak())
            self.add_page_header(story, section_name="Portfolio Overview - Monthly Portfolio Value")
            monthly_portfolio_value_chart = self.create_monthly_portfolio_value_chart()
            if monthly_portfolio_value_chart:
                if isinstance(monthly_portfolio_value_chart, BytesIO):
                    story.append(
                        Image(monthly_portfolio_value_chart, width=10 * inch, height=6 * inch)
                    )
                else:
                    story.append(monthly_portfolio_value_chart)

        if self.include_annual:
            story.append(PageBreak())
            self.add_page_header(story, section_name="Portfolio Overview - Annual Portfolio Value")
            annual_portfolio_value_chart = self.create_annual_portfolio_value_chart()
            if annual_portfolio_value_chart:
                if isinstance(annual_portfolio_value_chart, BytesIO):
                    story.append(
                        Image(annual_portfolio_value_chart, width=10 * inch, height=6 * inch)
                    )
                else:
                    story.append(annual_portfolio_value_chart)

        # RETURN ANALYSIS SECTION TITLE PAGE
        story.append(PageBreak())
        return_analysis_title = self.create_section_title_page("Return Analysis")
        story.extend(return_analysis_title)

        story.append(PageBreak())
        self.add_page_header(story, section_name="Return Analysis - Daily Returns")
        daily_returns_chart = self.create_daily_returns_chart()
        if daily_returns_chart:
            if isinstance(daily_returns_chart, BytesIO):
                story.append(Image(daily_returns_chart, width=10 * inch, height=6 * inch))
            else:
                story.append(daily_returns_chart)

        if self.include_monthly:
            story.append(PageBreak())
            self.add_page_header(story, section_name="Return Analysis - Monthly Returns")
            monthly_returns_chart = self.create_monthly_returns_chart()
            if monthly_returns_chart:
                if isinstance(monthly_returns_chart, BytesIO):
                    story.append(Image(monthly_returns_chart, width=10 * inch, height=6 * inch))
                else:
                    story.append(monthly_returns_chart)

        if self.include_quarterly:
            story.append(PageBreak())
            self.add_page_header(story, section_name="Return Analysis - Quarterly Returns")
            quarterly_returns_chart = self.create_quarterly_returns_chart()
            if quarterly_returns_chart:
                if isinstance(quarterly_returns_chart, BytesIO):
                    story.append(Image(quarterly_returns_chart, width=10 * inch, height=6 * inch))
                else:
                    story.append(quarterly_returns_chart)

        if self.include_annual:
            story.append(PageBreak())
            self.add_page_header(story, section_name="Return Analysis - Annual Returns")
            annual_returns_chart = self.create_annual_returns_chart()
            if annual_returns_chart:
                if isinstance(annual_returns_chart, BytesIO):
                    story.append(Image(annual_returns_chart, width=10 * inch, height=6 * inch))
                else:
                    story.append(annual_returns_chart)

        story.append(PageBreak())
        self.add_page_header(story, section_name="Return Analysis - Daily Return Distribution")
        daily_distribution_chart = self.create_daily_return_distribution_chart()
        if daily_distribution_chart:
            if isinstance(daily_distribution_chart, BytesIO):
                story.append(Image(daily_distribution_chart, width=10 * inch, height=6 * inch))
            else:
                story.append(daily_distribution_chart)

        if self.include_monthly:
            story.append(PageBreak())
            self.add_page_header(
                story, section_name="Return Analysis - Monthly Return Distribution"
            )
            monthly_distribution_chart = self.create_monthly_return_distribution_chart()
            if monthly_distribution_chart:
                if isinstance(monthly_distribution_chart, BytesIO):
                    story.append(
                        Image(monthly_distribution_chart, width=10 * inch, height=6 * inch)
                    )
                else:
                    story.append(monthly_distribution_chart)

        # HOLDINGS ANALYSIS SECTION TITLE PAGE
        story.append(PageBreak())
        holdings_analysis_title = self.create_section_title_page("Holdings Analysis")
        story.extend(holdings_analysis_title)

        # HOLDINGS ANALYSIS SECTION
        story.append(PageBreak())
        self.add_page_header(story, section_name="Holdings Analysis - Holdings Summary")
        holdings_table = self.create_holdings_summary_table()
        if holdings_table:
            story.append(holdings_table)

        story.append(PageBreak())
        self.add_page_header(story, section_name="Holdings Analysis - Holdings Over Time")
        holdings_chart = self.create_holdings_analysis_chart()
        story.append(Image(holdings_chart, width=10 * inch, height=6 * inch))

        story.append(PageBreak())
        self.add_page_header(story, section_name="Holdings Analysis - Holding Duration Summary")

        duration_title = self.create_table_title("Duration Summary", Colors.SLATE_BLUE)
        story.append(duration_title)
        story.append(Spacer(1, 5))

        duration_summary_table = self.create_holding_duration_summary_table()
        if duration_summary_table:
            story.append(duration_summary_table)
            story.append(Spacer(1, 20))  # Add space between sections

        # Add top durations section on the same page
        story.append(Spacer(1, 10))
        longest_table, shortest_table = self.create_top_duration_tables()
        style = TableStyle(
            [("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]
        )
        if longest_table and shortest_table:
            # Create titles for the duration tables
            longest_title = self.create_table_title("Top 5 Longest Hold", Colors.EMERALD)
            shortest_title = self.create_table_title("Top 5 Shortest Hold", Colors.GOLD)

            # Create containers with titles and tables
            longest_container = Table(
                [[longest_title], [Spacer(1, 8)], [longest_table]], colWidths=[3.5 * inch]
            )
            longest_container.setStyle(style)

            shortest_container = Table(
                [[shortest_title], [Spacer(1, 8)], [shortest_table]], colWidths=[3.5 * inch]
            )
            shortest_container.setStyle(style)

            # Add spacer between the two tables
            spacer_cell = Table([[Spacer(1, 1)]], colWidths=[1.5 * inch])
            duration_tables_data = [[longest_container, spacer_cell, shortest_container]]
            combined_duration_table = Table(
                duration_tables_data, colWidths=[3.5 * inch, 1.5 * inch, 3.5 * inch]
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
        self.add_page_header(story, section_name="Holdings Analysis - Duration vs Sector")
        sector_duration_chart = self.create_sector_duration_boxplot()
        story.append(Image(sector_duration_chart, width=10 * inch, height=6 * inch))

        # SECTOR ANALYSIS SECTION TITLE PAGE
        story.append(PageBreak())
        sector_analysis_title = self.create_section_title_page("Sector Analysis")
        story.extend(sector_analysis_title)

        # SECTOR ANALYSIS SECTION
        story.append(PageBreak())
        self.add_page_header(story, section_name="Sector Analysis - Exposure Over Time")
        sector_chart = self.create_sector_exposure_chart()
        story.append(Image(sector_chart, width=10 * inch, height=6.4 * inch))

        story.append(PageBreak())
        self.add_page_header(story, section_name="Sector Analysis - Average Sector Composition (%)")
        pie_chart = self.create_sector_composition_pie()
        story.append(Image(pie_chart, width=8.5 * inch, height=6.4 * inch))

        # PNL ANALYSIS SECTION TITLE PAGE
        story.append(PageBreak())
        pnl_analysis_title = self.create_section_title_page("PnL Analysis")
        story.extend(pnl_analysis_title)

        # PNL ANALYSIS SECTION
        story.append(PageBreak())
        self.add_page_header(story, section_name="PnL Analysis - Daily Net PnL")
        daily_pnl_chart = self.create_daily_pnl_chart()
        if daily_pnl_chart:
            if isinstance(daily_pnl_chart, BytesIO):
                story.append(Image(daily_pnl_chart, width=10 * inch, height=6 * inch))
            else:
                story.append(daily_pnl_chart)

        if self.include_monthly:
            story.append(PageBreak())
            self.add_page_header(story, section_name="PnL Analysis - Monthly Net PnL")
            monthly_pnl_chart = self.create_monthly_pnl_chart()
            if monthly_pnl_chart:
                if isinstance(monthly_pnl_chart, BytesIO):
                    story.append(Image(monthly_pnl_chart, width=10 * inch, height=6 * inch))
                else:
                    story.append(monthly_pnl_chart)

        if self.include_annual:
            story.append(PageBreak())
            self.add_page_header(story, section_name="PnL Analysis - Annual Net PnL")
            annual_pnl_chart = self.create_annual_pnl_chart()
            if annual_pnl_chart:
                if isinstance(annual_pnl_chart, BytesIO):
                    story.append(Image(annual_pnl_chart, width=10 * inch, height=6 * inch))
                else:
                    story.append(annual_pnl_chart)

        # TRADING ANALYSIS SECTION TITLE PAGE
        story.append(PageBreak())
        trading_analysis_title = self.create_section_title_page("Trading Analysis")
        story.extend(trading_analysis_title)

        # TRADING ANALYSIS SECTION
        story.append(PageBreak())
        self.add_page_header(story, section_name="Trading Analysis - Summary")
        trading_summary_table = self.create_trading_analysis_summary_table()
        story.append(trading_summary_table)

        story.append(PageBreak())
        self.add_page_header(story, section_name="Trading Analysis - Key Metrics")
        trading_table = self.create_trading_metrics_table()
        story.append(trading_table)

        story.append(PageBreak())
        self.add_page_header(story, section_name="Trading Analysis - Trading Over Time")
        trading_chart = self.create_trading_activity_chart(graph_type="D")
        story.append(Image(trading_chart, width=10 * inch, height=6.4 * inch))

        story.append(PageBreak())
        self.add_page_header(story, section_name="Trading Analysis - Top 10 Tickers")
        bought_table, sold_table, traded_table = self.create_top_tickers_tables()
        style = TableStyle(
            [("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]
        )
        if bought_table and sold_table and traded_table:
            # Create titles for each table
            bought_title = self.create_table_title("Top 10 Most Bought Tickers", Colors.SLATE_BLUE)
            sold_title = self.create_table_title("Top 10 Most Sold Tickers", Colors.EMERALD)
            traded_title = self.create_table_title("Top 10 Most Traded Tickers", Colors.GOLD)

            # Create containers with titles and tables
            bought_container = Table(
                [[bought_title], [Spacer(1, 8)], [bought_table]], colWidths=[2.2 * inch]
            )
            bought_container.setStyle(style)

            sold_container = Table(
                [[sold_title], [Spacer(1, 8)], [sold_table]], colWidths=[2.2 * inch]
            )
            sold_container.setStyle(style)

            traded_container = Table(
                [[traded_title], [Spacer(1, 8)], [traded_table]], colWidths=[2.2 * inch]
            )
            traded_container.setStyle(style)

            # Arrange three containers side by side with consistent alignment
            spacer_cell1 = Table([[Spacer(1, 1)]], colWidths=[1.0 * inch])
            spacer_cell1.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))

            spacer_cell2 = Table([[Spacer(1, 1)]], colWidths=[1.0 * inch])
            spacer_cell2.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))

            tables_data = [
                [bought_container, spacer_cell1, sold_container, spacer_cell2, traded_container]
            ]
            three_tables = Table(
                tables_data, colWidths=[2.2 * inch, 1.0 * inch, 2.2 * inch, 1.0 * inch, 2.2 * inch]
            )
            three_tables.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
        story.append(three_tables)

        # Build PDF with page numbers
        doc.build(story)
        print(f"Custom PDF report saved to: {filename}")
        return filename


def generate_report(
    backtest_or_portfolio,
    rf=0.02,
    bmk_returns=0.1,
    filename=None,
    dpi=300,
    include_monthly=True,
    include_quarterly=True,
    include_annual=True,
) -> str:
    # Handle both Backtest and Portfolio objects
    if hasattr(backtest_or_portfolio, 'generate_analytics'):
        # This is a Backtest object
        analytics = backtest_or_portfolio.generate_analytics(rf=rf, bmk_returns=bmk_returns)
        portfolio = backtest_or_portfolio.portfolio
        
        # Store analytics on portfolio for access in report generator
        portfolio.portfolio_analytics = analytics
        
        # Generate required data structures
        metrics = analytics.performance_metrics(rf=rf, bmk_returns=bmk_returns)
        trading_metrics = analytics.trading_metrics()
        holdings_summary = {
            "holdings_count": analytics.holdings_metrics(),
            "trades_ts": list(trading_metrics["trades_ts"].values()),
            "trades_by_ticker": trading_metrics["trades_by_ticker"],
        }
    else:
        # This is a Portfolio object (legacy support)
        portfolio = backtest_or_portfolio
        if not hasattr(portfolio, "metrics") or not hasattr(portfolio, "holdings_summary"):
            raise ValueError("Portfolio object must have metrics and holdings_summary attributes")
        metrics = portfolio.metrics
        holdings_summary = portfolio.holdings_summary

    generator = ReportGenerator(
        portfolio,
        metrics,
        holdings_summary,
        dpi=dpi,
        include_monthly=include_monthly,
        include_quarterly=include_quarterly,
        include_annual=include_annual,
    )
    return generator.generate_report(filename=filename)
