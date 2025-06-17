from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, Spacer, Table, TableStyle

from reporting.report import SimpleReportGenerator
from reporting.report_styling import Colors


class ReportGenerator(SimpleReportGenerator):
    def __init__(self, portfolio_analytics, dpi):
        super().__init__(portfolio_analytics, dpi)

    def get_report_template(self):
        return super().generate_report_template()

    def add_title_page(self, story):
        title_page = self.create_title_page()
        story.extend(title_page)
        story.append(PageBreak())

    def add_session_page(self, story, title):
        session_title_page = self.create_section_title_page(title)
        story.extend(session_title_page)
        story.append(PageBreak())

    def add_portfolio_info(self, story, title):
        self.add_page_header(story, section_name=title)
        overview_page = self.create_portfolio_overview_page_config_and_metrics()
        story.extend(overview_page)
        story.append(PageBreak())

    def add_portfolio_performance(self, story, title):
        self.add_page_header(story, section_name=title)
        chart = self.create_portfolio_overview_page_performance()
        story.append(Image(chart, width=10 * inch, height=6 * inch))
        story.append(PageBreak())

    def add_return_distribution(self, story, title):
        self.add_page_header(story, section_name=title)
        distribution_chart = self.create_monthly_return_distribution_chart()
        story.append(Image(distribution_chart, width=10 * inch, height=6 * inch))
        story.append(PageBreak())

    def add_return_sharpe_ir(self, story, title):
        self.add_page_header(story, section_name=title)
        sharpe_ir_chart = self.create_monthly_sharpe_ir_chart()
        story.append(Image(sharpe_ir_chart, width=10 * inch, height=6 * inch))
        story.append(PageBreak())

    def add_return_topn(self, story, title):
        self.add_page_header(story, section_name=title)
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

    def add_holding_summary(self, story, title):
        self.add_page_header(story, section_name=title)

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

    def add_holding_ts(self, story, title):
        self.add_page_header(story, section_name=title)
        holdings_chart = self.create_holdings_analysis_chart()
        story.append(Image(holdings_chart, width=10 * inch, height=6 * inch))
        story.append(PageBreak())

    def add_holding_topn(self, story, title):
        self.add_page_header(story, section_name=title)

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

    def add_trading_summary(self, story, title):
        self.add_page_header(story, section_name=title)
        trading_summary_table = self.create_trading_analysis_summary_table()
        story.append(trading_summary_table)
        story.append(PageBreak())

    def add_trading_ts(self, story, title):
        self.add_page_header(story, section_name=title)
        trading_activity_chart = self.create_trading_activity_chart(graph_type="D")
        story.append(Image(trading_activity_chart, width=10 * inch, height=6.4 * inch))
        story.append(PageBreak())

    def add_trading_topn(self, story, title):
        self.add_page_header(story, section_name=title)
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

    def add_cashflow_ts(self, story, title):
        self.add_page_header(story, section_name=title)
        cashflow_chart = self.create_cashflow_over_time_chart(graph_type="D")
        story.append(Image(cashflow_chart, width=10 * inch, height=6.4 * inch))
        story.append(PageBreak())

    def add_pnl_ts(self, story, title):
        self.add_page_header(story, section_name=title)
        pnl_chart = self.create_pnl_over_time_chart(graph_type="D")
        story.append(Image(pnl_chart, width=10 * inch, height=6.4 * inch))
        story.append(PageBreak())

    def add_sector_ts(self, story, title):
        self.add_page_header(story, section_name=title)
        sector_exposure_chart = self.create_sector_exposure_chart()
        story.append(Image(sector_exposure_chart, width=10 * inch, height=6 * inch))
        story.append(PageBreak())

    def add_sector_composition(self, story, title):
        self.add_page_header(story, section_name=title)
        sector_composition_chart = self.create_sector_composition_pie()
        story.append(Image(sector_composition_chart, width=8 * inch, height=6 * inch))
        story.append(PageBreak())

    def add_sector_duration(self, story, title):
        self.add_page_header(story, section_name=title)
        sector_duration_chart = self.create_sector_duration_boxplot()
        story.append(Image(sector_duration_chart, width=10 * inch, height=6 * inch))
        story.append(PageBreak())

    def add_sector_return(self, story, title):
        self.add_page_header(story, section_name=title)
        sector_return_chart = self.create_sector_return_boxplot()
        story.append(Image(sector_return_chart, width=10 * inch, height=6 * inch))
        story.append(PageBreak())

    def add_sector_duration_return(self, story, title):
        self.add_page_header(story, section_name=title)
        return_duration_scatter = self.create_return_duration_scatter()
        story.append(Image(return_duration_scatter, width=10 * inch, height=6 * inch))
        story.append(PageBreak())

    def add_capital_contribution_analysis(self, story, title):
        self.add_page_header(story, section_name=title)
        capital_table = self.create_capital_contribution_table()

        story.append(capital_table)
        story.append(PageBreak())

    def add_trading_contribution_analysis(self, story, title):
        self.add_page_header(story, section_name=title)
        trading_table = self.create_trading_contribution_table()
        story.append(trading_table)
        story.append(PageBreak())

    def generate_report_template(self):
        story = []

        self.add_title_page(story)

        self.add_session_page(story, "Portfolio Overview")
        self.add_portfolio_info(story, "Portfolio Setup & Key Metrics")
        self.add_portfolio_performance(story, "Portfolio Performance")

        self.add_session_page(story, "Return Analysis")
        self.add_return_distribution(story, "Return Analysis - Return Distribution")
        self.add_return_sharpe_ir(story, "Return Analysis - Sharpe & IR")
        self.add_return_topn(story, "Return Analysis - Top Returns")

        self.add_session_page(story, "Contribution Analysis")
        self.add_capital_contribution_analysis(
            story, "Contribution Analysis - Capital Contribution"
        )
        self.add_trading_contribution_analysis(
            story, "Contribution Analysis - Trading Contribution"
        )

        self.add_session_page(story, "Trading Analysis")
        self.add_trading_summary(story, "Trading Analysis - Trading Summary")
        self.add_trading_ts(story, "Trading Analysis - Trading Activity")
        self.add_trading_topn(story, "Trading Analysis - Top Traded")

        self.add_session_page(story, "Cashflow Analysis")
        self.add_cashflow_ts(story, "Cashflow Analysis - Cashflow Over Time")
        self.add_pnl_ts(story, "Cashflow Analysis - PnL Over Time")

        self.add_session_page(story, "Holdings Analysis")
        self.add_holding_summary(story, "Holdings Analysis - Holdings Summary")
        self.add_holding_ts(story, "Holdings Analysis - Holdings Over Time")
        self.add_holding_topn(story, "Holdings Analysis - Top Holdings")

        self.add_session_page(story, "Sector Analysis")
        self.add_sector_ts(story, "Sector Analysis - Sector Exposure")
        self.add_sector_composition(story, "Sector Analysis - Sector Composition")
        self.add_sector_duration(story, "Sector Analysis - Sector Duration")
        self.add_sector_return(story, "Sector Analysis - Sector Return")
        self.add_sector_duration_return(story, "Sector Analysis - Duration vs Return")

        return story

    def generate_report(self, filename=None) -> str:
        story = self.generate_report_template()
        return super().generate_report(filename=filename, story=story)
