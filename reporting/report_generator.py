import io
import os
from collections import Counter
from datetime import datetime
from enum import Enum
from io import BytesIO

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
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


# Professional inspired color palette
class Colors:
    # Primary colors for ReportLab (PDF elements) - inspired
    NAVY_BLUE = colors.HexColor("#003366")  # Deep navy
    DEEP_BLUE = colors.HexColor("#001a33")  # Darker navy
    SLATE_BLUE = colors.HexColor("#2c5282")  # Professional blue

    # Accent colors for ReportLab (PDF elements) - gold and professional tones
    GOLD = colors.HexColor("#DAA520")  # signature gold
    AMBER = colors.HexColor("#FF8C00")  # Darker gold
    EMERALD = colors.HexColor("#2F855A")  # Professional green
    CORAL = colors.HexColor("#E53E3E")  # Professional red

    # Neutral colors for ReportLab (PDF elements)
    CHARCOAL = colors.HexColor("#2D3748")  # Professional dark gray
    LIGHT_GRAY = colors.HexColor("#F7FAFC")  # Very light gray
    MEDIUM_GRAY = colors.HexColor("#E2E8F0")  # Medium gray
    DARK_GRAY = colors.HexColor("#4A5568")  # Darker gray
    WHITE = colors.HexColor("#FFFFFF")

    # Chart colors for matplotlib (string format) - inspired
    CHART_NAVY = "#003366"  # Primary navy
    CHART_GOLD = "#DAA520"  # signature gold
    CHART_BLUE = "#2c5282"  # Professional blue
    CHART_GREEN = "#2F855A"  # Professional green
    CHART_RED = "#E53E3E"  # Professional red
    CHART_AMBER = "#FF8C00"  # Darker gold
    CHART_TEAL = "#2C7A7B"  # Professional teal
    CHART_DEEP_BLUE = "#001a33"  # Darker navy
    CHART_CHARCOAL = "#2D3748"  # Professional dark gray
    CHART_LIGHT_GRAY = "#F7FAFC"  # Very light gray
    CHART_MEDIUM_GRAY = "#E2E8F0"  # Medium gray
    CHART_DARK_GRAY = "#4A5568"  # Darker gray
    CHART_WHITE = "#FFFFFF"


