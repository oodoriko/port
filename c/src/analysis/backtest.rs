use crate::core::params::{
    PortfolioConstraintParams, PortfolioParams, PositionConstraintParams, SignalParams,
};
use crate::data::database_service;
use crate::trading::portfolio::Portfolio;
use crate::trading::strategy::Strategy;
use crate::trading::trade::TradeType;
use chrono::{DateTime, Utc};
use port_etl::InfluxDBHandler;

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
    debug: bool,
) -> Result<
    (
        Portfolio,
        std::collections::HashMap<i64, Vec<crate::trading::trade::Trade>>,
        bool,
    ),
    Box<dyn std::error::Error>,
> {
    let mut early_exit = false;

    let (data, timestamps) = get_data(tickers.clone(), start, end, debug, cadence).await?;
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
    let mut prev_close_prices = Vec::with_capacity(n_assets);
    let mut prev_open_prices = Vec::with_capacity(n_assets);
    let mut curr_open_prices = Vec::with_capacity(n_assets);

    // Track executed trades by date - key: timestamp, value: executed trades
    let mut executed_trades_by_date = std::collections::HashMap::new();

    let data_len = data.len();

    println!("Start backtesting...");
    println!("start: {:?}", start);
    println!("end: {:?}", end);

    for idx in warm_up_period..data_len {
        // Ensure we don't exceed timestamps array bounds
        if idx >= timestamps.len() {
            println!("Warning: Reached end of timestamp data at index {}", idx);
            break;
        }
        let time = timestamps[idx];
        let mut cash_after_trades = portfolio.get_current_cash();
        let mut total_cost = 0.0;
        let mut total_realized_pnl = 0.0;

        // Fast price extraction using unsafe for bounds check elimination
        prev_close_prices.clear();
        prev_open_prices.clear();
        curr_open_prices.clear();

        unsafe {
            let prev_data = data.get_unchecked(idx - 1);
            for asset_ohlcv in prev_data {
                prev_close_prices.push(*asset_ohlcv.get_unchecked(3)); // close
                prev_open_prices.push(*asset_ohlcv.get_unchecked(0)); // open
            }
            let curr_data = data.get_unchecked(idx);
            for asset_ohlcv in curr_data {
                curr_open_prices.push(*asset_ohlcv.get_unchecked(0)); // open
            }
        }

        // update position with t-1 close
        portfolio.pre_order_update(&prev_close_prices);

        // pre order check: mark portfolio at t-1 close, check take profit, stop loss, max drawdown
        let (is_exit, mut risk_management_trades, take_profit_trades) = constraint.pre_order_check(
            &prev_close_prices,
            &portfolio.positions,
            portfolio.peak_equity,
            portfolio.get_current_cash(),
            time as u64,
        );

        if is_exit {
            portfolio.liquidation(&curr_open_prices, &mut risk_management_trades, time as u64);
            executed_trades_by_date.insert(time, risk_management_trades);
            println!("江南皮革厂倒闭啦！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！");
            early_exit = true;
            break;
        }

        // update signals with t-1 close
        strategy.update_signals(data[idx - 1].clone());
        let signals = strategy.generate_signals();

        // pick out the ticker id of stop loss triggered positions
        let stop_loss_triggered_pos = risk_management_trades
            .iter()
            .filter(|t| t.trade_type == TradeType::StopLoss)
            .map(|t| t.ticker_id)
            .collect::<Vec<_>>();

        // first execute pre signal trades using current t0 open prices (bypassing the backtest logic where t0 is na until t+1
        let mut total_executed_trades = Vec::new();
        risk_management_trades.extend(take_profit_trades);
        if risk_management_trades.len() > 0 {
            let (
                new_cash_after_trades,
                new_total_cost,
                new_total_realized_pnl,
                new_executed_trades,
            ) = portfolio.execute_trades(
                &mut risk_management_trades,
                &curr_open_prices,
                time as u64,
                &[],
            );
            cash_after_trades += new_cash_after_trades;
            total_cost += new_total_cost;
            total_realized_pnl += new_total_realized_pnl;
            total_executed_trades.extend(new_executed_trades);
        }

        // then execute previous trades using t-1 close prices
        let mut pending_trades = portfolio.pending_trades.clone(); // previous period trades
        if !pending_trades.is_empty() {
            let (
                new_cash_after_trades,
                new_total_cost,
                new_total_realized_pnl,
                new_executed_trades,
            ) = portfolio.execute_trades(
                &mut pending_trades,
                &prev_close_prices,
                time as u64,
                &stop_loss_triggered_pos,
            );
            cash_after_trades += new_cash_after_trades;
            total_cost += new_total_cost;
            total_realized_pnl += new_total_realized_pnl;
            total_executed_trades.extend(new_executed_trades);
        }
        if total_executed_trades.len() > 0 {
            executed_trades_by_date.insert(time, total_executed_trades);
        }

        // handle cash distribution event, being conservative here, t0 cash is not available for trading
        let available_cash = cash_after_trades + portfolio.get_new_cash(time);

        // generate signal based trades after trades and capital distribution
        let new_signal_based_trades = constraint.generate_trades(
            &signals,
            &prev_close_prices,
            portfolio.get_current_equity(),
            available_cash,
            time as u64,
            &portfolio.positions,
        );

        portfolio.pending_trades = new_signal_based_trades;

        // mark portfolio at t-1 close (NEED TO THINK ABOUT THIS AGAIN)
        portfolio.post_order_update(
            &prev_close_prices,
            available_cash,
            total_cost,
            total_realized_pnl,
        );
    }

    println!("Backtesting completed");
    if early_exit {
        println!("Early exit due to max drawdown");
    }

    // Timestamps are now recorded during post_order_update to match curve data points
    // portfolio.timestamps already contains the correct timestamps

    println!("Total trade executions: {}", executed_trades_by_date.len());
    println!("Total time periods: {}", data_len - warm_up_period);
    println!(
        "Trade execution rate: {:.2}%",
        (executed_trades_by_date.len() as f64 / (data_len - warm_up_period) as f64) * 100.0
    );

    Ok((portfolio, executed_trades_by_date, early_exit))
}

