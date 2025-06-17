gs level:

- indicator generation level: parameters
- strategy level: different combo of strategy (pos and neg signal)
- portfolio level: loss control, capital injection, trading/rebalance threshold
  static(should base on appetite): - cost multiple (market impact + fixed) - ?
  orders: everything in batch

1. indicator generation
   -> pd, preferably np vectorization + talib
   -> make parameters easily parametrizable
2. signal generation
   -> strategy rules
   -> voting rules
   ------output is an NdArray (T _ n _ p), T - date, n - ticker, p - indicator----
3. lightweight data cacher - just cache a big chunk of price data and move on
   -----output is also NdArray ( T _ n _ p), p-prices or volume
4. can i batch trade? i think i can...
   - steps in trading: market to mkt, check max drawdown, update trail stop price, check stop loss, trade sell, trade buy, market to mkt
   - we need a lot of numpy arrays.... check what xx does

record keeping during trading is important... think through this
