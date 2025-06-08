from enum import Enum
from io import BytesIO

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle


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
    CHARCOAL = colors.HexColor("#1A202C")  # Darker, more visible gray
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
    CHART_CHARCOAL = "#1A202C"  # Darker, more visible gray
    CHART_LIGHT_GRAY = "#F7FAFC"  # Very light gray
    CHART_MEDIUM_GRAY = "#E2E8F0"  # Medium gray
    CHART_DARK_GRAY = "#4A5568"  # Darker gray
    CHART_WHITE = "#FFFFFF"


class ReportStyling:
    """Helper class containing styling and generic functions for report generation"""

    def __init__(self, dpi=1000):
        self.styles = getSampleStyleSheet()
        self.custom_styles = StyleUtility()
        self.dpi = dpi
        # Multi-color theme for charts with multiple categories (sectors, etc.)
        self.multi_color_theme = plt.cm.Set2

        # Define major financial crisis periods for background overlays
        self.crisis_periods = [
            {
                "name": "Brexit Referendum",
                "start": "2016-06-20",
                "end": "2016-07-15",
                "color": "#E91E63",  # Pink
                "alpha": 0.15,
            },
            {
                "name": "COVID-19 Pandemic",
                "start": "2020-02-01",
                "end": "2020-04-01",
                "color": "#FF5722",  # Deep Orange
                "alpha": 0.18,
            },
            {
                "name": "Ukraine War",
                "start": "2022-02-24",
                "end": "2022-05-01",
                "color": "#9C27B0",  # Purple
                "alpha": 0.16,
            },
            {
                "name": "Inflation/Rate Hikes",
                "start": "2022-01-01",
                "end": "2022-10-01",
                "color": "#2196F3",  # Blue
                "alpha": 0.14,
            },
            {
                "name": "Liberation Day",
                "start": "2025-04-01",
                "end": "2025-04-30",
                "color": "#4CAF50",  # Green
                "alpha": 0.15,
            },
        ]

    def add_crisis_overlays(self, ax, date_range=None, add_legend=False):
        """
        Add financial crisis period overlays to a chart

        Parameters:
        - ax: matplotlib axes object
        - date_range: tuple of (start_date, end_date) to filter relevant crises
        - add_legend: whether to add crisis legend to this axes object

        Returns:
        - list of crisis patches for custom legend handling
        """
        # Convert string dates to datetime for comparison
        crisis_patches = []

        for crisis in self.crisis_periods:
            crisis_start = pd.to_datetime(crisis["start"])
            crisis_end = pd.to_datetime(crisis["end"])

            # Filter crises that overlap with the chart's date range
            if date_range:
                chart_start, chart_end = date_range
                chart_start = pd.to_datetime(chart_start)
                chart_end = pd.to_datetime(chart_end)
                # Check if crisis overlaps with chart date range
                if crisis_end < chart_start or crisis_start > chart_end:
                    continue  # Skip this crisis as it doesn't overlap

            # Add the crisis overlay - convert to matplotlib date format
            patch = ax.axvspan(
                mdates.date2num(crisis_start),
                mdates.date2num(crisis_end),
                color=crisis["color"],
                alpha=crisis["alpha"],
                label=f"{crisis['name']}" if add_legend else "",
                zorder=0,  # Send to background
            )
            crisis_patches.append(
                {"patch": patch, "name": crisis["name"], "color": crisis["color"]}
            )

        return crisis_patches

    def setup_matplotlib_style(self, legend_fontsize=12):
        """Setup consistent matplotlib styling for all charts"""
        plt.style.use("default")
        plt.rcParams.update(
            {
                "font.family": ["Arial", "Helvetica", "sans-serif"],
                "font.size": 12,
                "axes.titlesize": 18,
                "axes.labelsize": 14,
                "xtick.labelsize": 11,
                "ytick.labelsize": 11,
                "legend.fontsize": legend_fontsize,
                "axes.spines.top": False,
                "axes.spines.right": False,
                "axes.grid": True,
                "grid.alpha": 0.3,
            }
        )

    def create_styled_table(
        self,
        data,
        column_widths,
        header_color=None,
        header_text_color=None,
        body_bg_color=None,
        font_sizes=None,
        custom_styles=None,
    ):
        """
        Generic table creation function with consistent professional styling

        Parameters:
        - data: List of lists containing table data (first row should be headers)
        - column_widths: List of column widths
        - header_color: Color for header background (defaults to SLATE_BLUE)
        - header_text_color: Color for header text (defaults to WHITE)
        - body_bg_color: Color for body background (defaults to LIGHT_GRAY)
        - font_sizes: Dict with 'header' and 'body' keys for font sizes
        - custom_styles: Additional TableStyle commands to apply
        """
        if header_color is None:
            header_color = Colors.SLATE_BLUE
        if header_text_color is None:
            header_text_color = Colors.WHITE
        if body_bg_color is None:
            body_bg_color = Colors.LIGHT_GRAY
        if font_sizes is None:
            font_sizes = {"header": 12, "body": 11}

        table = Table(data, colWidths=column_widths)

        # Base table style
        base_style = [
            # Header styling
            ("BACKGROUND", (0, 0), (-1, 0), header_color),
            ("TEXTCOLOR", (0, 0), (-1, 0), header_text_color),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), font_sizes["header"]),
            # Body styling
            ("BACKGROUND", (0, 1), (-1, -1), body_bg_color),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), font_sizes["body"]),
            # Common styling
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("LINEBELOW", (0, 0), (-1, -1), 1, Colors.MEDIUM_GRAY),
            ("BOX", (0, 0), (-1, -1), 1.5, header_color),
        ]

        # Add custom styles if provided
        if custom_styles:
            base_style.extend(custom_styles)

        table.setStyle(TableStyle(base_style))
        return table

    def create_generic_line_chart(
        self,
        metrics=None,
        data_dict=None,
        data_key=None,
        title=None,
        color=Colors.CHART_NAVY,
        linewidth=1,
        markersize=0,
        resample_freq=None,
        date_format="%Y-%m",
        y_label="Value",
        y_formatter=None,
        no_data_message="No data available",
        multiply_by_100=False,
        add_zero_line=False,
        interval=1,
        normal_style=None,
        show_crisis_periods=True,
        graph_type="D",
    ):
        """
        Unified generic function to create line charts for any time series data

        Parameters:
        - portfolio: Portfolio object (for portfolio values, holdings, etc.)
        - metrics: Metrics dictionary (for returns data)
        - data_dict: Direct data dictionary (for portfolio values, holdings, etc.)
        - data_key: Key to look up in metrics (for returns data)
        - multiply_by_100: Whether to convert to percentage (for returns)
        - add_zero_line: Whether to add horizontal line at y=0 (for returns)
        - interval: Date interval for x-axis formatting
        - show_crisis_periods: Whether to overlay financial crisis periods in background
        """
        try:
            # Set professional matplotlib styling
            self.setup_matplotlib_style()

            fig, ax = plt.subplots(figsize=(10, 7))
            fig.patch.set_facecolor("white")

            # Get data from either direct dict or metrics lookup
            if data_dict is not None:
                # Direct data dictionary (portfolio values, holdings count, etc.)
                if data_dict and len(data_dict) > 0:
                    dates = pd.to_datetime(list(data_dict.keys()))
                    values = list(data_dict.values())

                    # Convert to percentage if needed
                    if multiply_by_100:
                        values = [float(v) * 100 for v in values]

                    df = pd.DataFrame({"Date": dates, "Value": values})
                    df.set_index("Date", inplace=True)
                    df = df.sort_index()

                    # Apply resampling if specified for portfolio value data
                    # For portfolio values, we want to show the actual progression, not just end-of-period values
                    if resample_freq:
                        # Create a complete date range to avoid missing data
                        full_date_range = pd.date_range(
                            start=df.index.min(), end=df.index.max(), freq="D"
                        )
                        df = df.reindex(full_date_range).ffill()

                        if resample_freq == "M":  # Monthly
                            # For better visualization, sample at monthly intervals but keep all data points
                            if len(df) > 100:  # Only resample if we have lots of data
                                df = df.resample("ME").last()
                            date_format = "%Y-%m"
                        elif resample_freq == "Q":  # Quarterly
                            # For better visualization, sample at quarterly intervals but keep all data points
                            if len(df) > 50:  # Only resample if we have lots of data
                                df = df.resample("QE").last()
                            date_format = "%Y-%q"
                        elif resample_freq == "Y":  # Yearly
                            # For better visualization, sample at yearly intervals but keep all data points
                            if len(df) > 20:  # Only resample if we have lots of data
                                df = df.resample("YE").last()
                            date_format = "%Y"

                    has_data = True

                    # Only switch to daily format if we have very few data points
                    if graph_type == "D" and len(df) <= 7:  # Less than a week of data
                        date_format = "%Y-%m-%d"
                else:
                    has_data = False
            elif data_key is not None:
                # Look up in metrics (returns data)
                if (
                    data_key in metrics
                    and metrics[data_key] is not None
                    and len(metrics[data_key]) > 0
                ):
                    returns_data = metrics[data_key]

                    # Handle different data structures for returns
                    if hasattr(returns_data, "keys") and hasattr(returns_data, "values"):
                        # This is a dict-like structure
                        if graph_type == "Y":
                            # For yearly returns, keys should be years
                            dates_or_years = list(returns_data.keys())
                        else:
                            # For daily/monthly/quarterly returns
                            dates_or_years = list(returns_data.keys())

                        values = [float(r) * 100 for r in returns_data.values]
                    else:
                        if graph_type == "Y":
                            dates_or_years = (
                                list(returns_data.index) if hasattr(returns_data, "index") else []
                            )
                            values = (
                                [float(r) * 100 for r in returns_data]
                                if len(dates_or_years) > 0
                                else []
                            )
                        else:
                            dates_or_years = (
                                pd.to_datetime(list(returns_data.index))
                                if hasattr(returns_data, "index")
                                else []
                            )
                            values = (
                                [float(r) * 100 for r in returns_data]
                                if len(dates_or_years) > 0
                                else []
                            )

                    # For returns data, we work with the raw dates/values
                    has_data = len(dates_or_years) > 0 and len(values) > 0
                else:
                    has_data = False
            else:
                raise ValueError("Must provide either data_dict or data_key")

            if has_data:
                # Plot configuration
                plot_kwargs = {
                    "linewidth": linewidth,
                    "color": color,
                }

                # Add markers if specified
                if markersize > 0:
                    plot_kwargs.update({"marker": "o", "markersize": markersize})

                # Plot the data
                if data_dict is not None:
                    # Regular time series data (portfolio values, holdings)
                    ax.plot(df.index, df["Value"], **plot_kwargs)
                    date_formatting_needed = True
                else:
                    # Returns data (already processed dates_or_years and values)
                    # Determine if we have datetime data or sequential data
                    if len(dates_or_years) > 0:
                        first_item = dates_or_years[0]
                        # Check if it's integer data (sequential indices)
                        if isinstance(first_item, (int, np.integer)):
                            # Plot as sequential data
                            ax.plot(range(len(values)), values, **plot_kwargs)
                            ax.set_xlabel("Period", fontsize=14, color=Colors.CHART_CHARCOAL)
                            date_formatting_needed = False
                        else:
                            # Try to convert to datetime if it's not already
                            try:
                                if not hasattr(first_item, "year"):  # Not already a datetime
                                    dates_or_years = pd.to_datetime(dates_or_years)
                                ax.plot(dates_or_years, values, **plot_kwargs)
                                date_formatting_needed = True
                            except:
                                # If datetime conversion fails, plot as sequential
                                ax.plot(range(len(values)), values, **plot_kwargs)
                                ax.set_xlabel("Period", fontsize=14, color=Colors.CHART_CHARCOAL)
                                date_formatting_needed = False
                    else:
                        # Empty data
                        date_formatting_needed = False

                # Add zero line for returns charts
                if add_zero_line:
                    ax.axhline(y=0, color=Colors.CHART_CHARCOAL, linestyle="--", alpha=0.5)

                    # Add financial crisis overlays if requested
                crisis_overlays = []
                if show_crisis_periods and graph_type != "Y" and date_formatting_needed:
                    # Determine date range for filtering relevant crises
                    date_range = None
                    if data_dict is not None:
                        date_range = (df.index.min(), df.index.max())
                    else:
                        # Only create date range if we have actual datetime objects
                        if len(dates_or_years) > 0 and hasattr(dates_or_years[0], "year"):
                            date_range = (min(dates_or_years), max(dates_or_years))

                    # Only add overlays if we have a valid date range
                    if date_range is not None:
                        crisis_overlays = self.add_crisis_overlays(ax, date_range)

                # Set y-axis label and formatting
                ax.set_ylabel(y_label, fontsize=14, color=Colors.CHART_CHARCOAL)

                if y_formatter and data_dict is not None:
                    ax.yaxis.set_major_formatter(y_formatter)

                # Date formatting - only apply if we have actual dates
                if data_dict is not None or (data_key is not None and date_formatting_needed):
                    if date_format == "%Y":
                        # For annual data, show every year if there are few years
                        if data_dict is not None:
                            years_span = (df.index.max() - df.index.min()).days / 365.25
                        else:
                            years_span = len(dates_or_years) if len(dates_or_years) < 20 else 20
                        year_interval = max(1, int(years_span / 10)) if years_span > 10 else 1
                        ax.xaxis.set_major_locator(mdates.YearLocator(base=year_interval))
                        ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
                    elif date_format == "%Y-%m":
                        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=interval))
                        ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
                    elif date_format in ["%Y-%q", "%Y-Q%q"]:  # Handle quarterly format
                        ax.xaxis.set_major_locator(
                            mdates.MonthLocator(bymonth=[1, 4, 7, 10], interval=interval)
                        )

                        # Use quarterly months formatter - will show as Q1, Q2, Q3, Q4
                        def quarter_formatter(x, pos):
                            date = mdates.num2date(x)
                            quarter = (date.month - 1) // 3 + 1
                            return f"{date.year}-Q{quarter}"

                        ax.xaxis.set_major_formatter(plt.FuncFormatter(quarter_formatter))
                    elif date_format == "%Y-%m-%d":
                        ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
                        ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))

                    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

                # Legend only if there are crisis overlays (legend entries)
                if crisis_overlays:
                    legend = ax.legend(
                        frameon=True,
                        fancybox=True,
                        shadow=True,
                        facecolor=Colors.CHART_WHITE,
                        edgecolor=Colors.CHART_BLUE,
                        loc="best",
                        fontsize=10,
                    )
                    legend.get_frame().set_alpha(0.9)
            else:
                # No data available
                if data_key is not None:
                    message = f"No {data_key.replace('_', ' ')} data available"
                else:
                    message = no_data_message

                ax.text(
                    0.5,
                    0.5,
                    message,
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=16,
                    color=Colors.CHART_DEEP_BLUE,
                    weight="bold",
                )

            # Set title and styling (applied to both cases)
            if title:
                ax.set_title(
                    title,
                    fontsize=20,
                    fontweight="bold",
                    color=Colors.CHART_DEEP_BLUE,
                    pad=25,
                )

            ax.tick_params(colors=Colors.CHART_CHARCOAL)
            ax.grid(True, alpha=0.3, color=Colors.CHART_MEDIUM_GRAY)
            ax.set_facecolor(Colors.CHART_LIGHT_GRAY)

            plt.tight_layout(pad=1.0)

            buffer = BytesIO()
            fig.savefig(
                buffer,
                format="png",
                dpi=self.dpi,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
            buffer.seek(0)
            plt.close()

            return buffer
        except Exception as e:
            plt.close()
            chart_name = title.lower() if title else "chart"
            if normal_style:
                return Paragraph(f"Error creating {chart_name}: {str(e)}", normal_style)
            else:
                return f"Error creating {chart_name}: {str(e)}"

    def create_generic_distribution_chart(
        self,
        metrics,
        data_key,
        title=None,
        bins=50,
        color=Colors.CHART_NAVY,
        median_color=Colors.CHART_GOLD,
        normal_style=None,
    ):
        """
        Generic function to create return distribution charts

        Parameters:
        - metrics: Metrics dictionary
        - data_key: Key to look up in metrics (e.g., 'daily_returns', 'monthly_returns')
        - title: Chart title
        - bins: Number of histogram bins
        - color: Main histogram color
        - median_color: Color for median line
        - normal_style: Style for error paragraphs
        """
        try:
            # Set professional matplotlib styling
            self.setup_matplotlib_style()

            fig, ax = plt.subplots(figsize=(12, 8))
            fig.patch.set_facecolor("white")

            # Check if data exists
            if data_key in metrics and metrics[data_key] is not None and len(metrics[data_key]) > 0:
                returns_data = metrics[data_key]
                if hasattr(returns_data, "values"):
                    returns = [float(r) * 100 for r in returns_data.values]
                else:
                    returns = [float(r) * 100 for r in returns_data]

                ax.hist(
                    returns,
                    bins=bins,
                    alpha=0.7,
                    color=color,
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
                    color=median_color,
                    linestyle="--",
                    linewidth=3,
                    label=f"Median: {np.median(returns):.2f}%",
                )

                # Format axis labels based on data type
                data_type = data_key.replace("_returns", "").title()
                ax.set_xlabel(f"{data_type} Return (%)", fontsize=14, color=Colors.CHART_CHARCOAL)
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
                no_data_message = f"No {data_key.replace('_', ' ')} data available"
                ax.text(
                    0.5,
                    0.5,
                    no_data_message,
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=16,
                    color=Colors.CHART_DEEP_BLUE,
                    weight="bold",
                )

            if title:
                ax.set_title(
                    title,
                    fontsize=20,
                    fontweight="bold",
                    color=Colors.CHART_DEEP_BLUE,
                    pad=25,
                )

            plt.tight_layout(pad=1.0)

            buffer = BytesIO()
            fig.savefig(
                buffer,
                format="png",
                dpi=self.dpi,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
            buffer.seek(0)
            plt.close()

            return buffer
        except Exception as e:
            plt.close()
            chart_name = title.lower() if title else "chart"
            if normal_style:
                return Paragraph(f"Error creating {chart_name}: {str(e)}", normal_style)
            else:
                return f"Error creating {chart_name}: {str(e)}"

    def create_table_title(self, title_text, color=None, base_title_style=None):
        """Create a table title paragraph with custom color"""
        if color is None:
            color = Colors.NAVY_BLUE  # Default color

        if base_title_style is None:
            # Create default base style if not provided
            base_title_style = ParagraphStyle(
                "BaseTableTitle",
                parent=getSampleStyleSheet()["Heading3"],
                fontName="Helvetica-Bold",
                fontSize=16,
                spaceAfter=10,
                spaceBefore=15,
                alignment=TA_CENTER,
                leading=18,
            )

        # Create a custom style with the specified color
        custom_title_style = ParagraphStyle(
            f"TableTitle_{title_text.replace(' ', '_')}",
            parent=base_title_style,
            textColor=color,
        )

        return Paragraph(title_text, custom_title_style)

    def create_generic_pie_chart(
        self,
        data_dict,
        title=None,
        figsize=(10, 7),
        fontsize=11,
        no_data_message="No data available",
        normal_style=None,
    ):
        """
        Generic function to create pie charts

        Parameters:
        - data_dict: Dictionary with labels as keys and values as values
        - title: Chart title
        - figsize: Figure size tuple
        - fontsize: Base font size
        - no_data_message: Message to show when no data
        - normal_style: Style for error paragraphs
        """
        try:
            plt.style.use("default")
            plt.rcParams.update(
                {
                    "font.family": ["Arial", "Helvetica", "sans-serif"],
                    "font.size": fontsize,
                }
            )
            fig, ax = plt.subplots(figsize=figsize)

            if data_dict and len(data_dict) > 0:
                # Filter out zero values
                filtered_data = {k: v for k, v in data_dict.items() if v > 0}

                if len(filtered_data) > 0:
                    labels = list(filtered_data.keys())
                    values = list(filtered_data.values())

                    # Use multi-color theme for pie chart
                    colors_list = self.multi_color_theme(np.linspace(0, 1, len(labels)))

                    wedges, texts, autotexts = ax.pie(
                        values,
                        autopct="%1.1f%%",
                        colors=colors_list,
                        startangle=90,
                        pctdistance=0.85,
                    )

                    # Style the percentage text
                    for autotext in autotexts:
                        autotext.set_color("white")
                        autotext.set_fontweight("bold")
                        autotext.set_fontsize(fontsize)
                        autotext.set_family("Arial")

                    # Create legend
                    ax.legend(
                        wedges,
                        labels,
                        title="Categories",
                        loc="center left",
                        bbox_to_anchor=(1, 0, 0.5, 1),
                        fontsize=fontsize,
                        title_fontsize=fontsize + 1,
                        frameon=True,
                        fancybox=True,
                        shadow=True,
                        facecolor=Colors.CHART_WHITE,
                        edgecolor=Colors.CHART_BLUE,
                    )

                    if title:
                        ax.set_title(
                            title,
                            fontsize=fontsize + 5,
                            fontweight="bold",
                            color=Colors.CHART_DEEP_BLUE,
                            pad=20,
                            family="Arial",
                        )
                else:
                    # No non-zero data
                    ax.text(
                        0.5, 0.5, no_data_message, transform=ax.transAxes, ha="center", va="center"
                    )
                    if title:
                        ax.set_title(
                            title,
                            fontsize=fontsize + 3,
                            fontweight="bold",
                        )
            else:
                # No data at all
                ax.text(0.5, 0.5, no_data_message, transform=ax.transAxes, ha="center", va="center")
                if title:
                    ax.set_title(
                        title,
                        fontsize=fontsize + 3,
                        fontweight="bold",
                    )

            plt.tight_layout(pad=1.0)

            buffer = BytesIO()
            fig.savefig(buffer, format="png", dpi=self.dpi, bbox_inches="tight")
            buffer.seek(0)
            plt.close()

            return buffer
        except Exception as e:
            plt.close()
            chart_name = title.lower() if title else "chart"
            if normal_style:
                return Paragraph(f"Error creating {chart_name}: {str(e)}", normal_style)
            else:
                return f"Error creating {chart_name}: {str(e)}"

    def create_generic_multiline_chart(
        self,
        data_df,
        title=None,
        figsize=(10, 5),
        y_label="Value",
        interval=1,
        date_format="%Y-%m",
        legend_position="top",
        legend_ncol=3,
        no_data_message="No data available",
        normal_style=None,
    ):
        """
        Generic function to create multi-line charts (like sector exposure over time)

        Parameters:
        - data_df: DataFrame with datetime index and multiple columns for different lines
        - title: Chart title
        - figsize: Figure size
        - y_label: Y-axis label
        - interval: Date interval for x-axis
        - date_format: Date format for x-axis
        - legend_position: "top" or other legend positions
        - legend_ncol: Number of columns in legend
        - no_data_message: Message when no data
        - normal_style: Style for error paragraphs
        """
        try:
            # Set professional matplotlib styling
            self.setup_matplotlib_style(legend_fontsize=11)

            # Increase height slightly for better utilization
            enhanced_figsize = (figsize[0], figsize[1] + 1) if len(figsize) == 2 else (10, 6)
            fig, ax = plt.subplots(figsize=enhanced_figsize)
            fig.patch.set_facecolor("white")
            if data_df is not None and len(data_df) > 0 and len(data_df.columns) > 0:
                # Use multi-color theme for better visual distinction
                colors = self.multi_color_theme(np.linspace(0, 1, len(data_df.columns)))

                # Plot each column as a line
                for i, column in enumerate(data_df.columns):
                    ax.plot(
                        data_df.index,
                        data_df[column],
                        linewidth=1,
                        label=column,
                        color=colors[i],
                    )

                if title:
                    ax.set_title(
                        title,
                        fontsize=20,
                        fontweight="bold",
                        color=Colors.CHART_DEEP_BLUE,
                        pad=25,
                    )

                # Adapt date format based on data density
                if date_format == "%Y-%m" and len(data_df) <= 7:  # Less than a week of data
                    date_format = "%Y-%m-%d"
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
                elif date_format == "%Y-%q" and len(data_df.resample("Q").last()) <= 1:
                    date_format = "%Y-%m"
                    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=interval))
                elif date_format == "%Y" and len(data_df.resample("Y").last()) <= 1:
                    date_format = "%Y-%q"
                    ax.xaxis.set_major_locator(
                        mdates.MonthLocator(bymonth=[1, 4, 7, 10], interval=interval)
                    )
                else:
                    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=interval))

                # Handle quarterly format properly
                if date_format == "%Y-%q":

                    def quarter_formatter_multi(x, pos):
                        date = mdates.num2date(x)
                        quarter = (date.month - 1) // 3 + 1
                        return f"{date.year}-Q{quarter}"

                    ax.xaxis.set_major_formatter(plt.FuncFormatter(quarter_formatter_multi))
                else:
                    ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
                ax.set_ylabel(y_label, fontsize=14, color=Colors.CHART_CHARCOAL)

                # Professional styling
                ax.tick_params(colors=Colors.CHART_CHARCOAL)
                ax.grid(True, alpha=0.3, color=Colors.CHART_MEDIUM_GRAY)
                ax.set_facecolor(Colors.CHART_LIGHT_GRAY)

                # Legend styling
                if legend_position == "top":
                    legend = ax.legend(
                        bbox_to_anchor=(0.5, 1.02),
                        loc="lower center",
                        ncol=legend_ncol,
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
                    no_data_message,
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=16,
                    color=Colors.CHART_CHARCOAL,
                )
                if title:
                    ax.set_title(
                        title,
                        fontsize=20,
                        fontweight="bold",
                        color=Colors.CHART_DEEP_BLUE,
                        pad=25,
                    )

            plt.tight_layout(pad=1.0)

            buffer = BytesIO()
            fig.savefig(
                buffer,
                format="png",
                dpi=self.dpi,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
            buffer.seek(0)
            plt.close()

            return buffer
        except Exception as e:
            plt.close()
            chart_name = title.lower() if title else "chart"
            if normal_style:
                return Paragraph(f"Error creating {chart_name}: {str(e)}", normal_style)
            else:
                return f"Error creating {chart_name}: {str(e)}"

    def create_generic_boxplot(
        self,
        data_dict,
        title=None,
        figsize=(10, 6),
        y_label="Value",
        no_data_message="No data available",
        normal_style=None,
    ):
        """
        Create a generic box plot chart

        Parameters:
        - data_dict: Dictionary where keys are categories and values are lists of data points
        - title: Chart title
        - figsize: Figure size tuple
        - y_label: Y-axis label
        - no_data_message: Message to display when no data is available
        - normal_style: Text style for error messages
        """
        try:
            self.setup_matplotlib_style()
            fig, ax = plt.subplots(figsize=figsize)

            if data_dict and any(len(values) > 0 for values in data_dict.values()):
                # Filter out empty data
                filtered_data = {k: v for k, v in data_dict.items() if len(v) > 0}

                if filtered_data:
                    # Create box plot
                    box_data = list(filtered_data.values())
                    box_labels = list(filtered_data.keys())

                    bp = ax.boxplot(
                        box_data,
                        labels=box_labels,
                        patch_artist=True,
                        boxprops=dict(facecolor=Colors.CHART_BLUE, alpha=0.7),
                        medianprops=dict(color=Colors.CHART_GOLD, linewidth=2),
                        whiskerprops=dict(color=Colors.CHART_NAVY),
                        capprops=dict(color=Colors.CHART_NAVY),
                        flierprops=dict(
                            marker="o", markerfacecolor=Colors.CHART_RED, markersize=6, alpha=0.5
                        ),
                    )

                    ax.set_ylabel(y_label, fontsize=14, fontweight="bold")
                    ax.tick_params(axis="x", rotation=45)

                    # Add grid
                    ax.grid(True, alpha=0.3)

                    if title:
                        ax.set_title(title, fontsize=16, fontweight="bold", pad=20)
                else:
                    ax.text(
                        0.5, 0.5, no_data_message, transform=ax.transAxes, ha="center", va="center"
                    )
                    if title:
                        ax.set_title(title, fontsize=14, fontweight="bold")
            else:
                ax.text(0.5, 0.5, no_data_message, transform=ax.transAxes, ha="center", va="center")
                if title:
                    ax.set_title(title, fontsize=14, fontweight="bold")

            plt.tight_layout(pad=1.0)

            buffer = BytesIO()
            fig.savefig(buffer, format="png", dpi=self.dpi, bbox_inches="tight")
            buffer.seek(0)
            plt.close()

            return buffer
        except Exception as e:
            plt.close()
            chart_name = title.lower() if title else "chart"
            if normal_style:
                return Paragraph(f"Error creating {chart_name}: {str(e)}", normal_style)
            else:
                return f"Error creating {chart_name}: {str(e)}"

    def create_generic_dual_axis_chart(
        self,
        data_dict_left=None,
        data_dict_right=None,
        data_key_left=None,
        data_key_right=None,
        metrics=None,
        title=None,
        left_y_label="Left Y-axis",
        right_y_label="Right Y-axis",
        left_color=Colors.CHARCOAL,
        right_color=Colors.CHARCOAL,
        left_linestyle="-",
        right_linestyle="-",
        left_linewidth=1,
        right_linewidth=1,
        left_marker="",
        right_marker="",
        figsize=(10, 6),
        resample_freq=None,
        date_format="%Y-%m",
        no_data_message="No data available",
        normal_style=None,
        show_crisis_periods=True,
        interval=1,
        graph_type="D",
        # Bar chart parameters
        bar_data_dict=None,
        bar_label="Bar Data",
        bar_color="lightgray",
        bar_alpha=0.7,
        bar_width=25,
        bar_position_ratio=0.80,  # Position bars at 80% of bottom value
        bar_height_ratio=0.15,  # Bars take 15% of chart height
        right_axis_zero_line=False,  # Add horizontal line at 0 for right axis
    ):
        """
        Create a generic dual y-axis line chart with optional bar chart below

        Parameters:
        - data_dict_left/right: Dictionary with datetime keys and numeric values for left/right axis
        - data_key_left/right: Key to extract from metrics dictionary for left/right axis
        - metrics: Metrics object containing the data
        - title: Chart title
        - left/right_y_label: Y-axis labels
        - left/right_color: Line colors
        - left/right_linestyle: Line styles ('-', '--', '-.', ':')
        - left/right_linewidth: Line widths
        - left/right_marker: Marker styles ('o', 's', '^', etc.)
        - figsize: Figure size tuple
        - resample_freq: Frequency for resampling ('D', 'M', 'Q', 'Y')
        - date_format: Format for date labels
        - no_data_message: Message when no data available
        - normal_style: Text style for error messages
        - show_crisis_periods: Whether to show crisis overlays
        - interval: Interval for date labels
        - graph_type: Graph type for date formatting
        - bar_data_dict: Dictionary with datetime keys and numeric values for bar chart
        - bar_label: Label for bar chart in legend
        - bar_color: Color for bars
        - bar_alpha: Transparency for bars (0.0 to 1.0)
        - bar_width: Width of bars
        - bar_position_ratio: Position bars at this ratio of bottom chart value
        - bar_height_ratio: Bar height as ratio of chart height
        - right_axis_zero_line: Add horizontal line at 0 for right axis (useful for returns)
        """
        try:
            self.setup_matplotlib_style()
            fig, ax1 = plt.subplots(figsize=figsize)

            # Prepare data for left axis
            left_data = None
            if data_dict_left:
                left_data = data_dict_left
            elif metrics and data_key_left:
                left_data = getattr(metrics, data_key_left, {})

            # Prepare data for right axis
            right_data = None
            if data_dict_right:
                right_data = data_dict_right
            elif metrics and data_key_right:
                right_data = getattr(metrics, data_key_right, {})

            # Check if we have any data
            has_left_data = left_data and len(left_data) > 0
            has_right_data = right_data and len(right_data) > 0

            if not has_left_data and not has_right_data:
                ax1.text(
                    0.5, 0.5, no_data_message, transform=ax1.transAxes, ha="center", va="center"
                )
                if title:
                    ax1.set_title(title, fontsize=16, fontweight="bold", pad=20)
                plt.tight_layout()
                buffer = BytesIO()
                fig.savefig(buffer, format="png", dpi=self.dpi, bbox_inches="tight")
                buffer.seek(0)
                plt.close()
                return buffer

            # Create second y-axis
            ax2 = ax1.twinx()

            # Plot left axis data
            if has_left_data:
                df_left = pd.DataFrame(list(left_data.items()), columns=["date", "value"])
                df_left["date"] = pd.to_datetime(
                    df_left["date"], format="%Y-%m-%d", errors="coerce"
                )
                df_left = df_left.dropna(subset=["date"])  # Remove any failed conversions
                df_left = df_left.sort_values("date")
                df_left.set_index("date", inplace=True)

                # Resample if requested
                if resample_freq:
                    if resample_freq == "M":
                        df_left = df_left.resample("ME").last()
                    elif resample_freq == "Q":
                        df_left = df_left.resample("QE").last()
                    elif resample_freq == "Y":
                        df_left = df_left.resample("YE").last()

                line1 = ax1.plot(
                    df_left.index,
                    df_left["value"],
                    color=left_color,
                    linestyle=left_linestyle,
                    linewidth=left_linewidth,
                    marker=left_marker,
                    label=left_y_label,
                )
                ax1.set_ylabel(left_y_label, color=left_color, fontsize=14, fontweight="bold")
                ax1.tick_params(axis="y", labelcolor=left_color)

            # Plot right axis data
            if has_right_data:
                df_right = pd.DataFrame(list(right_data.items()), columns=["date", "value"])
                df_right["date"] = pd.to_datetime(
                    df_right["date"], format="%Y-%m-%d", errors="coerce"
                )
                df_right = df_right.dropna(subset=["date"])  # Remove any failed conversions
                df_right = df_right.sort_values("date")
                df_right.set_index("date", inplace=True)

                # Resample if requested
                if resample_freq:
                    if resample_freq == "M":
                        df_right = df_right.resample("ME").last()
                    elif resample_freq == "Q":
                        df_right = df_right.resample("QE").last()
                    elif resample_freq == "Y":
                        df_right = df_right.resample("YE").last()

                line2 = ax2.plot(
                    df_right.index,
                    df_right["value"],
                    color=right_color,
                    linestyle=right_linestyle,
                    linewidth=right_linewidth,
                    marker=right_marker,
                    label=right_y_label,
                )
                ax2.set_ylabel(right_y_label, color=right_color, fontsize=14, fontweight="bold")
                ax2.tick_params(axis="y", labelcolor=right_color)

            # Format x-axis
            if has_left_data or has_right_data:
                # Get the data range for crisis overlays
                all_dates = []
                if has_left_data:
                    all_dates.extend(df_left.index.tolist())
                if has_right_data:
                    all_dates.extend(df_right.index.tolist())

                if all_dates:
                    date_range = (min(all_dates), max(all_dates))

                    # Add crisis overlays
                    crisis_patches = []
                    if show_crisis_periods:
                        crisis_patches = self.add_crisis_overlays(ax1, date_range, add_legend=False)

                    # Format dates
                    if graph_type == "M":
                        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=interval))
                        ax1.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
                    elif graph_type == "Q":
                        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3 * interval))
                        ax1.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
                    elif graph_type == "Y":
                        ax1.xaxis.set_major_locator(mdates.YearLocator(interval=interval))
                        ax1.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
                    else:  # Daily
                        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=interval))
                        ax1.xaxis.set_major_formatter(mdates.DateFormatter(date_format))

            # Add right axis zero line if requested
            if right_axis_zero_line and has_right_data:
                ax2.axhline(y=0, color=right_color, linestyle="-", alpha=0.3)

            # Add bar chart if provided
            if bar_data_dict and len(bar_data_dict) > 0:
                # Prepare bar data
                df_bar = pd.DataFrame(list(bar_data_dict.items()), columns=["date", "value"])
                df_bar["date"] = pd.to_datetime(df_bar["date"], format="%Y-%m-%d", errors="coerce")
                df_bar = df_bar.dropna(subset=["date"])
                df_bar = df_bar.sort_values("date")
                df_bar.set_index("date", inplace=True)

                # Resample if requested (same as other data)
                if resample_freq:
                    if resample_freq == "M":
                        df_bar = df_bar.resample("ME").mean()  # Use mean for bar data
                    elif resample_freq == "Q":
                        df_bar = df_bar.resample("QE").mean()
                    elif resample_freq == "Y":
                        df_bar = df_bar.resample("YE").mean()

                # Calculate bar positioning
                if has_left_data:
                    left_values = df_left["value"].values
                    bar_bottom = min(left_values) * bar_position_ratio
                    bar_height_scale = (max(left_values) - min(left_values)) * bar_height_ratio
                else:
                    # Fallback positioning if no left axis data
                    bar_bottom = 0
                    bar_height_scale = max(df_bar["value"].values) * bar_height_ratio

                # Normalize and position bars
                if len(df_bar) > 0 and not df_bar["value"].isna().all():
                    max_bar_value = df_bar["value"].max()
                    min_bar_value = df_bar["value"].min()

                    if max_bar_value > 0:
                        normalized_bars = (df_bar["value"] / max_bar_value) * bar_height_scale
                        bar_legend_label = (
                            f"{bar_label} (Min: {int(min_bar_value)}, Max: {int(max_bar_value)})"
                        )

                        bars = ax1.bar(
                            df_bar.index,
                            normalized_bars,
                            bottom=bar_bottom,
                            color=bar_color,
                            alpha=bar_alpha,
                            width=bar_width,
                            label=bar_legend_label,
                            zorder=1,  # Behind lines but above grid
                        )
                    else:
                        bar_legend_label = f"{bar_label} (No data)"
                else:
                    bar_legend_label = f"{bar_label} (No data)"

            # Set title
            if title:
                ax1.set_title(title, fontsize=16, fontweight="bold", pad=20)

            # Create main legend for data (left side)
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            if lines1 or lines2:
                ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=12)

            # Create separate crisis legend (right side) if we have crisis overlays
            if show_crisis_periods and "crisis_patches" in locals() and crisis_patches:
                import matplotlib.patches as mpatches

                crisis_handles = []
                crisis_labels = []

                for crisis_info in crisis_patches:
                    # Create a patch for the legend
                    legend_patch = mpatches.Patch(
                        color=crisis_info["color"],
                        alpha=0.5,  # Slightly more opaque for legend visibility
                        label=crisis_info["name"],
                    )
                    crisis_handles.append(legend_patch)
                    crisis_labels.append(crisis_info["name"])

                if crisis_handles:
                    # Add crisis legend in upper right corner
                    crisis_legend = ax1.legend(
                        crisis_handles,
                        crisis_labels,
                        loc="upper right",
                        fontsize=10,
                        title="Financial Events",
                        title_fontsize=11,
                        framealpha=0.8,
                    )
                    # Add the main legend back (since ax1.legend overwrites the previous one)
                    if lines1 or lines2:
                        main_legend = ax1.legend(
                            lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=12
                        )
                        ax1.add_artist(main_legend)  # Keep both legends

            # Format dates on x-axis
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha="right")

            # Add grid
            ax1.grid(True, alpha=0.3)

            plt.tight_layout()

            buffer = BytesIO()
            fig.savefig(buffer, format="png", dpi=self.dpi, bbox_inches="tight")
            buffer.seek(0)
            plt.close()

            return buffer

        except Exception as e:
            plt.close()
            # Create a simple error chart instead of returning text
            fig, ax = plt.subplots(figsize=figsize)
            ax.text(
                0.5,
                0.5,
                f"Error creating chart: {str(e)}",
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=12,
            )
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")

            buffer = BytesIO()
            fig.savefig(buffer, format="png", dpi=self.dpi, bbox_inches="tight")
            buffer.seek(0)
            plt.close()
            return buffer

    def create_formatted_list(self, data_dict, title):
        """Create a formatted list from dictionary data with title"""
        content = []

        # Add title
        title_paragraph = Paragraph(title, self.custom_styles.create_list_style())
        content.append(title_paragraph)
        content.append(Spacer(1, 10))

        # Create formatted list items
        for key, value in data_dict.items():
            # Format the key - capitalize and replace underscores with spaces
            formatted_key = key.replace("_", " ").title()

            # Special formatting for portfolio configuration
            if isinstance(value, list) and len(value) == 0:
                formatted_value = "None"
            elif isinstance(value, list) and all(isinstance(item, Enum) for item in value):
                formatted_value = ", ".join([vv.value for vv in value])
            elif isinstance(value, list):
                formatted_value = ", ".join(str(v) for v in value) if value else "None"
            elif key == "allow_short":
                formatted_value = "Not allowed" if not value else "Allowed"
            elif key in ["min_market_cap", "max_market_cap", "initial_capital"]:
                if key == "max_market_cap" and value == np.inf:
                    formatted_value = "Uncapped"
                elif value is not None and isinstance(value, (int, float)):
                    formatted_value = f"${value:,.0f}"
                else:
                    formatted_value = "None"
            elif isinstance(value, (int, float)) and key not in [
                "initial_capital",
                "min_market_cap",
                "max_market_cap",
                "Overall Sharpe Ratio",
            ]:
                formatted_value = f"{value:.2%}"
            elif isinstance(value, (int, float)):
                formatted_value = f"{value:,.2f}"
            else:
                formatted_value = str(value)

            # Create paragraph with bolded key
            list_item_style = ParagraphStyle(
                "ListItem",
                parent=self.custom_styles.create_normal_style(),
                fontName="Helvetica",
                fontSize=11,
                spaceAfter=5,
                spaceBefore=2,
                leftIndent=0,
                bulletIndent=0,
                alignment=TA_LEFT,
            )

            item_text = f"<b>{formatted_key}:</b> {formatted_value}"
            item_paragraph = Paragraph(item_text, list_item_style)
            content.append(item_paragraph)

        return content


