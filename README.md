CACHE SOME DATA FIRST

# Portfolio Construction

## Backtest

A backtest consists of:

- **Strategies**: Trading or investment strategies to evaluate
- **Date Range**: Time period for the backtest
- **Portfolio**: The portfolio configuration to test

## Portfolio

A portfolio is defined by:

### Core Components

- **Tickers**: Usually a subset of the benchmark universe
- **Ticker Data**: Product and price data for selected securities
- **Constraints**: Investment rules and limitations
- **Capital**: Available investment capital

### Additional Features

- Analytics capabilities for performance evaluation
- Trading history caching for efficiency

TODO:

1. A cost model dependent on prev day volume -> done
2. Shares -> done
3. add capital, fracitional shares (divide capital across shares) -> DONE
4. FIX GRAPH STYLING -> DONE
5. SET UP GRID SEARCH ->DONE
6. SET UP GRID SESARH REP -> DONE
7. REFACTOR FOR CLARITY - CURRENTLY TOO NESTED -> done

8. optimizing strategy calculation, more vectorization and try online [P3]
9. generate more data for analytics so that no data is process in report.py [P2]
10. make date easier to access [P1]
11. CHECK ACCRUACY
12. - VOTING/SUMMING ALGO
    - METRICS CALCULATION
13. RUN REAL GS
14. WRITE DOCS FOR EVERYTHING

maybe:

1. logger
2. immutable class for potfolio
3. data chunking for backtesting
