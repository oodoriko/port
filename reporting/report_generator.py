import io
import os
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class ReportGenerator:
    def __init__(self, portfolio, metrics, holdings_summary):
        self.portfolio = portfolio
        self.metrics = metrics
        self.holdings_summary = holdings_summary
        self.styles = getSampleStyleSheet()

        # Create custom styles
        self.title_style = ParagraphStyle(
            "CustomTitle",
            parent=self.styles["Heading1"],
            fontSize=20,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.darkblue,
        )

        self.block_title_style = ParagraphStyle(
            "BlockTitle",
            parent=self.styles["Heading2"],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=15,
            textColor=colors.darkblue,
            alignment=TA_LEFT,
        )

        self.normal_style = ParagraphStyle(
            "CustomNormal",
            parent=self.styles["Normal"],
            fontSize=11,
            spaceAfter=6,
        )

    def create_header_info_block(self):
        """Create the header information block"""
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
            ["Analysis Period:", f"{start_date} to {end_date}"],
        ]

        table = Table(header_data, colWidths=[2.5 * inch, 4 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 1, colors.lightgrey),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ]
            )
        )

        return table

    def create_portfolio_config_block(self):
        """Create the portfolio configuration block"""
        # Get initial capital
        initial_capital = (
            self.portfolio.setup.get("initial_capital", 0)
            if hasattr(self.portfolio, "setup")
            else 0
        )

        # Get constraints information
        constraints_info = "None"
        if hasattr(self.portfolio, "constraints") and self.portfolio.constraints:
            constraints_list = []
            if hasattr(self.portfolio.constraints, "max_long_count"):
                constraints_list.append(
                    f"Max Long: {getattr(self.portfolio.constraints, 'max_long_count', 'N/A')}"
                )
            if hasattr(self.portfolio.constraints, "max_short_count"):
                constraints_list.append(
                    f"Max Short: {getattr(self.portfolio.constraints, 'max_short_count', 'N/A')}"
                )
            if constraints_list:
                constraints_info = ", ".join(constraints_list)

        config_data = [
            ["Initial Capital:", f"${initial_capital:,.2f}"],
            ["Transaction Cost:", f"{self.portfolio.transaction_cost:.3%}"],
            ["Universe Size:", f"{len(self.portfolio.universe)}"],
            ["Setup Constraints:", constraints_info],
        ]

        table = Table(config_data, colWidths=[2.5 * inch, 4 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 1, colors.lightgrey),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.lightblue),
                ]
            )
        )

        return table

    def create_key_performance_block(self):
        """Create the key performance metrics block"""
        performance_data = [
            ["Total Return:", f"{self.metrics['total_return']:.2%}"],
            ["Annualized Return:", f"{self.metrics['annualized_return']:.2%}"],
            ["Overall Sharpe Ratio:", f"{self.metrics['overall_sharpe_ratio']:.2f}"],
            ["Win Rate:", f"{self.metrics['win_rate']:.2%}"],
            ["Daily Win Rate:", f"{self.metrics['avg_win']:.2%}"],
        ]

        table = Table(performance_data, colWidths=[2.5 * inch, 4 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 1, colors.lightgrey),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.lightgreen),
                ]
            )
        )

        return table

    def create_holdings_analysis_chart(self):
        """Create holdings count over time line chart"""
        plt.style.use("default")
        fig, ax = plt.subplots(figsize=(10, 6))

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
                marker="o",
                markersize=4,
                linewidth=2,
                color="darkblue",
            )
            ax.set_title("Holdings Count Over Time", fontsize=14, fontweight="bold")
            ax.set_ylabel("Number of Holdings")
            ax.set_xlabel("Date")
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
        else:
            ax.text(
                0.5,
                0.5,
                "No holdings data available",
                transform=ax.transAxes,
                ha="center",
                va="center",
            )
            ax.set_title("Holdings Count Over Time", fontsize=14, fontweight="bold")

        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        buf.seek(0)
        plt.close()

        return buf

    def create_holdings_summary_table(self):
        """Create holdings summary table with max, min, and average"""
        if not self.holdings_summary["holdings_count"]:
            return None

        holdings_dates = list(self.holdings_summary["holdings_count"].keys())
        holdings_counts = list(self.holdings_summary["holdings_count"].values())

        # Find max and min
        max_holdings = max(holdings_counts)
        min_holdings = min(holdings_counts)
        avg_holdings = sum(holdings_counts) / len(holdings_counts)

        # Find dates for max and min
        max_date = holdings_dates[holdings_counts.index(max_holdings)]
        min_date = holdings_dates[holdings_counts.index(min_holdings)]

        summary_data = [
            ["Metric", "Value", "Date"],
            ["Maximum Holdings", f"{max_holdings}", str(max_date)],
            ["Minimum Holdings", f"{min_holdings}", str(min_date)],
            ["Average Holdings", f"{avg_holdings:.1f}", "Overall"],
        ]

        table = Table(summary_data, colWidths=[2 * inch, 1.5 * inch, 2.5 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.lightblue),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        return table

    def create_holding_duration_summary_table(self):
        """Create holding duration summary table with max and min"""
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

        table = Table(duration_data, colWidths=[2.5 * inch, 2 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.darkgreen),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.lightgreen),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        return table

    def create_top_duration_tables(self):
        """Create tables for top longest and shortest hold tickers"""
        if not self.holdings_summary["duration_by_ticker"]:
            return None, None

        duration_df = pd.DataFrame(self.holdings_summary["duration_by_ticker"])

        # Top 5 longest hold
        top_longest = duration_df.nlargest(5, "duration")[["ticker", "duration"]]
        longest_data = [["Ticker", "Duration (Days)"]]
        for _, row in top_longest.iterrows():
            longest_data.append([str(row["ticker"]), str(row["duration"])])

        longest_table = Table(longest_data, colWidths=[1.5 * inch, 1.5 * inch])
        longest_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.lightblue),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        # Top 5 shortest hold
        top_shortest = duration_df.nsmallest(5, "duration")[["ticker", "duration"]]
        shortest_data = [["Ticker", "Duration (Days)"]]
        for _, row in top_shortest.iterrows():
            shortest_data.append([str(row["ticker"]), str(row["duration"])])

        shortest_table = Table(shortest_data, colWidths=[1.5 * inch, 1.5 * inch])
        shortest_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.darkorange),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.lightyellow),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        return longest_table, shortest_table

    def create_portfolio_value_chart(self):
        """Create portfolio value over time line chart"""
        try:
            plt.figure(figsize=(12, 6))

            if "portfolio_value" in self.metrics and self.metrics["portfolio_value"]:
                dates = pd.to_datetime(list(self.metrics["portfolio_value"].keys()))
                values = list(self.metrics["portfolio_value"].values())

                plt.plot(dates, values, linewidth=2, color="darkblue", label="Portfolio Value")
                plt.title("Portfolio Value Over Time", fontsize=16, fontweight="bold")
                plt.xlabel("Date", fontsize=12)
                plt.ylabel("Portfolio Value ($)", fontsize=12)
                plt.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                plt.legend()

                # Format y-axis to show dollar amounts
                plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))

            plt.tight_layout()

            buffer = BytesIO()
            plt.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
            buffer.seek(0)
            plt.close()

            return Image(buffer, width=7 * inch, height=3.5 * inch)
        except Exception as e:
            plt.close()
            return Paragraph(f"Error creating portfolio value chart: {str(e)}", self.normal_style)

    def create_returns_charts(self):
        """Create daily, monthly, and annual returns line charts"""
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

            # Daily returns
            if "daily_returns" in self.metrics and self.metrics["daily_returns"]:
                dates = pd.to_datetime(list(self.metrics["daily_returns"].keys()))
                returns = [
                    float(r) * 100 for r in self.metrics["daily_returns"].values()
                ]  # Convert to percentage

                ax1.plot(dates, returns, linewidth=1, color="green", alpha=0.7)
                ax1.set_title("Daily Returns (%)", fontsize=14, fontweight="bold")
                ax1.set_ylabel("Return (%)")
                ax1.grid(True, alpha=0.3)
                ax1.tick_params(axis="x", rotation=45)

            # Monthly returns
            if "monthly_returns" in self.metrics and self.metrics["monthly_returns"]:
                dates = pd.to_datetime(list(self.metrics["monthly_returns"].keys()))
                returns = [float(r) * 100 for r in self.metrics["monthly_returns"].values()]

                ax2.plot(dates, returns, linewidth=2, color="orange", marker="o", markersize=4)
                ax2.set_title("Monthly Returns (%)", fontsize=14, fontweight="bold")
                ax2.set_ylabel("Return (%)")
                ax2.grid(True, alpha=0.3)
                ax2.tick_params(axis="x", rotation=45)

            # Annual returns
            if "annual_returns" in self.metrics and self.metrics["annual_returns"]:
                years = list(self.metrics["annual_returns"].keys())
                returns = [float(r) * 100 for r in self.metrics["annual_returns"].values()]

                ax3.bar(years, returns, color="purple", alpha=0.7)
                ax3.set_title("Annual Returns (%)", fontsize=14, fontweight="bold")
                ax3.set_ylabel("Return (%)")
                ax3.grid(True, alpha=0.3)
                ax3.tick_params(axis="x", rotation=45)

            # Sharpe ratio over time (rolling)
            if "sharpe_ratio" in self.holdings_summary:
                # Create a simple visualization showing Sharpe ratio
                ax4.text(
                    0.5,
                    0.5,
                    f'Overall Sharpe Ratio\n{self.holdings_summary["sharpe_ratio"]:.3f}',
                    horizontalalignment="center",
                    verticalalignment="center",
                    transform=ax4.transAxes,
                    fontsize=20,
                    fontweight="bold",
                    bbox=dict(boxstyle="round", facecolor="lightblue", alpha=0.8),
                )
                ax4.set_title("Sharpe Ratio", fontsize=14, fontweight="bold")
                ax4.set_xlim(0, 1)
                ax4.set_ylim(0, 1)
                ax4.set_xticks([])
                ax4.set_yticks([])

            plt.tight_layout()

            buffer = BytesIO()
            plt.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
            buffer.seek(0)
            plt.close()

            return Image(buffer, width=7 * inch, height=5 * inch)
        except Exception as e:
            plt.close()
            return Paragraph(f"Error creating returns charts: {str(e)}", self.normal_style)

    def create_return_distribution_charts(self):
        """Create return distribution analysis for daily and monthly returns"""
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

            # Daily return distribution
            if "daily_returns" in self.metrics and self.metrics["daily_returns"]:
                returns = [float(r) * 100 for r in self.metrics["daily_returns"].values()]

                ax1.hist(returns, bins=50, alpha=0.7, color="green", edgecolor="black")
                ax1.axvline(
                    np.mean(returns),
                    color="red",
                    linestyle="--",
                    linewidth=2,
                    label=f"Mean: {np.mean(returns):.2f}%",
                )
                ax1.axvline(
                    np.median(returns),
                    color="orange",
                    linestyle="--",
                    linewidth=2,
                    label=f"Median: {np.median(returns):.2f}%",
                )
                ax1.set_title("Daily Return Distribution", fontsize=14, fontweight="bold")
                ax1.set_xlabel("Daily Return (%)")
                ax1.set_ylabel("Frequency")
                ax1.legend()
                ax1.grid(True, alpha=0.3)

                # Add statistics text
                stats_text = f"Std: {np.std(returns):.2f}%\nSkew: {pd.Series(returns).skew():.2f}\nKurt: {pd.Series(returns).kurtosis():.2f}"
                ax1.text(
                    0.02,
                    0.98,
                    stats_text,
                    transform=ax1.transAxes,
                    fontsize=10,
                    verticalalignment="top",
                    bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
                )

            # Monthly return distribution
            if "monthly_returns" in self.metrics and self.metrics["monthly_returns"]:
                returns = [float(r) * 100 for r in self.metrics["monthly_returns"].values()]

                ax2.hist(returns, bins=20, alpha=0.7, color="orange", edgecolor="black")
                ax2.axvline(
                    np.mean(returns),
                    color="red",
                    linestyle="--",
                    linewidth=2,
                    label=f"Mean: {np.mean(returns):.2f}%",
                )
                ax2.axvline(
                    np.median(returns),
                    color="darkblue",
                    linestyle="--",
                    linewidth=2,
                    label=f"Median: {np.median(returns):.2f}%",
                )
                ax2.set_title("Monthly Return Distribution", fontsize=14, fontweight="bold")
                ax2.set_xlabel("Monthly Return (%)")
                ax2.set_ylabel("Frequency")
                ax2.legend()
                ax2.grid(True, alpha=0.3)

                # Add statistics text
                stats_text = f"Std: {np.std(returns):.2f}%\nSkew: {pd.Series(returns).skew():.2f}\nKurt: {pd.Series(returns).kurtosis():.2f}"
                ax2.text(
                    0.02,
                    0.98,
                    stats_text,
                    transform=ax2.transAxes,
                    fontsize=10,
                    verticalalignment="top",
                    bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
                )

            plt.tight_layout()

            buffer = BytesIO()
            plt.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
            buffer.seek(0)
            plt.close()

            return Image(buffer, width=7 * inch, height=3 * inch)
        except Exception as e:
            plt.close()
            return Paragraph(
                f"Error creating return distribution charts: {str(e)}", self.normal_style
            )

    def create_sector_exposure_chart(self):
        """Create multiline plot showing sector percentage over time"""
        plt.style.use("default")
        fig, ax = plt.subplots(figsize=(12, 8))

        if self.holdings_summary["sector_ts"] and self.holdings_summary["holdings_count"]:
            # Create dataframe from sector time series
            holdings_dates = list(self.holdings_summary["holdings_count"].keys())
            sector_df = pd.DataFrame(self.holdings_summary["sector_ts"])
            sector_df.index = pd.to_datetime(holdings_dates)
            sector_df = sector_df.sort_index()

            # Calculate total holdings for each date to get percentages
            holdings_df = (
                pd.DataFrame(
                    {
                        "Date": pd.to_datetime(holdings_dates),
                        "Total": list(self.holdings_summary["holdings_count"].values()),
                    }
                )
                .set_index("Date")
                .sort_index()
            )

            # Calculate percentages for each sector
            sector_pct_df = sector_df.div(holdings_df["Total"], axis=0) * 100
            sector_pct_df = sector_pct_df.fillna(0)

            # Plot each sector as a line
            colors_list = plt.cm.tab10(np.linspace(0, 1, len(sector_pct_df.columns)))
            for i, sector in enumerate(sector_pct_df.columns):
                ax.plot(
                    sector_pct_df.index,
                    sector_pct_df[sector],
                    marker="o",
                    markersize=3,
                    linewidth=2,
                    label=sector,
                    color=colors_list[i],
                )

            ax.set_title("Sector Exposure Over Time (%)", fontsize=14, fontweight="bold")
            ax.set_ylabel("Percentage of Portfolio (%)")
            ax.set_xlabel("Date")
            ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
        else:
            ax.text(
                0.5,
                0.5,
                "No sector data available",
                transform=ax.transAxes,
                ha="center",
                va="center",
            )
            ax.set_title("Sector Exposure Over Time (%)", fontsize=14, fontweight="bold")

        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        buf.seek(0)
        plt.close()

        return buf

    def create_sector_composition_pie(self):
        """Create pie chart of average sector composition"""
        plt.style.use("default")
        fig, ax = plt.subplots(figsize=(10, 8))

        if self.holdings_summary["sector_ts"]:
            # Calculate average sector composition
            sector_df = pd.DataFrame(self.holdings_summary["sector_ts"])
            avg_sector = sector_df.mean()
            avg_sector = avg_sector[avg_sector > 0]  # Only non-zero sectors

            if len(avg_sector) > 0:
                colors_list = plt.cm.Set3(np.linspace(0, 1, len(avg_sector)))
                wedges, texts, autotexts = ax.pie(
                    avg_sector.values,
                    labels=avg_sector.index,
                    autopct="%1.1f%%",
                    colors=colors_list,
                    startangle=90,
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

    def generate_page_2(self, story):
        """Generate page 2 - Portfolio Compositions"""
        # Page break and title
        story.append(PageBreak())
        title = Paragraph("Portfolio Compositions", self.title_style)
        story.append(title)
        story.append(Spacer(1, 30))

        # Holdings Analysis Section
        story.append(Paragraph("Holdings Analysis", self.block_title_style))

        # Holdings count chart
        holdings_chart = self.create_holdings_analysis_chart()
        img = Image(holdings_chart, width=6 * inch, height=3.6 * inch)
        story.append(img)
        story.append(Spacer(1, 15))

        # Holdings summary table
        holdings_table = self.create_holdings_summary_table()
        if holdings_table:
            story.append(holdings_table)
        story.append(Spacer(1, 20))

        # Holding duration summary table
        duration_summary_table = self.create_holding_duration_summary_table()
        if duration_summary_table:
            story.append(Paragraph("Holding Duration Summary", self.block_title_style))
            story.append(duration_summary_table)
            story.append(Spacer(1, 20))

        # Top duration tables
        longest_table, shortest_table = self.create_top_duration_tables()
        if longest_table and shortest_table:
            story.append(Paragraph("Top Duration Holdings", self.block_title_style))

            # Arrange duration tables side-by-side
            duration_tables_data = [
                [
                    Paragraph("Top 5 Longest Hold", self.normal_style),
                    Paragraph("Top 5 Shortest Hold", self.normal_style),
                ],
                [longest_table, shortest_table],
            ]

            combined_duration_table = Table(
                duration_tables_data, colWidths=[3.25 * inch, 3.25 * inch]
            )
            combined_duration_table.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 11),
                    ]
                )
            )
            story.append(combined_duration_table)
        story.append(Spacer(1, 30))

        # Sector Exposure Section
        story.append(Paragraph("Sector Exposure", self.block_title_style))

        # Sector exposure multiline chart
        sector_chart = self.create_sector_exposure_chart()
        img = Image(sector_chart, width=7 * inch, height=4.8 * inch)
        story.append(img)
        story.append(Spacer(1, 20))

        # Sector composition pie chart
        pie_chart = self.create_sector_composition_pie()
        img = Image(pie_chart, width=6 * inch, height=4.8 * inch)
        story.append(img)
        story.append(Spacer(1, 25))

    def create_trading_metrics_table(self):
        """Create trading metrics summary table"""
        total_buy_trades = sum(
            trade_data["buy"] for trade_data in self.holdings_summary["trades_ts"]
        )
        total_sell_trades = sum(
            trade_data["sell"] for trade_data in self.holdings_summary["trades_ts"]
        )
        total_trading_days = len(self.portfolio.trades_history)

        executed_days = sum(
            1 for status in self.portfolio.trades_status.values() if status == "executed"
        )
        cancelled_days = sum(
            1 for status in self.portfolio.trades_status.values() if status == "cancelled"
        )
        execution_rate = (
            executed_days / (executed_days + cancelled_days)
            if (executed_days + cancelled_days) > 0
            else 0
        )

        trading_data = [
            ["Trading Metric", "Value"],
            ["Total Trading Days", f"{total_trading_days}"],
            ["Total Buy Trades", f"{total_buy_trades}"],
            ["Total Sell Trades", f"{total_sell_trades}"],
            [
                "Avg Trades per Day",
                (
                    f"{(total_buy_trades + total_sell_trades) / total_trading_days:.1f}"
                    if total_trading_days > 0
                    else "N/A"
                ),
            ],
            ["Trade Execution Rate", f"{execution_rate:.2%}"],
            ["Cancelled Trades", f"{self.holdings_summary['cancelled_trades_count']}"],
        ]

        table = Table(trading_data, colWidths=[3 * inch, 2 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.darkorange),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.lightyellow),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        return table

    def create_trading_activity_chart(self):
        """Create trading activity bar chart with buy/sell bars and net trades"""
        plt.style.use("default")
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(12, 10), gridspec_kw={"height_ratios": [3, 1]}, sharex=True
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

            # Main chart - Buy/Sell bars with total trades line
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

            # Overlay total trades line
            ax1_twin = ax1.twinx()
            ax1_twin.plot(
                trades_df["Date"],
                trades_df["total_trades"],
                color="darkblue",
                linewidth=3,
                marker="o",
                markersize=4,
                label="Total Trades",
                alpha=0.8,
            )

            ax1.set_title("Trading Activity Over Time", fontsize=14, fontweight="bold")
            ax1.set_ylabel("Number of Trades (Buy +, Sell -)")
            ax1_twin.set_ylabel("Total Trades", color="darkblue")
            ax1.grid(True, alpha=0.3)
            ax1.axhline(y=0, color="black", linestyle="-", alpha=0.5)

            # Combine legends
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax1_twin.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

            # Bottom chart - Net trades (like volume)
            colors_net = ["green" if x >= 0 else "red" for x in trades_df["net_trades"]]
            ax2.bar(
                trades_df["Date"],
                trades_df["net_trades"],
                alpha=0.6,
                color=colors_net,
                width=bar_width,
            )
            ax2.set_ylabel("Net Trades\n(Buy - Sell)")
            ax2.set_xlabel("Date")
            ax2.grid(True, alpha=0.3)
            ax2.axhline(y=0, color="black", linestyle="-", alpha=0.5)

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

        bought_table = Table(bought_data, colWidths=[1.5 * inch, 1.5 * inch])
        bought_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.darkgreen),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.lightgreen),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        # Top 5 most sold
        top_sold = trades_df.nlargest(5, "sell")[["ticker", "sell"]]
        sold_data = [["Ticker", "Sell Trades"]]
        for _, row in top_sold.iterrows():
            sold_data.append([str(row["ticker"]), str(row["sell"])])

        sold_table = Table(sold_data, colWidths=[1.5 * inch, 1.5 * inch])
        sold_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.darkred),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.lightpink),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        # Top 5 most traded (total)
        top_traded = trades_df.nlargest(5, "total_trades")[["ticker", "total_trades"]]
        traded_data = [["Ticker", "Total Trades"]]
        for _, row in top_traded.iterrows():
            traded_data.append([str(row["ticker"]), str(row["total_trades"])])

        traded_table = Table(traded_data, colWidths=[1.5 * inch, 1.5 * inch])
        traded_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.lightblue),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        return bought_table, sold_table, traded_table

    def generate_page_3(self, story):
        """Generate page 3 - Trades Analysis"""
        # Page break and title
        story.append(PageBreak())
        title = Paragraph("Trades Analysis", self.title_style)
        story.append(title)
        story.append(Spacer(1, 30))

        # Trading Metrics Table
        story.append(Paragraph("Trading Metrics Summary", self.block_title_style))
        story.append(self.create_trading_metrics_table())
        story.append(Spacer(1, 25))

        # Trading Activity Chart
        story.append(Paragraph("Trading Activity Over Time", self.block_title_style))
        trading_chart = self.create_trading_activity_chart()
        img = Image(trading_chart, width=7 * inch, height=6 * inch)
        story.append(img)
        story.append(Spacer(1, 25))

        # Top Tickers Tables
        story.append(Paragraph("Top Trading Securities", self.block_title_style))
        bought_table, sold_table, traded_table = self.create_top_tickers_tables()

        if bought_table and sold_table and traded_table:
            # Arrange tables in a row
            tables_data = [
                [
                    Paragraph("Top 5 Most Bought", self.normal_style),
                    Paragraph("Top 5 Most Sold", self.normal_style),
                    Paragraph("Top 5 Most Traded", self.normal_style),
                ],
                [bought_table, sold_table, traded_table],
            ]

            combined_table = Table(tables_data, colWidths=[2.3 * inch, 2.3 * inch, 2.3 * inch])
            combined_table.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 11),
                    ]
                )
            )
            story.append(combined_table)
        story.append(Spacer(1, 25))

    def generate_page_4(self, story):
        """Generate Page 4: Portfolio Performance"""
        story.append(PageBreak())
        story.append(Paragraph("Portfolio Performance", self.title_style))
        story.append(Spacer(1, 30))

        # Portfolio value over time
        portfolio_value_chart = self.create_portfolio_value_chart()
        if portfolio_value_chart:
            story.append(Paragraph("Portfolio Value Over Time", self.block_title_style))
            story.append(portfolio_value_chart)
            story.append(Spacer(1, 20))

        # Returns analysis (daily, monthly, annual, Sharpe)
        returns_charts = self.create_returns_charts()
        if returns_charts:
            story.append(Paragraph("Returns Analysis", self.block_title_style))
            story.append(returns_charts)
            story.append(Spacer(1, 20))

        # Return distribution analysis
        distribution_charts = self.create_return_distribution_charts()
        if distribution_charts:
            story.append(Paragraph("Return Distribution Analysis", self.block_title_style))
            story.append(distribution_charts)
            story.append(Spacer(1, 30))

    def generate_page_1(self, story):
        """Generate page 1 with the three specified blocks"""
        # Title
        title = Paragraph("Portfolio Analysis Report", self.title_style)
        story.append(title)
        story.append(Spacer(1, 30))

        # Block 1: Header Information
        story.append(Paragraph("Portfolio Information", self.block_title_style))
        story.append(self.create_header_info_block())
        story.append(Spacer(1, 25))

        # Block 2: Portfolio Configuration
        story.append(Paragraph("Portfolio Configuration", self.block_title_style))
        story.append(self.create_portfolio_config_block())
        story.append(Spacer(1, 25))

        # Block 3: Key Performance Metrics
        story.append(Paragraph("Key Performance Metrics", self.block_title_style))
        story.append(self.create_key_performance_block())
        story.append(Spacer(1, 25))

    def generate_report(self, filename=None):
        """Generate the custom PDF report"""
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

        # Create PDF document
        doc = SimpleDocTemplate(filename, pagesize=A4)
        story = []

        # Generate Page 1
        self.generate_page_1(story)

        # Generate Page 2
        self.generate_page_2(story)

        # Generate Page 3
        self.generate_page_3(story)

        # Generate Page 4
        self.generate_page_4(story)

        # Build PDF
        doc.build(story)
        print(f"Custom PDF report saved to: {filename}")
        return filename


def generate_report(portfolio, rf=0.02, bmk_returns=0.1, filename=None):
    if not hasattr(portfolio, "metrics") or not hasattr(portfolio, "holdings_summary"):
        portfolio.generate_analytics(rf=rf, bmk_returns=bmk_returns)

    generator = ReportGenerator(portfolio, portfolio.metrics, portfolio.holdings_summary)
    return generator.generate_report(filename=filename)