async fn get_data(
    tickers: Vec<String>,
    start: DateTime<Utc>,
    end: DateTime<Utc>,
    debug: bool,
    cadence: u64,
) -> Result<(Vec<Vec<Vec<f32>>>, Vec<i64>), Box<dyn std::error::Error>> {
    let (data, timestamps) = if debug {
        // Use InfluxDB for debug mode
        let handler = InfluxDBHandler::new()?;
        let ticker_refs: Vec<&str> = tickers.iter().map(|s| s.as_str()).collect();
        handler
            .load_ohlcv_data(&ticker_refs, start, end, Some(cadence))
            .await?
    } else {
        // Use database service for production mode
        let historical_data = database_service::get_historical_data(start, end, tickers.clone())
            .await
            .map_err(|e| -> Box<dyn std::error::Error> { e })?;

        // Convert database service data to the format expected by the backtest
        let mut converted_data = Vec::new();
        let mut converted_timestamps = Vec::new();

        // Find the minimum length among all tickers to prevent index out of bounds
        let min_data_len = historical_data
            .values()
            .map(|data| data.len())
            .min()
            .unwrap_or(0);

        if min_data_len > 0 {
            for i in 0..min_data_len {
                let mut time_point_data = Vec::new();
                let mut timestamp = 0i64;

                for ticker in &tickers {
                    if let Some(ticker_data) = historical_data.get(ticker) {
                        // Additional safety check to prevent panic
                        if i < ticker_data.len() {
                            let ohlcv = &ticker_data[i];
                            time_point_data.push(vec![
                                ohlcv.open,
                                ohlcv.high,
                                ohlcv.low,
                                ohlcv.close,
                                ohlcv.volume,
                            ]);
                            timestamp = ohlcv.timestamp;
                        }
                    }
                }

                // Only add data if we have data for all tickers at this time point
                if time_point_data.len() == tickers.len() {
                    converted_data.push(time_point_data);
                    converted_timestamps.push(timestamp);
                }
            }
        }

        (converted_data, converted_timestamps)
    };
    Ok((data, timestamps))
}

