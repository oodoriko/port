# Portfolio Construction Notes

## Portfolio Value Calculation

Portfolio value = Sigma((new weight - current weight) \* curr_portfolio_value) -> ideally

## Architecture Overview

- The portfolio has a list of initial holdings
- The holders are given a weight based on the setup constraints
- Then initial capital is allocated to the initial holdings based on weights
- Next we select a benchmark and get the watch list from the benchmark
- The watch list the bmk filtered by the setup constraints

## Strategy Framework

We will have a list of strategies, each strategy has one or more indicators
For each day, we generate a buy or sell signal for each ticker in the watch list and in the portfolio
Given the signal, we generate trading plan based on the constraints

## Trading Plan Implementation

Trading plan is basically a list of weights for each ticker in the watch list and in the portfolio, positive
weight is to buy more i.e. buy shares = (new weight - current weight) \* portfolio value / share price
This plan can be very tricky to implement given the constraints.

To trade on the trading plan, we use next day's open price
We will apply a multiplier to the trading plan to account for transaction cost of any sorts
We then calculate the end of day portfolio value after trading

## Code Flow

```python
portfolio = Portfolio()
strategy = Strategy()
constraints = Constraints()
trades = Trades()
for date in dates:
    # every function returns ths same length array = holdings + watch list
    strategy = strategy.get_signal((holdings + watch list).historical_prices)    -> [Buy, sell, hold]
    strategy.archive(strategy)
    trade_plan = constraints.get_trade_plan(strategy, (holdings + watch list).product_data) -> [w1, w2, w3, ...]
    trades.archive(trade_plan)

    portfolio.trade(trades plan) -> update holding list, update portfolio value
```

Finally we can report the performance of the portfolio
Pick a few metrics and plot

## Development Scenarios

### Scenario 1: I only have two brain cells

1. no initial holdings
2. no constraints (buy all or sell all) & unlimited capital
3. no rebalancing
4. no new capital
5. no slippage
6. another brain cell for including transaction cost (WHAT ABOUT THE SPREAD!?)
7. one brain cell for including ONE trading strategy (single indicator)

### Scenario 2: Rousseau wrote "Man is born free and everywhere he is in chains"

I am thus a slave to my constraints, but I still only have two brain cells

1. no initial holdings
2. ONE constraint on sector exposure
3. no rebalancing
4. no new capital
5. no slippage
6. one brain cell for including trading cost
7. one brain cell for including ONE trading strategy (single indicator)

### Scenario 3: I might have grown a brain at this point

1. no initial holdings
2. MANY constraints (mixed signals, etc.)
3. no rebalancing
4. no new capital
5. no slippage
6. one brain cell for including trading cost
7. one brain cell for including ONE trading strategy (single indicator)

### Scenario 4: Should've lost interest in this project by now

1. initial holdings
2. MANY constraints (tokuni, cash%, dynamic allocation, etc.)
3. target weights for each ticker
4. no rebalancing
5. new capital
6. no slippage
7. one brain cell for including trading cost
8. one brain cell for including ONE trading strategy (single indicator)
