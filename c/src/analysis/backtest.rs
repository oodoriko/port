use crate::core::params::{
    PortfolioConstraintParams, PortfolioParams, PositionConstraintParams, SignalParams,
};
use crate::data::database_service;
use crate::trading::portfolio::Portfolio;
use crate::trading::strategy::Strategy;
use crate::trading::trade::{Trade, TradeType};
use crate::utils::utils::export_backtest_data_to_csv;
use chrono::{DateTime, Utc};
use port_etl::InfluxDBHandler;

use std::time::Instant;

pub struct BacktestResult {
    pub portfolio: Portfolio,
    pub executed_trades_by_date: std::collections::HashMap<i64, Vec<Trade>>,
    pub exited_early: bool,
    pub start_timestamp: u64,
    pub end_timestamp: u64,
    pub timestamps: Vec<i64>,
    pub exit_price: Vec<f32>, // use to calculate unrealized pnl in positions still open
    pub trades_type_count: Vec<i32>,
}

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
) -> Result<BacktestResult, Box<dyn std::error::Error>> {
    //*************** preparing data ***************
    let (data, timestamps) = get_data(tickers.clone(), start, end, cadence, debug).await?;
    // Safety check: ensure we have enough data for warm-up period
    if data.len() <= warm_up_period {
        return Err(format!(
            "Insufficient data: got {} data points, need at least {} for warm-up period",
            data.len(),
            warm_up_period + 1
        )
        .into());
    }

    let warm_up_price_data: Vec<Vec<Vec<f32>>> = data[..warm_up_period].to_vec();
    let n_assets = tickers.len();
    let mut prev_close_prices = Vec::with_capacity(n_assets);
    let mut prev_open_prices = Vec::with_capacity(n_assets);
    let mut curr_open_prices = Vec::with_capacity(n_assets);

    //*************** audit trail ***************
    let mut all_trade = Vec::new();
    let mut all_positions = Vec::new();
    let mut all_portfolio = Vec::new();
    //*************** audit trail ***************

    //*************** rehydrate portfolio ***************
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

    //*************** initiate backtest variables ***************
    let mut early_exit = false;
    let data_len = data.len();
    let mut exit_idx = data_len - 2;
    let mut executed_trades_by_date = std::collections::HashMap::new();
    let mut trades_type_count = vec![0; 10];

    //*************** backtest ***************
    println!("Start backtesting...");
    let backtest_timer = Instant::now();
    for idx in warm_up_period..data_len - 1 {
        let time = timestamps[idx];
        let mut available_cash = portfolio.get_current_cash();
        let mut new_cost = 0.0;
        let mut new_realized_pnl = 0.0;
        let mut executed_trades = Vec::new();

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
        let (is_liquidation, mut risk_management_trades, take_profit_trades) = constraint
            .pre_order_check(
                &prev_close_prices,
                &portfolio.positions,
                portfolio.peak_equity,
                available_cash,
                time as u64,
            );

        if is_liquidation {
            portfolio.liquidation(
                &curr_open_prices,
                &mut risk_management_trades,
                time as u64,
                &mut trades_type_count,
            );
            executed_trades_by_date.insert(time, risk_management_trades);
            println!("江南皮革厂倒闭啦！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！");
            early_exit = true;
            exit_idx = idx;
            break;
        }

        // first execute pre signal trades using current t0 open prices
        // we are bypassing the backtest logic here because t0 is not available until t+1
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
                &mut trades_type_count,
            );

            //*************** audit trail ***************
            let mut position_data = Vec::new();
            let pos = portfolio.positions[0].as_ref().unwrap();
            position_data.push(pos.ticker_id as i64);
            position_data.push((curr_open_prices[pos.ticker_id as usize] * 10000.0) as i64);
            position_data.push((pos.quantity * 10000.0) as i64);
            position_data.push((pos.avg_entry_price * 10000.0) as i64);
            position_data.push(pos.entry_timestamp as i64);
            position_data.push((pos.notional * 10000.0) as i64);
            position_data.push((pos.peak_price * 10000.0) as i64);
            position_data.push((pos.trailing_stop_price * 10000.0) as i64);
            position_data.push((pos.take_profit_price * 10000.0) as i64);
            position_data.push((pos.unrealized_pnl * 10000.0) as i64);
            position_data.push((pos.cum_buy_proceeds * 10000.0) as i64);
            position_data.push((pos.cum_buy_cost * 10000.0) as i64);
            position_data.push((pos.last_entry_price * 10000.0) as i64);
            position_data.push(pos.last_entry_timestamp as i64);
            position_data.push((pos.cum_sell_proceeds * 10000.0) as i64);
            position_data.push((pos.cum_sell_cost * 10000.0) as i64);
            position_data.push((pos.realized_pnl_gross * 10000.0) as i64);
            position_data.push((pos.realized_pnl_net * 10000.0) as i64);
            position_data.push((pos.last_exit_price * 10000.0) as i64);
            position_data.push(pos.last_exit_timestamp as i64);
            position_data.push((pos.last_exit_pnl * 10000.0) as i64);
            position_data.push((pos.total_shares_bought * 10000.0) as i64);
            position_data.push((pos.total_shares_sold * 10000.0) as i64);
            position_data.push((pos.take_profit_gain * 10000.0) as i64);
            position_data.push((pos.take_profit_loss * 10000.0) as i64);
            position_data.push((pos.stop_loss_gain * 10000.0) as i64);
            position_data.push((pos.stop_loss_loss * 10000.0) as i64);
            position_data.push((pos.signal_sell_gain * 10000.0) as i64);
            position_data.push((pos.signal_sell_loss * 10000.0) as i64);
            all_positions.push(position_data);
            //*************** audit trail ***************

            available_cash += new_cash_after_trades;
            new_cost += new_total_cost;
            new_realized_pnl += new_total_realized_pnl;
            executed_trades.extend(new_executed_trades);
        }

        // then execute previous trades using t-1 close prices
        // pick out the asset id of asset that just triggered stop loss - they are no longer tradable
        let stop_loss_triggered_pos = risk_management_trades
            .iter()
            .filter(|t| t.trade_type == TradeType::StopLoss)
            .map(|t| t.ticker_id)
            .collect::<Vec<_>>();

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
                &mut trades_type_count,
            );
            //*************** audit trail ***************
            let mut position_data = Vec::new();
            let pos = portfolio.positions[0].as_ref().unwrap();
            position_data.push(pos.ticker_id as i64);
            position_data.push((prev_close_prices[pos.ticker_id as usize] * 10000.0) as i64);
            position_data.push((pos.quantity * 10000.0) as i64);
            position_data.push((pos.avg_entry_price * 10000.0) as i64);
            position_data.push(pos.entry_timestamp as i64);
            position_data.push((pos.notional * 10000.0) as i64);
            position_data.push((pos.peak_price * 10000.0) as i64);
            position_data.push((pos.trailing_stop_price * 10000.0) as i64);
            position_data.push((pos.take_profit_price * 10000.0) as i64);
            position_data.push((pos.unrealized_pnl * 10000.0) as i64);
            position_data.push((pos.cum_buy_proceeds * 10000.0) as i64);
            position_data.push((pos.cum_buy_cost * 10000.0) as i64);
            position_data.push((pos.last_entry_price * 10000.0) as i64);
            position_data.push(pos.last_entry_timestamp as i64);
            position_data.push((pos.cum_sell_proceeds * 10000.0) as i64);
            position_data.push((pos.cum_sell_cost * 10000.0) as i64);
            position_data.push((pos.realized_pnl_gross * 10000.0) as i64);
            position_data.push((pos.realized_pnl_net * 10000.0) as i64);
            position_data.push((pos.last_exit_price * 10000.0) as i64);
            position_data.push(pos.last_exit_timestamp as i64);
            position_data.push((pos.last_exit_pnl * 10000.0) as i64);
            position_data.push((pos.total_shares_bought * 10000.0) as i64);
            position_data.push((pos.total_shares_sold * 10000.0) as i64);
            position_data.push((pos.take_profit_gain * 10000.0) as i64);
            position_data.push((pos.take_profit_loss * 10000.0) as i64);
            position_data.push((pos.stop_loss_gain * 10000.0) as i64);
            position_data.push((pos.stop_loss_loss * 10000.0) as i64);
            position_data.push((pos.signal_sell_gain * 10000.0) as i64);
            position_data.push((pos.signal_sell_loss * 10000.0) as i64);
            all_positions.push(position_data);
            //*************** audit trail ***************
            available_cash += new_cash_after_trades;
            new_cost += new_total_cost;
            new_realized_pnl += new_total_realized_pnl;
            executed_trades.extend(new_executed_trades);
        }

        let temp_trades = executed_trades.clone();
        if executed_trades.len() > 0 {
            //*************** audit trail ***************

            for trade in executed_trades.clone() {
                let mut trade_data = Vec::new();
                trade_data.push(time);
                trade_data.push((trade.quantity * 10000.0) as i64);
                trade_data.push(trade.trade_type as i64);
                trade_data.push(trade.trade_status as i64);
                trade_data.push(trade.generated_at as i64);
                trade_data.push(trade.execution_timestamp as i64);
                trade_data.push((trade.price * 10000.0) as i64);
                trade_data.push((trade.cost * 10000.0) as i64);
                trade_data.push((trade.pro_rata_buy_cost * 10000.0) as i64);
                trade_data.push((trade.avg_entry_price * 10000.0) as i64);
                trade_data.push(trade.holding_period as i64);
                trade_data.push((trade.realized_pnl_gross * 10000.0) as i64);
                trade_data.push((trade.realized_return_net * 10000.0) as i64);
                all_trade.push(trade_data);
            }
            executed_trades_by_date.insert(time, executed_trades);
            //*************** audit trail ***************
        }

        // handle cash distribution event, being conservative here, t0 cash is not available for trading
        available_cash += portfolio.get_new_cash(time);

        // update signals with t-1 close
        strategy.update_signals(data[idx - 1].clone());
        let signals = strategy.generate_signals();

        // generate signal based trades after trades and capital distribution
        let new_signal_based_trades = constraint.generate_trades(
            &signals,
            &prev_close_prices,
            portfolio.get_current_equity(),
            available_cash,
            time as u64,
            &portfolio.positions,
            &mut trades_type_count,
        );

        portfolio.pending_trades = new_signal_based_trades;

        // mark portfolio at t-1 close (NEED TO THINK ABOUT THIS AGAIN)
        portfolio.post_order_update(
            &prev_close_prices,
            available_cash,
            new_cost,
            new_realized_pnl,
        );
        //*************** audit trail ***************
        if temp_trades.len() > 0 {
            let mut portfolio_data = Vec::new();
            portfolio_data.push(time);
            portfolio_data
                .push((portfolio.equity_curve[portfolio.equity_curve.len() - 1] * 10000.0) as i64);
            portfolio_data
                .push((portfolio.cash_curve[portfolio.cash_curve.len() - 1] * 10000.0) as i64);
            portfolio_data.push(
                (portfolio.notional_curve[portfolio.notional_curve.len() - 1] * 10000.0) as i64,
            );
            portfolio_data
                .push((portfolio.cost_curve[portfolio.cost_curve.len() - 1] * 10000.0) as i64);
            portfolio_data.push(
                (portfolio.realized_pnl_curve[portfolio.realized_pnl_curve.len() - 1] * 10000.0)
                    as i64,
            );
            portfolio_data.push(
                (portfolio.unrealized_pnl_curve[portfolio.unrealized_pnl_curve.len() - 1] * 10000.0)
                    as i64,
            );
            portfolio_data.push((portfolio.peak_equity * 10000.0) as i64);
            portfolio_data.push(portfolio.num_assets as i64);
            portfolio_data.push((portfolio.total_capital_distribution * 10000.0) as i64);
            portfolio_data
                .push((portfolio.holdings[portfolio.holdings.len() - 1] * 10000.0) as i64);

            all_portfolio.push(portfolio_data);
        };
        //*************** audit trail ***************
    }

    println!("Backtesting completed");
    println!(
        "[Timer] Time to run backtest: {:.3} seconds",
        backtest_timer.elapsed().as_secs_f64()
    );

    //*************** export audit trail ***************
    export_backtest_data_to_csv(
        &all_trade,
        &all_portfolio,
        &all_positions,
        &format!("{}_backtest", strategy_name),
    )
    .unwrap();
    //*************** export audit trail ***************

    Ok(BacktestResult {
        portfolio,
        executed_trades_by_date,
        exited_early: early_exit,
        start_timestamp: timestamps[warm_up_period + 1] as u64,
        end_timestamp: timestamps[exit_idx] as u64,
        timestamps: timestamps,
        exit_price: data[data_len - 1].iter().map(|x| x[3]).collect::<Vec<_>>(),
        trades_type_count,
    })
}

