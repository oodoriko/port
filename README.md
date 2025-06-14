Check out example notebook.
Cache data first.

Assumptions:

1. trades are executed at current date's open price at T-0
2. no partial execution
3. no price impact
4. rf = .02 bmk=.1

TODO: 0. graph y-axis

1. the negative trading signal doesn't make sense...
1. move data processing out of report
1. optimizing strategy calculation using more vectorization/online
1. check strategy filter logic
1. check trade accuracy

maybe:

1. logger
2. immutable class for portfolio
3. data chunking for backtesting
4. complete vectorization: no pandas, NdArray keyed by date, columned by ticker