class ReportGenerator:
    def __init__(self, portfolio, metrics, holdings_summary):
        self.portfolio = portfolio
        self.metrics = metrics
        self.holdings_summary = holdings_summary
        self.styles = getSampleStyleSheet()

        # Create custom styles with professional typography
        self.title_style = ParagraphStyle(
            "CustomTitle",
            parent=self.styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=28,
            spaceAfter=30,
            spaceBefore=20,
            alignment=TA_CENTER,
            textColor=Colors.NAVY_BLUE,
            leading=32,
        )

        self.block_title_style = ParagraphStyle(
            "BlockTitle",
            parent=self.styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=18,
            spaceAfter=16,
            spaceBefore=25,
            textColor=Colors.DEEP_BLUE,
            alignment=TA_CENTER,
            leading=22,
        )

        self.section_title_style = ParagraphStyle(
            "SectionTitle",
            parent=self.styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=14,
            spaceAfter=10,
            spaceBefore=15,
            textColor=Colors.SLATE_BLUE,
            alignment=TA_CENTER,
            leading=16,
        )

        self.normal_style = ParagraphStyle(
            "CustomNormal",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            spaceAfter=8,
            textColor=Colors.CHARCOAL,
            leading=14,
            alignment=TA_JUSTIFY,
        )

        self.page_header_style = ParagraphStyle(
            "PageHeader",
            parent=self.styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=16,
            spaceAfter=12,
            spaceBefore=8,
            textColor=Colors.NAVY_BLUE,
            alignment=TA_CENTER,
            leading=18,
        )

        # Portfolio info style for header
        self.portfolio_info_style = ParagraphStyle(
            "PortfolioInfo",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            spaceAfter=8,
            spaceBefore=5,
            textColor=Colors.CHARCOAL,
            alignment=TA_CENTER,
            leading=12,
        )

        # Section header style
        self.section_header_style = ParagraphStyle(
            "SectionHeader",
            parent=self.styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=14,
            spaceAfter=8,
            spaceBefore=10,
            textColor=Colors.SLATE_BLUE,
            alignment=TA_LEFT,
            leading=16,
        )

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

    def create_title_page(self):
        """Create a centered title page with key portfolio information"""
        story = []

        # Add spacer to center content vertically
        story.append(Spacer(1, 2.5 * inch))

        # Portfolio Name (Main Title)
        portfolio_name = self.portfolio.name or "Unnamed Portfolio"
        title_style = ParagraphStyle(
            "TitlePageTitle",
            parent=self.styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=36,
            spaceAfter=60,
            spaceBefore=20,
            alignment=TA_CENTER,
            textColor=Colors.NAVY_BLUE,
            leading=42,
        )
        story.append(Paragraph(portfolio_name, title_style))

        # Create info style for title page
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

        # Benchmark
        benchmark_text = (
            self.portfolio.benchmark.value
            if hasattr(self.portfolio.benchmark, "value")
            else str(self.portfolio.benchmark)
        )
        story.append(Paragraph(f"<b>Benchmark:</b> {benchmark_text}", info_style))

        # Run Date
        run_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        story.append(Paragraph(f"<b>Run Date:</b> {run_date}", info_style))

        # Period
        portfolio_dates = list(self.portfolio.portfolio_value_history.keys())
        if portfolio_dates:
            start_date = min(portfolio_dates).strftime("%Y-%m-%d")
            end_date = max(portfolio_dates).strftime("%Y-%m-%d")
            period_text = f"{start_date} to {end_date}"
        else:
            period_text = "N/A"
        story.append(Paragraph(f"<b>Analysis Period:</b> {period_text}", info_style))

        return story

    def create_section_title_page(self, section_name):
        """Create a centered section title page"""
        story = []

        # Add spacer to center content vertically
        story.append(Spacer(1, 3 * inch))

        # Section Name (Main Title)
        section_title_style = ParagraphStyle(
            "SectionTitlePage",
            parent=self.styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=48,
            spaceAfter=60,
            spaceBefore=20,
            alignment=TA_CENTER,
            textColor=Colors.NAVY_BLUE,
            leading=54,
        )
        story.append(Paragraph(section_name, section_title_style))

        return story

    def create_header_info_block(self):
        """Create the header information block with professional styling"""
        # Get analysis period
        portfolio_dates = list(self.portfolio.portfolio_value_history.keys())
        start_date = min(portfolio_dates) if portfolio_dates else "N/A"
        end_date = max(portfolio_dates) if portfolio_dates else "N/A"

        header_data = [
            ["Portfolio Name:", self.portfolio.name or "Unnamed Portfolio"],
            [
                "Benchmark:",
                (
                    self.portfolio.benchmark.value
                    if hasattr(self.portfolio.benchmark, "value")
                    else str(self.portfolio.benchmark)
                ),
            ],
            ["Run Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            [
                "Period:",
                f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            ],
        ]

        table = Table(header_data, colWidths=[2.8 * inch, 4.5 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 12),
                    ("LEFTPADDING", (0, 0), (-1, -1), 15),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 15),
                    ("BACKGROUND", (0, 0), (0, -1), Colors.LIGHT_GRAY),
                    ("BACKGROUND", (1, 0), (1, -1), Colors.WHITE),
                    ("LINEBELOW", (0, 0), (-1, -1), 1, Colors.MEDIUM_GRAY),
                    ("LINEAFTER", (0, 0), (0, -1), 1, Colors.MEDIUM_GRAY),
                    ("BOX", (0, 0), (-1, -1), 1.5, Colors.SLATE_BLUE),
                ]
            )
        )

        return table

    def create_portfolio_config_block(self):
        """Create the portfolio configuration block with title and enhanced styling"""
        # Create title
        title = Paragraph("Portfolio Configuration", self.section_title_style)

        # Get constraints information
        constraints_info = "None"
        if hasattr(self.portfolio, "constraints") and self.portfolio.constraints:
            constraints_list = self.portfolio.constraints.list_constraints()
            constraints_info = "\n".join([f"{k}: {v}" for k, v in constraints_list.items()])

        config_data = []
        for k, v in self.portfolio.setup.items():
            if isinstance(v, list) and all(isinstance(item, Enum) for item in v):
                config_data.append([f"{k}:", "\n".join([vv.value for vv in v])])
            elif isinstance(v, list):
                config_data.append([f"{k}:", "\n".join(v)])
            elif not isinstance(v, str):
                if isinstance(v, (int, float)) and 0 <= v <= 1:
                    config_data.append([f"{k}:", f"{v:.2%}"])
                else:
                    config_data.append([f"{k}:", f"{v:,.2f}"])
            else:
                config_data.append([f"{k}:", v])

        table = Table(config_data, colWidths=[2.0 * inch, 2.5 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("BACKGROUND", (0, 0), (0, -1), Colors.LIGHT_GRAY),
                    ("BACKGROUND", (1, 0), (1, -1), Colors.WHITE),
                    ("LINEBELOW", (0, 0), (-1, -1), 1, Colors.MEDIUM_GRAY),
                    ("LINEAFTER", (0, 0), (0, -1), 1, Colors.MEDIUM_GRAY),
                    ("BOX", (0, 0), (-1, -1), 1.5, Colors.EMERALD),
                ]
            )
        )

        # Combine title and table
        content = []
        content.append(title)
        content.append(Spacer(1, 10))
        content.append(table)

        return content

    def create_key_performance_block(self):
        """Create the key performance metrics block with title and professional colors"""
        # Create title
        title = Paragraph("Key Performance Metrics", self.section_title_style)

        performance_data = [
            ["Total Return:", f"{self.metrics['total_return']:.2%}"],
            ["Annualized Return:", f"{self.metrics['annualized_return']:.2%}"],
            ["Overall Sharpe Ratio:", f"{self.metrics['overall_sharpe_ratio']:.2f}"],
            ["Win Rate:", f"{self.metrics['win_rate']:.2%}"],
            ["Daily Win Rate:", f"{self.metrics['avg_win']:.2%}"],
            ["Sharpe Ratio:", f"{self.metrics['overall_sharpe_ratio']:.2f}"],
        ]

        table = Table(performance_data, colWidths=[2.0 * inch, 2.5 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("BACKGROUND", (0, 0), (0, -1), Colors.LIGHT_GRAY),
                    ("BACKGROUND", (1, 0), (1, -1), Colors.WHITE),
                    ("LINEBELOW", (0, 0), (-1, -1), 1, Colors.MEDIUM_GRAY),
                    ("LINEAFTER", (0, 0), (0, -1), 1, Colors.MEDIUM_GRAY),
                    ("BOX", (0, 0), (-1, -1), 1.5, Colors.AMBER),
                ]
            )
        )

        # Combine title and table
        content = []
        content.append(title)
        content.append(Spacer(1, 10))
        content.append(table)

        return content

    def create_portfolio_info_header(self):
        """Create portfolio info header for each page"""
        portfolio_dates = list(self.portfolio.portfolio_value_history.keys())
        start_date = min(portfolio_dates) if portfolio_dates else "N/A"
        end_date = max(portfolio_dates) if portfolio_dates else "N/A"

        portfolio_name = self.portfolio.name or "Unnamed Portfolio"
        benchmark = (
            self.portfolio.benchmark.value
            if hasattr(self.portfolio.benchmark, "value")
            else str(self.portfolio.benchmark)
        )
        run_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        period = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"

        info_text = (
            f"{portfolio_name} | Benchmark: {benchmark} | Run Date: {run_date} | Period: {period}"
        )
        return Paragraph(info_text, self.portfolio_info_style)

    def create_holdings_analysis_chart(self):
        """Create holdings count over time line chart with professional styling"""
        # Set matplotlib style for professional look
        plt.style.use("default")
        plt.rcParams.update(
            {
                "font.family": ["Arial", "Helvetica", "sans-serif"],
                "font.size": 12,
                "axes.titlesize": 16,
                "axes.labelsize": 12,
                "xtick.labelsize": 10,
                "ytick.labelsize": 10,
                "legend.fontsize": 10,
                "axes.spines.top": False,
                "axes.spines.right": False,
                "axes.grid": True,
                "grid.alpha": 0.3,
            }
        )

        fig, ax = plt.subplots(figsize=(8, 4.5))
        fig.patch.set_facecolor("white")

        if self.holdings_summary["holdings_count"]:
            # Create dataframe from holdings count data
            holdings_dates = list(self.holdings_summary["holdings_count"].keys())
            holdings_counts = list(self.holdings_summary["holdings_count"].values())

            holdings_df = pd.DataFrame(
                {"Date": pd.to_datetime(holdings_dates), "Count": holdings_counts}
            )
            holdings_df = holdings_df.sort_values("Date")

            ax.plot(
                holdings_df["Date"],
                holdings_df["Count"],
                linewidth=1,
                color=Colors.CHART_NAVY,
            )
            ax.set_title(
                "Holdings Count Over Time",
                fontsize=18,
                fontweight="bold",
                color=Colors.CHART_DEEP_BLUE,
                pad=20,
            )
            ax.set_ylabel("Number of Holdings", fontsize=14, color=Colors.CHART_CHARCOAL)
            ax.set_xlabel("Date", fontsize=14, color=Colors.CHART_CHARCOAL)

            # Styling
            ax.tick_params(colors=Colors.CHART_CHARCOAL)
            ax.grid(True, alpha=0.3, color=Colors.CHART_MEDIUM_GRAY)
            ax.set_facecolor(Colors.CHART_LIGHT_GRAY)

            # Add more ticks
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=self.interval))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

            plt.xticks(rotation=45)
        else:
            ax.text(
                0.5,
                0.5,
                "No holdings data available",
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=14,
                color=Colors.CHART_CHARCOAL,
            )
            ax.set_title(
                "Holdings Count Over Time",
                fontsize=18,
                fontweight="bold",
                color=Colors.CHART_DEEP_BLUE,
                pad=20,
            )

        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(
            buf, format="png", dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none"
        )
        buf.seek(0)
        plt.close()

        return buf

    def create_holdings_summary_table(self):
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

        table = Table(summary_data, colWidths=[2.2 * inch, 1.8 * inch, 2.5 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), Colors.NAVY_BLUE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), Colors.WHITE),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("FONTSIZE", (0, 1), (-1, -1), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), Colors.LIGHT_GRAY),
                    ("LINEBELOW", (0, 0), (-1, -1), 1, Colors.MEDIUM_GRAY),
                    ("BOX", (0, 0), (-1, -1), 1.5, Colors.NAVY_BLUE),
                ]
            )
        )

        return table

    def create_holding_duration_summary_table(self):
        """Create holding duration summary table with professional styling"""
        if not self.holdings_summary["duration_by_ticker"]:
            return None

        duration_df = pd.DataFrame(self.holdings_summary["duration_by_ticker"])
        durations = duration_df["duration"]

        max_duration = durations.max()
        min_duration = durations.min()
        avg_duration = durations.mean()

        duration_data = [
            ["Duration Metric", "Value (Days)"],
            ["Maximum Duration", f"{max_duration}"],
            ["Minimum Duration", f"{min_duration}"],
            ["Average Duration", f"{avg_duration:.1f}"],
        ]

        table = Table(duration_data, colWidths=[2.8 * inch, 2.2 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), Colors.EMERALD),
                    ("TEXTCOLOR", (0, 0), (-1, 0), Colors.WHITE),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("FONTSIZE", (0, 1), (-1, -1), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), Colors.LIGHT_GRAY),
                    ("LINEBELOW", (0, 0), (-1, -1), 1, Colors.MEDIUM_GRAY),
                    ("BOX", (0, 0), (-1, -1), 1.5, Colors.EMERALD),
                ]
            )
        )

        return table

    def create_top_duration_tables(self):
        """Create tables for top longest and shortest hold tickers with professional styling"""
        if not self.holdings_summary["duration_by_ticker"]:
            return None, None

        duration_df = pd.DataFrame(self.holdings_summary["duration_by_ticker"])

        # Top 5 longest hold
        top_longest = duration_df.nlargest(5, "duration")[["ticker", "duration"]]
        longest_data = [["Ticker", "Duration (Days)"]]
        for _, row in top_longest.iterrows():
            longest_data.append([str(row["ticker"]), str(row["duration"])])

        longest_table = Table(longest_data, colWidths=[1.7 * inch, 1.8 * inch])
        longest_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), Colors.SLATE_BLUE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), Colors.WHITE),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("FONTSIZE", (0, 1), (-1, -1), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), Colors.LIGHT_GRAY),
                    ("LINEBELOW", (0, 0), (-1, -1), 1, Colors.MEDIUM_GRAY),
                    ("BOX", (0, 0), (-1, -1), 1.5, Colors.SLATE_BLUE),
                ]
            )
        )

        # Top 5 shortest hold
        top_shortest = duration_df.nsmallest(5, "duration")[["ticker", "duration"]]
        shortest_data = [["Ticker", "Duration (Days)"]]
        for _, row in top_shortest.iterrows():
            shortest_data.append([str(row["ticker"]), str(row["duration"])])

        shortest_table = Table(shortest_data, colWidths=[1.7 * inch, 1.8 * inch])
        shortest_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), Colors.CORAL),
                    ("TEXTCOLOR", (0, 0), (-1, 0), Colors.WHITE),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("FONTSIZE", (0, 1), (-1, -1), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), Colors.LIGHT_GRAY),
                    ("LINEBELOW", (0, 0), (-1, -1), 1, Colors.MEDIUM_GRAY),
                    ("BOX", (0, 0), (-1, -1), 1.5, Colors.CORAL),
                ]
            )
        )

        return longest_table, shortest_table

    def create_portfolio_value_chart(self):
        """Create portfolio value over time line chart with professional styling"""
        try:
            # Set professional matplotlib styling
            plt.style.use("default")
            plt.rcParams.update(
                {
                    "font.family": ["Arial", "Helvetica", "sans-serif"],
                    "font.size": 12,
                    "axes.titlesize": 18,
                    "axes.labelsize": 14,
                    "xtick.labelsize": 11,
                    "ytick.labelsize": 11,
                    "legend.fontsize": 12,
                    "axes.spines.top": False,
                    "axes.spines.right": False,
                    "axes.grid": True,
                    "grid.alpha": 0.3,
                }
            )

            fig, ax = plt.subplots(figsize=(9, 4.5))
            fig.patch.set_facecolor("white")

            if (
                self.portfolio.portfolio_value_history
                and len(self.portfolio.portfolio_value_history) > 0
            ):
                dates = pd.to_datetime(list(self.portfolio.portfolio_value_history.keys()))
                values = list(self.portfolio.portfolio_value_history.values())

                ax.plot(
                    dates,
                    values,
                    linewidth=1,
                    color=Colors.CHART_NAVY,
                    label="Portfolio Value",
                )
            else:
                # No data available - create a placeholder message
                ax.text(
                    0.5,
                    0.5,
                    "No portfolio value data available",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=16,
                    color=Colors.CHART_CHARCOAL,
                )
            # Set title and labels (common for both cases)
            ax.set_title(
                "Portfolio Value Over Time",
                fontsize=20,
                fontweight="bold",
                color=Colors.CHART_DEEP_BLUE,
                pad=25,
            )

            # Only set axis labels if we have data
            if (
                self.portfolio.portfolio_value_history
                and len(self.portfolio.portfolio_value_history) > 0
            ):
                ax.set_xlabel("Date", fontsize=14, color=Colors.CHART_CHARCOAL)
                ax.set_ylabel("Portfolio Value ($)", fontsize=14, color=Colors.CHART_CHARCOAL)

                # Date formatting
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=self.interval))
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

                # Y-axis formatting
                ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))

                # Legend styling
                legend = ax.legend(
                    frameon=True,
                    fancybox=True,
                    shadow=True,
                    facecolor=Colors.CHART_WHITE,
                    edgecolor=Colors.CHART_BLUE,
                )
                legend.get_frame().set_alpha(0.9)

            # Professional styling (applied to both cases)
            ax.tick_params(colors=Colors.CHART_CHARCOAL)
            ax.grid(True, alpha=0.3, color=Colors.CHART_MEDIUM_GRAY)
            ax.set_facecolor(Colors.CHART_LIGHT_GRAY)

            plt.tight_layout()

            buffer = BytesIO()
            fig.savefig(
                buffer,
                format="png",
                dpi=300,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
            buffer.seek(0)
            plt.close()

            return buffer
        except Exception as e:
            plt.close()
            return Paragraph(f"Error creating portfolio value chart: {str(e)}", self.normal_style)

    def create_daily_returns_chart(self):
        """Create daily returns chart with professional styling"""
        try:
            # Set professional matplotlib styling
            plt.style.use("default")
            plt.rcParams.update(
                {
                    "font.family": ["Arial", "Helvetica", "sans-serif"],
                    "font.size": 12,
                    "axes.titlesize": 18,
                    "axes.labelsize": 14,
                    "xtick.labelsize": 11,
                    "ytick.labelsize": 11,
                    "legend.fontsize": 12,
                    "axes.spines.top": False,
                    "axes.spines.right": False,
                    "axes.grid": True,
                    "grid.alpha": 0.3,
                }
            )

            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor("white")

            # Daily returns
            if (
                "daily_returns" in self.metrics
                and self.metrics["daily_returns"] is not None
                and len(self.metrics["daily_returns"]) > 0
            ):
                daily_returns_data = self.metrics["daily_returns"]
                if hasattr(daily_returns_data, "keys") and hasattr(daily_returns_data, "values"):
                    dates = pd.to_datetime(list(daily_returns_data.keys()))
                    returns = [float(r) * 100 for r in daily_returns_data.values]
                else:
                    dates = (
                        pd.to_datetime(list(daily_returns_data.index))
                        if hasattr(daily_returns_data, "index")
                        else []
                    )
                    returns = [float(r) * 100 for r in daily_returns_data] if len(dates) > 0 else []

                ax.plot(dates, returns, linewidth=1, color=Colors.CHART_NAVY, alpha=0.8)
                ax.axhline(y=0, color=Colors.CHART_CHARCOAL, linestyle="--", alpha=0.5)
                ax.set_ylabel("Return (%)", color=Colors.CHART_CHARCOAL, fontsize=14)
                ax.set_xlabel("Date", color=Colors.CHART_CHARCOAL, fontsize=14)
                ax.tick_params(colors=Colors.CHART_CHARCOAL)
                ax.grid(True, alpha=0.3, color=Colors.CHART_MEDIUM_GRAY)
                ax.set_facecolor(Colors.CHART_LIGHT_GRAY)

                # Date formatting
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=self.interval))
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
            else:
                ax.text(
                    0.5,
                    0.5,
                    "No daily returns data available",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=16,
                    color=Colors.CHART_CHARCOAL,
                )

            ax.set_title(
                "Daily Returns (%)",
                fontsize=20,
                fontweight="bold",
                color=Colors.CHART_DEEP_BLUE,
                pad=25,
            )

            plt.tight_layout()

            buffer = BytesIO()
            fig.savefig(
                buffer,
                format="png",
                dpi=300,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
            buffer.seek(0)
            plt.close()

            return buffer
        except Exception as e:
            plt.close()
            return Paragraph(f"Error creating daily returns chart: {str(e)}", self.normal_style)

    def create_monthly_returns_chart(self):
        """Create monthly returns chart with professional styling"""
        try:
            # Set professional matplotlib styling
            plt.style.use("default")
            plt.rcParams.update(
                {
                    "font.family": ["Arial", "Helvetica", "sans-serif"],
                    "font.size": 12,
                    "axes.titlesize": 18,
                    "axes.labelsize": 14,
                    "xtick.labelsize": 11,
                    "ytick.labelsize": 11,
                    "legend.fontsize": 12,
                    "axes.spines.top": False,
                    "axes.spines.right": False,
                    "axes.grid": True,
                    "grid.alpha": 0.3,
                }
            )

            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor("white")

            # Monthly returns
            if (
                "monthly_returns" in self.metrics
                and self.metrics["monthly_returns"] is not None
                and len(self.metrics["monthly_returns"]) > 0
            ):
                monthly_returns_data = self.metrics["monthly_returns"]
                if hasattr(monthly_returns_data, "keys") and hasattr(
                    monthly_returns_data, "values"
                ):
                    dates = pd.to_datetime(list(monthly_returns_data.keys()))
                    returns = [float(r) * 100 for r in monthly_returns_data.values]
                else:
                    dates = (
                        pd.to_datetime(list(monthly_returns_data.index))
                        if hasattr(monthly_returns_data, "index")
                        else []
                    )
                    returns = (
                        [float(r) * 100 for r in monthly_returns_data] if len(dates) > 0 else []
                    )

                ax.plot(
                    dates,
                    returns,
                    linewidth=1,
                    color=Colors.CHART_GREEN,
                )
                ax.axhline(y=0, color=Colors.CHART_CHARCOAL, linestyle="--", alpha=0.5)
                ax.set_ylabel("Return (%)", color=Colors.CHART_CHARCOAL, fontsize=14)
                ax.set_xlabel("Date", color=Colors.CHART_CHARCOAL, fontsize=14)
                ax.tick_params(colors=Colors.CHART_CHARCOAL)
                ax.grid(True, alpha=0.3, color=Colors.CHART_MEDIUM_GRAY)
                ax.set_facecolor(Colors.CHART_LIGHT_GRAY)

                # Date formatting
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=self.interval))
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
            else:
                ax.text(
                    0.5,
                    0.5,
                    "No monthly returns data available",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=16,
                    color=Colors.CHART_CHARCOAL,
                )

            ax.set_title(
                "Monthly Returns (%)",
                fontsize=20,
                fontweight="bold",
                color=Colors.CHART_DEEP_BLUE,
                pad=25,
            )

            plt.tight_layout()

            buffer = BytesIO()
            fig.savefig(
                buffer,
                format="png",
                dpi=300,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
            buffer.seek(0)
            plt.close()

            return buffer
        except Exception as e:
            plt.close()
            return Paragraph(f"Error creating monthly returns chart: {str(e)}", self.normal_style)

    def create_quarterly_returns_chart(self):
        """Create quarterly returns chart with professional styling"""
        try:
            # Set professional matplotlib styling
            plt.style.use("default")
            plt.rcParams.update(
                {
                    "font.family": ["Arial", "Helvetica", "sans-serif"],
                    "font.size": 12,
                    "axes.titlesize": 18,
                    "axes.labelsize": 14,
                    "xtick.labelsize": 11,
                    "ytick.labelsize": 11,
                    "legend.fontsize": 12,
                    "axes.spines.top": False,
                    "axes.spines.right": False,
                    "axes.grid": True,
                    "grid.alpha": 0.3,
                }
            )

            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor("white")

            # Quarterly returns
            if (
                "quarterly_returns" in self.metrics
                and self.metrics["quarterly_returns"] is not None
                and len(self.metrics["quarterly_returns"]) > 0
            ):
                quarterly_returns_data = self.metrics["quarterly_returns"]
                if hasattr(quarterly_returns_data, "keys") and hasattr(
                    quarterly_returns_data, "values"
                ):
                    dates = pd.to_datetime(list(quarterly_returns_data.keys()))
                    returns = [float(r) * 100 for r in quarterly_returns_data.values]
                else:
                    dates = pd.to_datetime(list(quarterly_returns_data.index))
                    returns = (
                        [float(r) * 100 for r in quarterly_returns_data] if len(dates) > 0 else []
                    )

                ax.plot(
                    dates,
                    returns,
                    linewidth=1,
                    color=Colors.CHART_GOLD,
                )
                ax.axhline(y=0, color=Colors.CHART_CHARCOAL, linestyle="--", alpha=0.5)
                ax.set_ylabel("Return (%)", color=Colors.CHART_CHARCOAL, fontsize=14)
                ax.set_xlabel("Date", color=Colors.CHART_CHARCOAL, fontsize=14)
                ax.tick_params(colors=Colors.CHART_CHARCOAL)
                ax.grid(True, alpha=0.3, color=Colors.CHART_MEDIUM_GRAY)
                ax.set_facecolor(Colors.CHART_LIGHT_GRAY)

                # Date formatting
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=self.interval))
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
            else:
                ax.text(
                    0.5,
                    0.5,
                    "No quarterly returns data available",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=16,
                    color=Colors.CHART_CHARCOAL,
                )

            ax.set_title(
                "Quarterly Returns (%)",
                fontsize=20,
                fontweight="bold",
                color=Colors.CHART_DEEP_BLUE,
                pad=25,
            )

            plt.tight_layout()

            buffer = BytesIO()
            fig.savefig(
                buffer,
                format="png",
                dpi=300,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
            buffer.seek(0)
            plt.close()

            return buffer
        except Exception as e:
            plt.close()
            return Paragraph(f"Error creating quarterly returns chart: {str(e)}", self.normal_style)

    def create_annual_returns_chart(self):
        """Create annual returns chart with professional styling"""
        try:
            # Set professional matplotlib styling
            plt.style.use("default")
            plt.rcParams.update(
                {
                    "font.family": ["Arial", "Helvetica", "sans-serif"],
                    "font.size": 12,
                    "axes.titlesize": 18,
                    "axes.labelsize": 14,
                    "xtick.labelsize": 11,
                    "ytick.labelsize": 11,
                    "legend.fontsize": 12,
                    "axes.spines.top": False,
                    "axes.spines.right": False,
                    "axes.grid": True,
                    "grid.alpha": 0.3,
                }
            )

            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor("white")

            # Annual returns
            if (
                "annual_returns" in self.metrics
                and self.metrics["annual_returns"] is not None
                and len(self.metrics["annual_returns"]) > 0
            ):
                annual_returns_data = self.metrics["annual_returns"]
                if hasattr(annual_returns_data, "keys") and hasattr(annual_returns_data, "values"):
                    years = list(annual_returns_data.keys())
                    returns = [float(r) * 100 for r in annual_returns_data.values]
                else:
                    years = (
                        list(annual_returns_data.index)
                        if hasattr(annual_returns_data, "index")
                        else []
                    )
                    returns = (
                        [float(r) * 100 for r in annual_returns_data] if len(years) > 0 else []
                    )

                ax.plot(
                    years,
                    returns,
                    linewidth=1,
                    color=Colors.CHART_RED,
                    marker="o",
                    markersize=8,
                )
                ax.axhline(y=0, color=Colors.CHART_CHARCOAL, linestyle="--", alpha=0.5)
                ax.set_ylabel("Return (%)", color=Colors.CHART_CHARCOAL, fontsize=14)
                ax.set_xlabel("Year", color=Colors.CHART_CHARCOAL, fontsize=14)
                ax.tick_params(colors=Colors.CHART_CHARCOAL)
                ax.grid(True, alpha=0.3, color=Colors.CHART_MEDIUM_GRAY)
                ax.set_facecolor(Colors.CHART_LIGHT_GRAY)
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
            else:
                ax.text(
                    0.5,
                    0.5,
                    "No annual returns data available",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=16,
                    color=Colors.CHART_CHARCOAL,
                )

            ax.set_title(
                "Annual Returns (%)",
                fontsize=20,
                fontweight="bold",
                color=Colors.CHART_DEEP_BLUE,
                pad=25,
            )

            plt.tight_layout()

            buffer = BytesIO()
            fig.savefig(
                buffer,
                format="png",
                dpi=300,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
            buffer.seek(0)
            plt.close()

            return buffer
        except Exception as e:
            plt.close()
            return Paragraph(f"Error creating annual returns chart: {str(e)}", self.normal_style)

    def create_daily_return_distribution_chart(self):
        """Create daily return distribution analysis with professional styling"""
        try:
            # Set professional matplotlib styling
            plt.style.use("default")
            plt.rcParams.update(
                {
                    "font.family": ["Arial", "Helvetica", "sans-serif"],
                    "font.size": 12,
                    "axes.titlesize": 18,
                    "axes.labelsize": 14,
                    "xtick.labelsize": 11,
                    "ytick.labelsize": 11,
                    "legend.fontsize": 12,
                    "axes.spines.top": False,
                    "axes.spines.right": False,
                    "axes.grid": True,
                    "grid.alpha": 0.3,
                }
            )

            fig, ax = plt.subplots(figsize=(12, 7))
            fig.patch.set_facecolor("white")

            # Daily return distribution
            if (
                "daily_returns" in self.metrics
                and self.metrics["daily_returns"] is not None
                and len(self.metrics["daily_returns"]) > 0
            ):
                daily_returns_data = self.metrics["daily_returns"]
                if hasattr(daily_returns_data, "values"):
                    returns = [float(r) * 100 for r in daily_returns_data.values]
                else:
                    returns = [float(r) * 100 for r in daily_returns_data]

                ax.hist(
                    returns,
                    bins=50,
                    alpha=0.7,
                    color=Colors.CHART_NAVY,
                    edgecolor=Colors.CHART_CHARCOAL,
                    linewidth=0.5,
                )
                ax.axvline(
                    np.mean(returns),
                    color=Colors.CHART_RED,
                    linestyle="--",
                    linewidth=3,
                    label=f"Mean: {np.mean(returns):.2f}%",
                )
                ax.axvline(
                    np.median(returns),
                    color=Colors.CHART_GOLD,
                    linestyle="--",
                    linewidth=3,
                    label=f"Median: {np.median(returns):.2f}%",
                )
                ax.set_xlabel("Daily Return (%)", fontsize=14, color=Colors.CHART_CHARCOAL)
                ax.set_ylabel("Frequency", fontsize=14, color=Colors.CHART_CHARCOAL)
                ax.tick_params(colors=Colors.CHART_CHARCOAL)
                ax.grid(True, alpha=0.3, color=Colors.CHART_MEDIUM_GRAY)
                ax.set_facecolor(Colors.CHART_LIGHT_GRAY)

                # Enhanced legend
                legend = ax.legend(
                    frameon=True,
                    fancybox=True,
                    shadow=True,
                    facecolor=Colors.CHART_WHITE,
                    edgecolor=Colors.CHART_BLUE,
                )
                legend.get_frame().set_alpha(0.9)

                # Add statistics text with better styling
                stats_text = f"Std Dev: {np.std(returns):.2f}%\nSkewness: {pd.Series(returns).skew():.2f}\nKurtosis: {pd.Series(returns).kurtosis():.2f}"
                ax.text(
                    0.02,
                    0.98,
                    stats_text,
                    transform=ax.transAxes,
                    fontsize=12,
                    verticalalignment="top",
                    bbox=dict(
                        boxstyle="round,pad=0.5",
                        facecolor=Colors.CHART_WHITE,
                        alpha=0.9,
                        edgecolor=Colors.CHART_BLUE,
                    ),
                )
            else:
                ax.text(
                    0.5,
                    0.5,
                    "No daily returns data available",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=16,
                    color=Colors.CHART_CHARCOAL,
                )

            ax.set_title(
                "Daily Return Distribution",
                fontsize=20,
                fontweight="bold",
                color=Colors.CHART_DEEP_BLUE,
                pad=25,
            )

            plt.tight_layout()

            buffer = BytesIO()
            fig.savefig(
                buffer,
                format="png",
                dpi=300,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
            buffer.seek(0)
            plt.close()

            return buffer
        except Exception as e:
            plt.close()
            return Paragraph(
                f"Error creating daily return distribution chart: {str(e)}", self.normal_style
            )

    def create_monthly_return_distribution_chart(self):
        """Create monthly return distribution analysis with professional styling"""
        try:
            # Set professional matplotlib styling
            plt.style.use("default")
            plt.rcParams.update(
                {
                    "font.family": ["Arial", "Helvetica", "sans-serif"],
                    "font.size": 12,
                    "axes.titlesize": 18,
                    "axes.labelsize": 14,
                    "xtick.labelsize": 11,
                    "ytick.labelsize": 11,
                    "legend.fontsize": 12,
                    "axes.spines.top": False,
                    "axes.spines.right": False,
                    "axes.grid": True,
                    "grid.alpha": 0.3,
                }
            )

            fig, ax = plt.subplots(figsize=(12, 7))
            fig.patch.set_facecolor("white")

            # Monthly return distribution
            if (
                "monthly_returns" in self.metrics
                and self.metrics["monthly_returns"] is not None
                and len(self.metrics["monthly_returns"]) > 0
            ):
                monthly_returns_data = self.metrics["monthly_returns"]
                if hasattr(monthly_returns_data, "values"):
                    returns = [float(r) * 100 for r in monthly_returns_data.values]
                else:
                    returns = [float(r) * 100 for r in monthly_returns_data]

                ax.hist(
                    returns,
                    bins=20,
                    alpha=0.7,
                    color=Colors.CHART_GOLD,
                    edgecolor=Colors.CHART_CHARCOAL,
                    linewidth=0.5,
                )
                ax.axvline(
                    np.mean(returns),
                    color=Colors.CHART_RED,
                    linestyle="--",
                    linewidth=3,
                    label=f"Mean: {np.mean(returns):.2f}%",
                )
                ax.axvline(
                    np.median(returns),
                    color=Colors.CHART_DEEP_BLUE,
                    linestyle="--",
                    linewidth=3,
                    label=f"Median: {np.median(returns):.2f}%",
                )
                ax.set_xlabel("Monthly Return (%)", fontsize=14, color=Colors.CHART_CHARCOAL)
                ax.set_ylabel("Frequency", fontsize=14, color=Colors.CHART_CHARCOAL)
                ax.tick_params(colors=Colors.CHART_CHARCOAL)
                ax.grid(True, alpha=0.3, color=Colors.CHART_MEDIUM_GRAY)
                ax.set_facecolor(Colors.CHART_LIGHT_GRAY)

                # Enhanced legend
                legend = ax.legend(
                    frameon=True,
                    fancybox=True,
                    shadow=True,
                    facecolor=Colors.CHART_WHITE,
                    edgecolor=Colors.CHART_BLUE,
                )
                legend.get_frame().set_alpha(0.9)

                # Add statistics text with better styling
                stats_text = f"Std Dev: {np.std(returns):.2f}%\nSkewness: {pd.Series(returns).skew():.2f}\nKurtosis: {pd.Series(returns).kurtosis():.2f}"
                ax.text(
                    0.02,
                    0.98,
                    stats_text,
                    transform=ax.transAxes,
                    fontsize=12,
                    verticalalignment="top",
                    bbox=dict(
                        boxstyle="round,pad=0.5",
                        facecolor=Colors.CHART_WHITE,
                        alpha=0.9,
                        edgecolor=Colors.CHART_BLUE,
                    ),
                )
            else:
                ax.text(
                    0.5,
                    0.5,
                    "No monthly returns data available",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=16,
                    color=Colors.CHART_CHARCOAL,
                )

            ax.set_title(
                "Monthly Return Distribution",
                fontsize=20,
                fontweight="bold",
                color=Colors.CHART_DEEP_BLUE,
                pad=25,
            )

            plt.tight_layout()

            buffer = BytesIO()
            fig.savefig(
                buffer,
                format="png",
                dpi=300,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
            buffer.seek(0)
            plt.close()

            return buffer
        except Exception as e:
            plt.close()
            return Paragraph(
                f"Error creating monthly return distribution chart: {str(e)}", self.normal_style
            )

    def create_sector_exposure_chart(self):
        """Create multiline plot showing sector percentage over time with professional styling"""
        # Set professional matplotlib styling
        plt.style.use("default")
        plt.rcParams.update(
            {
                "font.family": ["Arial", "Helvetica", "sans-serif"],
                "font.size": 12,
                "axes.titlesize": 18,
                "axes.labelsize": 14,
                "xtick.labelsize": 11,
                "ytick.labelsize": 11,
                "legend.fontsize": 11,
                "axes.spines.top": False,
                "axes.spines.right": False,
                "axes.grid": True,
                "grid.alpha": 0.3,
            }
        )

        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor("white")

        if self.holdings_summary["sector_ts"] and self.holdings_summary["holdings_count"]:
            # Create dataframe from sector time series
            holdings_dates = list(self.holdings_summary["holdings_count"].keys())
            sector_df = pd.DataFrame(self.holdings_summary["sector_ts"])
            sector_df.index = pd.to_datetime(holdings_dates)
            sector_df = sector_df.sort_index()

            sector_pct_df = sector_df.div(sector_df[sector_df.columns].sum(axis=1), axis=0) * 100
            sector_pct_df = sector_pct_df.fillna(0)

            professional_colors = [
                Colors.CHART_NAVY,
                Colors.CHART_GOLD,
                Colors.CHART_BLUE,
                Colors.CHART_GREEN,
                Colors.CHART_RED,
                Colors.CHART_AMBER,
                Colors.CHART_TEAL,
                Colors.CHART_DEEP_BLUE,
                Colors.CHART_CHARCOAL,
                Colors.CHART_DARK_GRAY,
                "#8E44AD",
                "#E67E22",
            ]

            # Plot each sector as a line
            for i, sector in enumerate(sector_pct_df.columns):
                color = professional_colors[i % len(professional_colors)]
                ax.plot(
                    sector_pct_df.index,
                    sector_pct_df[sector],
                    linewidth=1,
                    label=sector,
                    color=color,
                )

            ax.set_title(
                "Sector Exposure Over Time (%)",
                fontsize=20,
                fontweight="bold",
                color=Colors.CHART_DEEP_BLUE,
                pad=25,
            )
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=self.interval))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
            ax.set_ylabel("Percentage of Portfolio (%)", fontsize=14, color=Colors.CHART_CHARCOAL)
            ax.set_xlabel("Date", fontsize=14, color=Colors.CHART_CHARCOAL)

            # Professional styling
            ax.tick_params(colors=Colors.CHART_CHARCOAL)
            ax.grid(True, alpha=0.3, color=Colors.CHART_MEDIUM_GRAY)
            ax.set_facecolor(Colors.CHART_LIGHT_GRAY)

            # Legend styling - place on top
            legend = ax.legend(
                bbox_to_anchor=(0.5, 1.02),
                loc="lower center",
                ncol=3,
                frameon=True,
                fancybox=True,
                shadow=True,
                facecolor=Colors.CHART_WHITE,
                edgecolor=Colors.CHART_BLUE,
            )
            legend.get_frame().set_alpha(0.95)

            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
        else:
            ax.text(
                0.5,
                0.5,
                "No sector data available",
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=16,
                color=Colors.CHART_CHARCOAL,
            )
            ax.set_title(
                "Sector Exposure Over Time (%)",
                fontsize=20,
                fontweight="bold",
                color=Colors.CHART_DEEP_BLUE,
                pad=25,
            )

        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(
            buf, format="png", dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none"
        )
        buf.seek(0)
        plt.close()

        return buf

    def create_sector_composition_pie(self):
        """Create pie chart of average sector composition with legend"""
        plt.style.use("default")
        plt.rcParams.update(
            {
                "font.family": ["Arial", "Helvetica", "sans-serif"],
                "font.size": 11,
            }
        )
        fig, ax = plt.subplots(figsize=(10, 7))

        if self.holdings_summary["sector_ts"]:
            # Calculate average sector composition
            sector_df = pd.DataFrame(self.holdings_summary["sector_ts"])
            avg_sector = sector_df.mean()
            avg_sector = avg_sector[avg_sector > 0]  # Only non-zero sectors

            if len(avg_sector) > 0:
                # Use Goldman Sachs inspired colors for pie chart
                gs_colors = [
                    Colors.CHART_NAVY,
                    Colors.CHART_GOLD,
                    Colors.CHART_BLUE,
                    Colors.CHART_GREEN,
                    Colors.CHART_RED,
                    Colors.CHART_AMBER,
                    Colors.CHART_TEAL,
                    Colors.CHART_CHARCOAL,
                    Colors.CHART_DARK_GRAY,
                ]
                # Cycle through colors if we have more sectors than colors
                colors_list = [gs_colors[i % len(gs_colors)] for i in range(len(avg_sector))]

                wedges, texts, autotexts = ax.pie(
                    avg_sector.values,
                    autopct="%1.1f%%",
                    colors=colors_list,
                    startangle=90,
                    pctdistance=0.85,
                )

                # Style the percentage text
                for autotext in autotexts:
                    autotext.set_color("white")
                    autotext.set_fontweight("bold")
                    autotext.set_fontsize(11)
                    autotext.set_family("Arial")

                # Create legend with sector names
                ax.legend(
                    wedges,
                    avg_sector.index,
                    title="Sectors",
                    loc="center left",
                    bbox_to_anchor=(1, 0, 0.5, 1),
                    fontsize=11,
                    title_fontsize=12,
                    frameon=True,
                    fancybox=True,
                    shadow=True,
                    facecolor=Colors.CHART_WHITE,
                    edgecolor=Colors.CHART_BLUE,
                )

                ax.set_title(
                    "Average Sector Composition",
                    fontsize=16,
                    fontweight="bold",
                    color=Colors.CHART_DEEP_BLUE,
                    pad=20,
                    family="Arial",
                )
            else:
                ax.text(
                    0.5,
                    0.5,
                    "No sector data available",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                )
                ax.set_title("Average Sector Composition", fontsize=14, fontweight="bold")
        else:
            ax.text(
                0.5,
                0.5,
                "No sector data available",
                transform=ax.transAxes,
                ha="center",
                va="center",
            )
            ax.set_title("Average Sector Composition", fontsize=14, fontweight="bold")

        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        buf.seek(0)
        plt.close()

        return buf

    def create_sector_duration_boxplot(self):
        """Create box plot showing duration distribution by sector"""
        plt.style.use("default")
        fig, ax = plt.subplots(figsize=(10, 6))

        if self.holdings_summary["duration_by_ticker"] and self.holdings_summary["sector_ts"]:

            # Get duration data
            duration_df = pd.DataFrame(self.holdings_summary["duration_by_ticker"])
            duration_df = duration_df.merge(self.portfolio.product_data, on="ticker", how="left")

            if len(duration_df) > 0:
                # Create box plot
                sectors = duration_df["sector"].unique()
                sector_data = [
                    duration_df[duration_df["sector"] == sector]["duration"] for sector in sectors
                ]

                box_plot = ax.boxplot(sector_data, labels=sectors, patch_artist=True)

                # Color the boxes
                colors = plt.cm.Set3(np.linspace(0, 1, len(sectors)))
                for patch, color in zip(box_plot["boxes"], colors):
                    patch.set_facecolor(color)
                    patch.set_alpha(0.7)

                ax.set_title(
                    "Holding Duration Distribution by Sector", fontsize=14, fontweight="bold"
                )
                ax.set_xlabel("Sector", fontsize=12)
                ax.set_ylabel("Duration (Days)", fontsize=12)
                ax.grid(True, alpha=0.3)
                plt.xticks(rotation=45, ha="right")
            else:
                ax.text(
                    0.5,
                    0.5,
                    "No sector-duration mapping available",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                )
                ax.set_title(
                    "Holding Duration Distribution by Sector", fontsize=14, fontweight="bold"
                )
        else:
            ax.text(
                0.5,
                0.5,
                "No duration or sector data available",
                transform=ax.transAxes,
                ha="center",
                va="center",
            )
            ax.set_title("Holding Duration Distribution by Sector", fontsize=14, fontweight="bold")

        plt.tight_layout()

        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        buf.seek(0)
        plt.close()

        return buf

    def create_trading_metrics_table(self):
        trades_df = pd.DataFrame(self.holdings_summary["trades_ts"])
        trades_df["total"] = trades_df.sum(axis=1)
        trades_df[["buy_pct", "sell_pct"]] = trades_df[["buy", "sell"]].div(
            trades_df["total"], axis=0
        )
        trades_df.fillna(0, inplace=True)

        count = Counter(self.portfolio.trades_status.values())
        executed = count.get(1, 0)
        cancelled = count.get(0, 0)
        total_trading_days = executed + cancelled

        trading_data = [
            ["Trading Metric", "Value"],
            ["Total Trading Days", f"{total_trading_days}"],
            ["Avg. Buy Trades per day", f"{trades_df['buy'].mean():.1f}"],
            ["Avg. Sell Trades per day", f"{trades_df['sell'].mean():.1f}"],
            [
                "Trade Execution Rate",
                f"{executed / total_trading_days if total_trading_days > 0 else 0:.2%}",
            ],
            ["Cancelled Trades", f"{cancelled}"],
        ]

        table = Table(trading_data, colWidths=[3.5 * inch, 2.5 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), Colors.GOLD),
                    ("TEXTCOLOR", (0, 0), (-1, 0), Colors.WHITE),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("FONTSIZE", (0, 1), (-1, -1), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), Colors.LIGHT_GRAY),
                    ("LINEBELOW", (0, 0), (-1, -1), 1, Colors.MEDIUM_GRAY),
                    ("BOX", (0, 0), (-1, -1), 1.5, Colors.GOLD),
                ]
            )
        )

        return table

    def create_trading_activity_chart(self):
        """Create trading activity bar chart with buy/sell bars and second chart with total/net trades lines"""
        plt.style.use("default")
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(10, 7.5), gridspec_kw={"height_ratios": [2, 1]}, sharex=True
        )

        if self.holdings_summary["trades_ts"] and self.holdings_summary["holdings_count"]:
            holdings_dates = list(self.holdings_summary["holdings_count"].keys())
            trades_df = pd.DataFrame(self.holdings_summary["trades_ts"])
            trades_df["Date"] = pd.to_datetime(holdings_dates)
            trades_df = trades_df.sort_values("Date")

            trades_df["buy"] = pd.to_numeric(trades_df["buy"], errors="coerce").fillna(0)
            trades_df["sell"] = pd.to_numeric(trades_df["sell"], errors="coerce").fillna(0)
            trades_df["net_trades"] = trades_df["buy"] - trades_df["sell"]
            trades_df["total_trades"] = trades_df["buy"] + trades_df["sell"]

            # Main chart - Buy/Sell bars only
            bar_width = 0.8
            ax1.bar(
                trades_df["Date"],
                trades_df["buy"],
                alpha=0.7,
                label="Buy Trades",
                color="green",
                width=bar_width,
            )
            ax1.bar(
                trades_df["Date"],
                -trades_df["sell"],
                alpha=0.7,
                label="Sell Trades",
                color="red",
                width=bar_width,
            )

            ax1.set_title("Trading Activity Over Time", fontsize=14, fontweight="bold")
            ax1.set_ylabel("Number of Trades (Buy +, Sell -)")
            ax1.grid(True, alpha=0.3)
            ax1.axhline(y=0, color="black", linestyle="-", alpha=0.5)
            ax1.legend(loc="upper left")

            # Bottom chart - Total trades and net trades as lines
            ax2.plot(
                trades_df["Date"],
                trades_df["total_trades"],
                color=Colors.CHART_NAVY,
                linewidth=1,
                label="Total Trades",
                alpha=0.8,
            )
            ax2.plot(
                trades_df["Date"],
                trades_df["net_trades"],
                color=Colors.CHART_GREEN,
                linewidth=1,
                label="Net Trades (Buy - Sell)",
                alpha=0.8,
            )

            ax2.set_ylabel("Number of Trades")
            ax2.set_xlabel("Date")
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
            ax1.set_title("Trading Activity Over Time", fontsize=14, fontweight="bold")
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
        fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        buf.seek(0)
        plt.close()

        return buf

    def create_top_tickers_tables(self):
        """Create tables for top bought, sold, and traded tickers"""
        if not self.holdings_summary["trades_by_ticker"]:
            return None, None, None

        trades_df = pd.DataFrame(self.holdings_summary["trades_by_ticker"])
        trades_df["total_trades"] = trades_df["buy"] + trades_df["sell"]

        # Top 5 most bought
        top_bought = trades_df.nlargest(5, "buy")[["ticker", "buy"]]
        bought_data = [["Ticker", "Buy Trades"]]
        for _, row in top_bought.iterrows():
            bought_data.append([str(row["ticker"]), str(row["buy"])])

        bought_table = Table(bought_data, colWidths=[1.8 * inch, 1.8 * inch])
        bought_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), Colors.EMERALD),
                    ("TEXTCOLOR", (0, 0), (-1, 0), Colors.WHITE),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("FONTSIZE", (0, 1), (-1, -1), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), Colors.LIGHT_GRAY),
                    ("LINEBELOW", (0, 0), (-1, -1), 1, Colors.MEDIUM_GRAY),
                    ("BOX", (0, 0), (-1, -1), 1.5, Colors.EMERALD),
                ]
            )
        )

        # Top 5 most sold
        top_sold = trades_df.nlargest(5, "sell")[["ticker", "sell"]]
        sold_data = [["Ticker", "Sell Trades"]]
        for _, row in top_sold.iterrows():
            sold_data.append([str(row["ticker"]), str(row["sell"])])

        sold_table = Table(sold_data, colWidths=[1.8 * inch, 1.8 * inch])
        sold_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), Colors.GOLD),
                    ("TEXTCOLOR", (0, 0), (-1, 0), Colors.WHITE),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("FONTSIZE", (0, 1), (-1, -1), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), Colors.LIGHT_GRAY),
                    ("LINEBELOW", (0, 0), (-1, -1), 1, Colors.MEDIUM_GRAY),
                    ("BOX", (0, 0), (-1, -1), 1.5, Colors.GOLD),
                ]
            )
        )

        # Top 5 most traded (total)
        top_traded = trades_df.nlargest(5, "total_trades")[["ticker", "total_trades"]]
        traded_data = [["Ticker", "Total Trades"]]
        for _, row in top_traded.iterrows():
            traded_data.append([str(row["ticker"]), str(row["total_trades"])])

        traded_table = Table(traded_data, colWidths=[1.8 * inch, 1.8 * inch])
        traded_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), Colors.NAVY_BLUE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), Colors.WHITE),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("FONTSIZE", (0, 1), (-1, -1), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), Colors.LIGHT_GRAY),
                    ("LINEBELOW", (0, 0), (-1, -1), 1, Colors.MEDIUM_GRAY),
                    ("BOX", (0, 0), (-1, -1), 1.5, Colors.NAVY_BLUE),
                ]
            )
        )

        return bought_table, sold_table, traded_table

    def add_page_header(self, story, section_name=None):
        """Add section header with divider line to each page"""
        if section_name:
            # Create header style for section names
            header_style = ParagraphStyle(
                "SectionPageHeader",
                parent=self.styles["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=14,
                spaceAfter=2,
                spaceBefore=0,
                textColor=Colors.NAVY_BLUE,
                alignment=TA_LEFT,
                leading=16,
            )
            story.append(Paragraph(section_name, header_style))

            # Add divider line using a table
            divider_table = Table([[""]], colWidths=[landscape(A4)[0] - 1.5 * inch])
            divider_table.setStyle(
                TableStyle(
                    [
                        ("LINEBELOW", (0, 0), (-1, -1), 1.5, Colors.NAVY_BLUE),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            story.append(divider_table)
            story.append(Spacer(1, 10))

    def generate_report(self, filename=None):
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
            canvas.saveState()

            # Draw footer divider line
            canvas.setStrokeColor(Colors.MEDIUM_GRAY)
            canvas.setLineWidth(0.5)
            canvas.line(0.75 * inch, 0.7 * inch, landscape(A4)[0] - 0.75 * inch, 0.7 * inch)

            # Add portfolio info in footer
            portfolio_dates = list(self.portfolio.portfolio_value_history.keys())
            start_date = min(portfolio_dates) if portfolio_dates else "N/A"
            end_date = max(portfolio_dates) if portfolio_dates else "N/A"

            portfolio_name = self.portfolio.name or "Unnamed Portfolio"
            benchmark = (
                self.portfolio.benchmark.value
                if hasattr(self.portfolio.benchmark, "value")
                else str(self.portfolio.benchmark)
            )
            run_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            period = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"

            footer_text = f"{portfolio_name} | Benchmark: {benchmark} | Run Date: {run_date} | Period: {period}"

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
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        frame = Frame(
            0.75 * inch,
            0.75 * inch,
            landscape(A4)[0] - 1.5 * inch,
            landscape(A4)[1] - 1.5 * inch,
            id="normal",
        )

        template = PageTemplate(id="normal", frames=frame, onPage=add_page_number)
        doc.addPageTemplates([template])

        story = []

        # TITLE PAGE
        # Page 1: Title Page with centered portfolio information
        title_page_content = self.create_title_page()
        story.extend(title_page_content)
        story.append(PageBreak())

        # PORTFOLIO OVERVIEW SECTION
        # Page 2: Portfolio Configuration and Performance Tables (no header)

        # Create side-by-side tables with titles and proper margins
        config_content = self.create_portfolio_config_block()
        performance_content = self.create_key_performance_block()

        # Create table containers for side-by-side layout
        config_container = Table([[content] for content in config_content], colWidths=[3.8 * inch])
        config_container.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))

        performance_container = Table(
            [[content] for content in performance_content], colWidths=[3.8 * inch]
        )
        performance_container.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))

        # Combine containers side by side with more space between and less edge margin
        # Add spacer between tables for better separation
        spacer_cell = Table([[Spacer(1, 1)]], colWidths=[0.8 * inch])
        tables_data = [[config_container, spacer_cell, performance_container]]
        combined_table = Table(tables_data, colWidths=[3.8 * inch, 0.8 * inch, 3.8 * inch])
        combined_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),  # Less margin from page edge
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),  # Less margin from page edge
                ]
            )
        )
        story.append(Spacer(1, 0.5 * inch))  # Add top margin
        story.append(combined_table)

        # Page 3: Portfolio Value Over Time
        story.append(PageBreak())
        self.add_page_header(story, section_name="Portfolio Analysis")
        portfolio_value_chart = self.create_portfolio_value_chart()

        # Handle both successful chart generation (BytesIO) and error cases (Paragraph)
        if portfolio_value_chart:
            if isinstance(portfolio_value_chart, BytesIO):
                # Successful chart generation
                story.append(Image(portfolio_value_chart, width=8.5 * inch, height=5 * inch))
            else:
                # Error case - chart method returned a Paragraph with error message
                story.append(portfolio_value_chart)
        else:
            # Fallback content if chart is None
            story.append(Paragraph("Portfolio value chart data not available", self.normal_style))

        # RETURN ANALYSIS SECTION TITLE PAGE
        story.append(PageBreak())
        return_analysis_title = self.create_section_title_page("Return Analysis")
        story.extend(return_analysis_title)

        # RETURN ANALYSIS SECTION
        # Page 4: Return Analysis - Daily Returns
        story.append(PageBreak())
        self.add_page_header(story, section_name="Return Analysis")
        daily_returns_chart = self.create_daily_returns_chart()
        if daily_returns_chart:
            if isinstance(daily_returns_chart, BytesIO):
                story.append(Image(daily_returns_chart, width=8.5 * inch, height=5 * inch))
            else:
                story.append(daily_returns_chart)

        # Page 5: Return Analysis - Monthly Returns
        story.append(PageBreak())
        self.add_page_header(story, section_name="Return Analysis")
        monthly_returns_chart = self.create_monthly_returns_chart()
        if monthly_returns_chart:
            if isinstance(monthly_returns_chart, BytesIO):
                story.append(Image(monthly_returns_chart, width=8.5 * inch, height=5 * inch))
            else:
                story.append(monthly_returns_chart)

        # Page 6: Return Analysis - Quarterly Returns
        story.append(PageBreak())
        self.add_page_header(story, section_name="Return Analysis")
        quarterly_returns_chart = self.create_quarterly_returns_chart()
        if quarterly_returns_chart:
            if isinstance(quarterly_returns_chart, BytesIO):
                story.append(Image(quarterly_returns_chart, width=8.5 * inch, height=5 * inch))
            else:
                story.append(quarterly_returns_chart)

        # Page 7: Return Analysis - Annual Returns
        story.append(PageBreak())
        self.add_page_header(story, section_name="Return Analysis")
        annual_returns_chart = self.create_annual_returns_chart()
        if annual_returns_chart:
            if isinstance(annual_returns_chart, BytesIO):
                story.append(Image(annual_returns_chart, width=8.5 * inch, height=5 * inch))
            else:
                story.append(annual_returns_chart)

        # Page 8: Return Analysis - Daily Return Distribution
        story.append(PageBreak())
        self.add_page_header(story, section_name="Return Analysis")
        daily_distribution_chart = self.create_daily_return_distribution_chart()
        if daily_distribution_chart:
            if isinstance(daily_distribution_chart, BytesIO):
                story.append(Image(daily_distribution_chart, width=8.5 * inch, height=5 * inch))
            else:
                story.append(daily_distribution_chart)

        # Page 9: Return Analysis - Monthly Return Distribution
        story.append(PageBreak())
        self.add_page_header(story, section_name="Return Analysis")
        monthly_distribution_chart = self.create_monthly_return_distribution_chart()
        if monthly_distribution_chart:
            if isinstance(monthly_distribution_chart, BytesIO):
                story.append(Image(monthly_distribution_chart, width=8.5 * inch, height=5 * inch))
            else:
                story.append(monthly_distribution_chart)

        # HOLDINGS ANALYSIS SECTION TITLE PAGE
        story.append(PageBreak())
        holdings_analysis_title = self.create_section_title_page("Holdings Analysis")
        story.extend(holdings_analysis_title)

        # HOLDINGS ANALYSIS SECTION
        # Page 10: Holdings Analysis - Holdings Summary
        story.append(PageBreak())
        self.add_page_header(story, section_name="Holdings Analysis")

        # Add table title
        table_title = Paragraph("Holdings Summary", self.section_header_style)
        story.append(table_title)
        story.append(Spacer(1, 5))

        holdings_table = self.create_holdings_summary_table()
        if holdings_table:
            story.append(holdings_table)

        # Page 11: Holdings Analysis - Holdings Over Time
        story.append(PageBreak())
        self.add_page_header(story, section_name="Holdings Analysis")
        holdings_chart = self.create_holdings_analysis_chart()
        story.append(Image(holdings_chart, width=8.5 * inch, height=5 * inch))

        # Page 12: Holdings Analysis - Duration Summary and Top Durations
        story.append(PageBreak())
        self.add_page_header(story, section_name="Holdings Analysis")

        # Add title for duration summary table
        duration_title = Paragraph("Duration Summary", self.section_header_style)
        story.append(duration_title)
        story.append(Spacer(1, 5))

        duration_summary_table = self.create_holding_duration_summary_table()
        if duration_summary_table:
            story.append(duration_summary_table)
            story.append(Spacer(1, 20))  # Add space between sections

        # Add top durations section on the same page
        story.append(
            Paragraph("Top 5 Longest Hold, Top 5 Shortest Hold", self.section_header_style)
        )
        story.append(Spacer(1, 10))
        longest_table, shortest_table = self.create_top_duration_tables()
        if longest_table and shortest_table:
            # Create titles for the duration tables
            longest_title = Paragraph("Top 5 Longest Hold", self.section_header_style)
            shortest_title = Paragraph("Top 5 Shortest Hold", self.section_header_style)

            # Create containers with titles and tables
            longest_container = Table(
                [[longest_title], [Spacer(1, 8)], [longest_table]], colWidths=[3.5 * inch]
            )
            longest_container.setStyle(
                TableStyle(
                    [("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]
                )
            )

            shortest_container = Table(
                [[shortest_title], [Spacer(1, 8)], [shortest_table]], colWidths=[3.5 * inch]
            )
            shortest_container.setStyle(
                TableStyle(
                    [("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]
                )
            )

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

        # Page 14: Holdings Analysis - Duration vs Sector
        story.append(PageBreak())
        self.add_page_header(story, section_name="Holdings Analysis")
        sector_duration_chart = self.create_sector_duration_boxplot()
        story.append(Image(sector_duration_chart, width=8.5 * inch, height=5 * inch))

        # SECTOR ANALYSIS SECTION TITLE PAGE
        story.append(PageBreak())
        sector_analysis_title = self.create_section_title_page("Sector Analysis")
        story.extend(sector_analysis_title)

        # SECTOR ANALYSIS SECTION
        # Page 15: Sector Analysis - Exposure Over Time
        story.append(PageBreak())
        self.add_page_header(story, section_name="Sector Analysis")
        sector_chart = self.create_sector_exposure_chart()
        story.append(Image(sector_chart, width=8.5 * inch, height=5 * inch))

        # Page 16: Sector Analysis - Average Sector Overtime
        story.append(PageBreak())
        self.add_page_header(story, section_name="Sector Analysis")
        pie_chart = self.create_sector_composition_pie()
        story.append(Image(pie_chart, width=7 * inch, height=5 * inch))

        # TRADING ANALYSIS SECTION TITLE PAGE
        story.append(PageBreak())
        trading_analysis_title = self.create_section_title_page("Trading Analysis")
        story.extend(trading_analysis_title)

        # TRADING ANALYSIS SECTION
        # Page 17: Trading Analysis - Trading Metrics
        story.append(PageBreak())
        self.add_page_header(story, section_name="Trading Analysis")

        # Add table title
        table_title = Paragraph("Trading Metrics", self.section_header_style)
        story.append(table_title)
        story.append(Spacer(1, 5))

        trading_table = self.create_trading_metrics_table()
        story.append(trading_table)

        # Page 18: Trading Analysis - Trading Over Time
        story.append(PageBreak())
        self.add_page_header(story, section_name="Trading Analysis")
        trading_chart = self.create_trading_activity_chart()
        story.append(Image(trading_chart, width=8.5 * inch, height=5 * inch))

        # Page 19: Trading Analysis - Top 5 Tables
        story.append(PageBreak())
        self.add_page_header(story, section_name="Trading Analysis")
        bought_table, sold_table, traded_table = self.create_top_tickers_tables()
        if bought_table and sold_table and traded_table:
            # Create titles for each table
            bought_title = Paragraph("Top 5 Most Bought Tickers", self.section_header_style)
            sold_title = Paragraph("Top 5 Most Sold Tickers", self.section_header_style)
            traded_title = Paragraph("Top 5 Most Traded Tickers", self.section_header_style)

            # Create containers with titles and tables
            bought_container = Table(
                [[bought_title], [Spacer(1, 8)], [bought_table]], colWidths=[2.8 * inch]
            )
            bought_container.setStyle(
                TableStyle(
                    [("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]
                )
            )

            sold_container = Table(
                [[sold_title], [Spacer(1, 8)], [sold_table]], colWidths=[2.8 * inch]
            )
            sold_container.setStyle(
                TableStyle(
                    [("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]
                )
            )

            traded_container = Table(
                [[traded_title], [Spacer(1, 8)], [traded_table]], colWidths=[2.8 * inch]
            )
            traded_container.setStyle(
                TableStyle(
                    [("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]
                )
            )

            # Arrange three containers side by side with more spacing
            spacer_cell1 = Table([[Spacer(1, 1)]], colWidths=[0.8 * inch])
            spacer_cell2 = Table([[Spacer(1, 1)]], colWidths=[0.8 * inch])
            tables_data = [
                [bought_container, spacer_cell1, sold_container, spacer_cell2, traded_container]
            ]
            three_tables = Table(
                tables_data, colWidths=[2.8 * inch, 0.8 * inch, 2.8 * inch, 0.8 * inch, 2.8 * inch]
            )
            three_tables.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            story.append(three_tables)

        # Build PDF with page numbers
        doc.build(story)
        print(f"Custom PDF report saved to: {filename}")
        return filename


def generate_report(portfolio, rf=0.02, bmk_returns=0.1, filename=None):
    if not hasattr(portfolio, "metrics") or not hasattr(portfolio, "holdings_summary"):
        portfolio.generate_analytics(rf=rf, bmk_returns=bmk_returns)

    generator = ReportGenerator(portfolio, portfolio.metrics, portfolio.holdings_summary)
    return generator.generate_report(filename=filename)