async fn get_data(
    tickers: Vec<String>,
    start: DateTime<Utc>,
    end: DateTime<Utc>,
    cadence: u64,
    debug: bool,
) -> Result<(Vec<Vec<Vec<f32>>>, Vec<i64>), Box<dyn std::error::Error>> {
    let data_timer = Instant::now();

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

        println!(
            "[Timer] Time to query nen: {:.3} seconds",
            data_timer.elapsed().as_secs_f64()
        );

        let convert_timer = Instant::now();
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

        println!(
            "[Timer] Time to convert data: {:.3} seconds",
            convert_timer.elapsed().as_secs_f64()
        );

        (converted_data, converted_timestamps)
    };
    Ok((data, timestamps))
}

#[inline(always)]
pub fn backtest_result(
    portfolio: &Portfolio,
    executed_trades_by_date: &std::collections::HashMap<i64, Vec<crate::trading::trade::Trade>>,
    trades_type_count: &Vec<i32>,
) {
    println!("=== BACKTEST RESULTS ===\n");

    println!("📊 Portfolio: {}", portfolio.name);
    let equity_len = portfolio.equity_curve.len();
    println!("📈 Total Records: {}", equity_len);
    println!("📅 Trade Events: {}", executed_trades_by_date.len());

    println!(
        "Trade execution rate: {:.2}%",
        trades_type_count[0] as f64 / trades_type_count.iter().sum::<i32>() as f64 * 100.0
    );

    println!("\n=== END BACKTEST RESULTS ===");
}
