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
            date.strftime("%Y-%m-%d"): value for date, value in monthly_portfolio_value.items()
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
            right_color=Colors.CHART_DARK_GRAY,
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
        if "monthly_sharpe" in self.metrics and self.metrics["monthly_sharpe"] is not None and len(self.metrics["monthly_sharpe"]) > 0:
            sharpe_series = self.metrics["monthly_sharpe"]
            # Convert pandas Series to dictionary with string dates
            for date_idx, value in sharpe_series.items():
                date_str = date_idx.strftime("%Y-%m-%d")
                monthly_sharpe_dict[date_str] = value

        # Prepare monthly IR data - assuming pandas Series with date index
        monthly_ir_dict = {}
        if "monthly_ir" in self.metrics and self.metrics["monthly_ir"] is not None and len(self.metrics["monthly_ir"]) > 0:
            ir_series = self.metrics["monthly_ir"]
            # Convert pandas Series to dictionary with string dates
            for date_idx, value in ir_series.items():
                date_str = date_idx.strftime("%Y-%m-%d")
                monthly_ir_dict[date_str] = value

        return self.styling.create_generic_dual_axis_chart(
            data_dict_left=monthly_sharpe_dict,
            data_dict_right=monthly_ir_dict,
            left_y_label="Sharpe Ratio",
            right_y_label="Information Ratio",
            right_color=Colors.CHART_DARK_GRAY,
            right_linestyle=":",
            figsize=(10, 6),
            resample_freq="M",
            no_data_message="No monthly Sharpe/IR data available",
            normal_style=self.normal_style,
            show_crisis_periods=True,
            interval=1,
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
            return_pct = f"{row['return']:.2%}" if pd.notna(row['return']) else "N/A"
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
            return_pct = f"{row['return']:.2%}" if pd.notna(row['return']) else "N/A"
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
            ["Maximum Holdings", f"{max_holdings}", str(pd.to_datetime(max_date).date())],
            ["Minimum Non-zero Holdings", f"{min_holdings}", str(pd.to_datetime(min_date).date())],
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
            ["Duration Metric", "Value (Days)", ""],
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
        """Create holdings over time chart"""
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
        
        return self.styling.create_generic_line_chart(
            data_dict=self.holdings_summary,
            color=Colors.CHART_NAVY,
            resample_freq=None,
            date_format="%Y-%m",
            y_label="Number of Holdings",
            y_formatter=plt.FuncFormatter(lambda x, p: f"{x:,.0f}"),
            no_data_message="No holdings data available",
            interval=interval,
            normal_style=self.normal_style,
            graph_type="D",
        )

    def create_top_duration_tables(self) -> tuple[Table, Table]:
        """Create tables for top 10 longest and shortest hold tickers with professional styling"""
        # Get duration data from trading metrics
        trading_metrics = self.analytics.trading_metrics()
        trades_by_ticker = trading_metrics["trades_by_ticker"]
        
        if trades_by_ticker.empty:
            return None, None

        # Common custom styles for smaller padding
        custom_padding_styles = [
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
        ]

        # Top 10 longest hold
        top_longest = trades_by_ticker.nlargest(10, "duration")[["ticker", "duration"]]
        longest_data = [["Ticker", "Duration (Days)"]]
        for _, row in top_longest.iterrows():
            duration_str = f"{row['duration']:.1f}" if pd.notna(row['duration']) else "N/A"
            longest_data.append([str(row["ticker"]), duration_str])

        longest_table = self.styling.create_styled_table(
            data=longest_data,
            column_widths=[1.8 * inch, 1.8 * inch],
            header_color=Colors.SLATE_BLUE,
            custom_styles=custom_padding_styles,
        )

        # Top 10 shortest hold
        top_shortest = trades_by_ticker.nsmallest(10, "duration")[["ticker", "duration"]]
        shortest_data = [["Ticker", "Duration (Days)"]]
        for _, row in top_shortest.iterrows():
            duration_str = f"{row['duration']:.1f}" if pd.notna(row['duration']) else "N/A"
            shortest_data.append([str(row["ticker"]), duration_str])

        shortest_table = self.styling.create_styled_table(
            data=shortest_data,
            column_widths=[1.8 * inch, 1.8 * inch],
            header_color=Colors.EMERALD,
            custom_styles=custom_padding_styles,
        )

        return longest_table, shortest_table

    def add_page_header(self, story: list, section_name: str = None) -> None:
        """Add page header with section name"""
        if section_name:
            story.append(Paragraph(section_name, self.section_header_style))
            story.append(Spacer(1, 20))

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
        self.add_page_header(story, section_name="Portfolio Overview - Config and Key Metrics")
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
        self.add_page_header(story, section_name="Return Analysis - Monthly Return Distribution")
        distribution_chart = self.create_monthly_return_distribution_chart()
        story.append(Image(distribution_chart, width=10 * inch, height=6 * inch))
        story.append(PageBreak())

        # Page 5: Return Analysis - Monthly Sharpe and IR
        self.add_page_header(
            story, section_name="Return Analysis - Monthly Sharpe and Information Ratios"
        )
        sharpe_ir_chart = self.create_monthly_sharpe_ir_chart()
        story.append(Image(sharpe_ir_chart, width=10 * inch, height=6 * inch))
        story.append(PageBreak())

        # Page 6: Return Analysis - Top 10 Returns by Tickers
        self.add_page_header(story, section_name="Return Analysis - Top 10 Returns by Tickers")
        highest_table, lowest_table = self.create_top_return_tables()
        
        if highest_table and lowest_table:
            # Create titles for the return tables
            highest_title = self.styling.create_table_title("Top 10 Highest Average Returns", Colors.SLATE_BLUE)
            lowest_title = self.styling.create_table_title("Top 10 Lowest Average Returns", Colors.EMERALD)

            # Create containers with titles and tables
            highest_container = Table(
                [[highest_title], [Spacer(1, 8)], [highest_table]], colWidths=[3.6 * inch]
            )
            highest_container.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"), 
                ("ALIGN", (0, 0), (-1, -1), "CENTER")
            ]))

            lowest_container = Table(
                [[lowest_title], [Spacer(1, 8)], [lowest_table]], colWidths=[3.6 * inch]
            )
            lowest_container.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"), 
                ("ALIGN", (0, 0), (-1, -1), "CENTER")
            ]))

            # Add spacer between the two tables
            spacer_cell = Table([[Spacer(1, 1)]], colWidths=[2.0 * inch])
            return_tables_data = [[highest_container, spacer_cell, lowest_container]]
            combined_return_table = Table(
                return_tables_data, colWidths=[3.6 * inch, 2.0 * inch, 3.6 * inch]
            )
            combined_return_table.setStyle(
                TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ])
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
        self.add_page_header(story, section_name="Holdings Analysis - Holdings Over Time")
        holdings_chart = self.create_holdings_analysis_chart()
        story.append(Image(holdings_chart, width=10 * inch, height=6 * inch))
        story.append(PageBreak())

        # Page 9: Holdings Analysis - Top 10 Duration Tables
        self.add_page_header(story, section_name="Holdings Analysis - Top 10 Duration by Tickers")
        
        # Create top duration tables
        longest_table, shortest_table = self.create_top_duration_tables()
        
        if longest_table and shortest_table:
            # Create titles for the duration tables
            longest_title = self.styling.create_table_title("Top 10 Longest Hold", Colors.SLATE_BLUE)
            shortest_title = self.styling.create_table_title("Top 10 Shortest Hold", Colors.EMERALD)

            # Create containers with titles and tables
            style = TableStyle(
                [("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]
            )
            
            longest_container = Table(
                [[longest_title], [Spacer(1, 8)], [longest_table]], colWidths=[3.6 * inch]
            )
            longest_container.setStyle(style)

            shortest_container = Table(
                [[shortest_title], [Spacer(1, 8)], [shortest_table]], colWidths=[3.6 * inch]
            )
            shortest_container.setStyle(style)

            # Add spacer between the two tables
            spacer_cell = Table([[Spacer(1, 1)]], colWidths=[2.0 * inch])
            duration_tables_data = [[longest_container, spacer_cell, shortest_container]]
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
