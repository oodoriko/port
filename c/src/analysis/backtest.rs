use crate::core::params::{
    PortfolioConstraintParams, PortfolioParams, PositionConstraintParams, SignalParams,
};
use crate::data::data::InfluxDBHandler;
use crate::trading::portfolio::Portfolio;
use crate::trading::strategy::Strategy;
use chrono::{DateTime, Utc};

#[inline(always)]
pub async fn backtest(
    strategy_name: String,
    portfolio_name: String,
    start: DateTime<Utc>,
    end: DateTime<Utc>,
    tickers: Vec<String>,
    strategies: Vec<Vec<SignalParams>>,
    portfolio_params: PortfolioParams,
    portfolio_constraints_params: PortfolioConstraintParams,
    position_constraints_params: Vec<PositionConstraintParams>,
    warm_up_period: usize,
    cadence: u64, // in minutes
) -> Result<Portfolio, Box<dyn std::error::Error>> {
    let handler = InfluxDBHandler::new()?;

    let ticker_refs: Vec<&str> = tickers.iter().map(|s| s.as_str()).collect();
    let (data, timestamps) = handler.load_data(&ticker_refs, start, end).await?;

    let warm_up_price_data: Vec<Vec<Vec<f32>>> = data[..warm_up_period].to_vec();

    let mut strategy = Strategy::new(
        &strategy_name,
        &portfolio_name,
        portfolio_params,
        portfolio_constraints_params,
        position_constraints_params,
        &strategies,
    );

    let mut portfolio = strategy.create_portfolio();
    let mut constraint = strategy.create_constraints();
    constraint.set_cadence(cadence * 60);
    strategy.warm_up_signals(&warm_up_price_data);

    let n_assets = tickers.len();
    let mut close_prices = Vec::with_capacity(n_assets);
    let mut open_prices = Vec::with_capacity(n_assets);
    let mut signals_adjusted = Vec::with_capacity(n_assets);

    let data_len = data.len();
    let mut exit = false;

    for idx in warm_up_period..data_len {
        let time = timestamps[idx];
        let mut available_cash = *portfolio.cash_curve.last().unwrap();
        let mut total_cost = 0.0;
        let mut total_realized_pnl = 0.0;

        // Fast price extraction using unsafe for bounds check elimination?? what is this?
        close_prices.clear();
        open_prices.clear();

        unsafe {
            let prev_data = data.get_unchecked(idx - 1);
            for asset_ohlcv in prev_data {
                close_prices.push(*asset_ohlcv.get_unchecked(3)); // close
                open_prices.push(*asset_ohlcv.get_unchecked(0)); // open
            }
        }

        if exit {
            let mut liquidation_trades = portfolio.trading_history.last().unwrap().clone();
            portfolio.liquidation(&close_prices, &mut liquidation_trades, time as u64);
            println!("江南皮革厂倒闭啦！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！");
            break;
        }

        portfolio.pre_order_update(&data[idx]);
        let (is_exit, risk_trades) = constraint.pre_order_check(
            &close_prices,
            &portfolio.positions,
            *portfolio.equity_curve.last().unwrap(),
            time as u64,
        );

        if is_exit {
            exit = true;
            portfolio.post_order_update(
                &close_prices,
                &Vec::new(),
                &risk_trades,
                available_cash,
                total_cost,
                total_realized_pnl,
            );
            continue;
        }

        // generate signal use t-1 close
        strategy.update_signals(data[idx - 1].clone());
        let signals = strategy.generate_signals();

        signals_adjusted.clear();
        signals_adjusted.extend_from_slice(&signals);

        for trade in &risk_trades {
            // hold off trading ticker in risk trades
            if trade.ticker_id < signals_adjusted.len() {
                signals_adjusted[trade.ticker_id] = 0;
            }
        }

        // execute t-2 trades using t-1 open at t0 because t-1 is the latest price we can get
        let trading_history_len = portfolio.trading_history.len();
        if trading_history_len >= 2 {
            let mut prev_trades = portfolio.trading_history[trading_history_len - 2].clone();
            if !prev_trades.is_empty() {
                (available_cash, total_cost, total_realized_pnl) =
                    portfolio.execute_trades(&mut prev_trades, &open_prices, time as u64);
            }
        }

        portfolio.update_capital(time);

        let mut trades = constraint.generate_trades(
            &signals_adjusted,
            &close_prices,
            *portfolio.equity_curve.last().unwrap(),
            available_cash,
            time as u64,
            &portfolio.positions,
        );
        trades.extend(risk_trades);

        let prev_trades = if trading_history_len >= 2 {
            portfolio.trading_history[trading_history_len - 2].clone()
        } else {
            Vec::new()
        };

        portfolio.post_order_update(
            &close_prices,
            &prev_trades,
            &trades,
            available_cash,
            total_cost,
            total_realized_pnl,
        );
    }

    Ok(portfolio)
}

#[inline(always)]
pub fn backtest_result(portfolio: Portfolio) {
    println!("=== BACKTEST RESULTS ===\n");

    println!("📊 Portfolio: {}", portfolio.name);
    let equity_len = portfolio.equity_curve.len();
    println!("📈 Total Records: {}", equity_len);

    if equity_len == 0 {
        println!("❌ No data to display");
        return;
    }

    let initial_value = portfolio.equity_curve[0];
    let final_value = portfolio.equity_curve[equity_len - 1];

    let (min_equity, max_equity) = portfolio
        .equity_curve
        .iter()
        .fold((f32::INFINITY, f32::NEG_INFINITY), |(min, max), &val| {
            (min.min(val), max.max(val))
        });

    let total_return = (final_value - initial_value) / initial_value * 100.0;

    println!("\n💰 PERFORMANCE SUMMARY:");
    println!("  Initial Value: ${:.2}", initial_value);
    println!("  Final Value:   ${:.2}", final_value);
    println!("  Total Return:  {:.2}%", total_return);
    println!("  Max Value:     ${:.2}", max_equity);
    println!("  Min Value:     ${:.2}", min_equity);
    println!("  Peak Notional: ${:.2}", portfolio.peak_notional);

    println!("\n=== END BACKTEST RESULTS ===");
}