#[inline(always)]
pub fn backtest_result(
    portfolio: &Portfolio,
    executed_trades_by_date: &std::collections::HashMap<i64, Vec<crate::trading::trade::Trade>>,
    exited_early: bool,
) {
    println!("=== BACKTEST RESULTS ===\n");
    if exited_early {
        println!("Early exit due to max drawdown");
    }
    println!("📊 Portfolio: {}", portfolio.name);
    let equity_len = portfolio.equity_curve.len();
    println!("📈 Total Records: {}", equity_len);
    println!("📅 Trade Events: {}", executed_trades_by_date.len());

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
    println!("  Peak Equity: ${:.2}", portfolio.peak_equity);

    // Show trade timing information
    if !executed_trades_by_date.is_empty() {
        let first_trade_time = executed_trades_by_date.keys().min().unwrap();
        let last_trade_time = executed_trades_by_date.keys().max().unwrap();

        println!("\n📊 TRADING ACTIVITY:");
        println!(
            "  First Trade: {}",
            chrono::DateTime::from_timestamp(*first_trade_time, 0)
                .unwrap_or_default()
                .format("%Y-%m-%d %H:%M:%S")
        );
        println!(
            "  Last Trade:  {}",
            chrono::DateTime::from_timestamp(*last_trade_time, 0)
                .unwrap_or_default()
                .format("%Y-%m-%d %H:%M:%S")
        );
        println!("  Total Trade Events: {}", executed_trades_by_date.len());

        // Calculate average time between trades
        if executed_trades_by_date.len() > 1 {
            let total_duration = last_trade_time - first_trade_time;
            let avg_time_between_trades =
                total_duration as f64 / (executed_trades_by_date.len() - 1) as f64;
            println!(
                "  Avg Time Between Trades: {:.1} seconds",
                avg_time_between_trades
            );
        }
    }

    // Show detailed trade information
    if !executed_trades_by_date.is_empty() {
        println!("\n📋 DETAILED TRADE HISTORY:");

        let mut sorted_dates: Vec<_> = executed_trades_by_date.keys().collect();
        sorted_dates.sort();

        for &timestamp in sorted_dates {
            let trades = &executed_trades_by_date[&timestamp];
            let date_str = chrono::DateTime::from_timestamp(timestamp, 0)
                .unwrap_or_default()
                .format("%Y-%m-%d %H:%M:%S");

            println!("\n  📅 {}", date_str);
            println!("     {} trades executed:", trades.len());

            for (i, trade) in trades.iter().enumerate() {
                let action = format!("{:?}", trade.trade_type);
                println!(
                    "       {}. {} | Ticker ID: {} | Quantity: {:.2} | Price: ${:.4} | Cost: ${:.2} | Realized PNL: ${:.2}",
                    i + 1,
                    action,
                    trade.ticker_id,
                    trade.quantity,
                    trade.price,
                    trade.cost,
                    trade.realized_pnl,
                );
                if let Some(comment) = &trade.trade_comment {
                    println!("          Comment: {}", comment);
                }
            }

            // Calculate total value traded on this day
            let total_value: f32 = trades.iter().map(|t| t.quantity * t.price).sum();
            let total_cost: f32 = trades.iter().map(|t| t.cost).sum();

            println!(
                "       📊 Day Total: ${:.2} traded, ${:.2} in costs",
                total_value, total_cost
            );
        }

        // Overall trade statistics
        let total_trades: usize = executed_trades_by_date
            .values()
            .map(|trades| trades.len())
            .sum();
        let total_volume: f32 = executed_trades_by_date
            .values()
            .flatten()
            .map(|t| t.quantity * t.price)
            .sum();
        let total_costs: f32 = executed_trades_by_date
            .values()
            .flatten()
            .map(|t| t.cost)
            .sum();

        println!("\n📈 TRADE STATISTICS:");
        println!("  Total Trades: {}", total_trades);
        println!("  Total Volume: ${:.2}", total_volume);
        println!("  Total Costs: ${:.2}", total_costs);
        println!(
            "  Avg Trades per Day: {:.1}",
            total_trades as f64 / executed_trades_by_date.len() as f64
        );
    }

    println!("\n=== END BACKTEST RESULTS ===");
}