class StyleUtility:
    """Utility class for creating consistent paragraph and table styles across reports"""

    def __init__(self):
        self.styles = getSampleStyleSheet()

    def create_title_page_title_style(self):
        """Create style for title page titles"""
        return ParagraphStyle(
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

    def create_section_title_style(self):
        """Create style for section titles"""
        return ParagraphStyle(
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

    def create_list_style(self):
        """Create style for list items"""
        return ParagraphStyle(
            "List",
            parent=self.styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=14,
            spaceAfter=10,
            spaceBefore=15,
            textColor=Colors.SLATE_BLUE,
            alignment=TA_CENTER,
            leading=16,
        )

    def create_normal_style(self):
        """Create custom normal style"""
        return ParagraphStyle(
            "CustomNormal",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            spaceAfter=8,
            textColor=Colors.CHARCOAL,
            leading=14,
            alignment=TA_JUSTIFY,
        )

    def create_footer_info_style(self):
        """Create portfolio info style for headers"""
        return ParagraphStyle(
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

    def create_section_header_style(self):
        """Create section header style"""
        return ParagraphStyle(
            "SectionHeader",
            parent=self.styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=14,
            spaceAfter=-3,
            spaceBefore=5,
            textColor=Colors.NAVY_BLUE,
            alignment=TA_LEFT,
            leading=16,
        )

    def create_base_table_title_style(self):
        """Create base table title style (centered, more spacing) - no color set here"""
        return ParagraphStyle(
            "BaseTableTitle",
            parent=self.styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=16,
            spaceAfter=10,
            spaceBefore=15,
            alignment=TA_CENTER,  # Center table titles
            leading=18,
        )

    def create_divider_table_style(self):
        """Create divider table style"""
        return TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -1), 1.5, Colors.NAVY_BLUE),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),  # Keep minimal for tight line
                ("TOPPADDING", (0, 0), (-1, -1), -5),  # Small negative to bring line close to title
            ]
        )
