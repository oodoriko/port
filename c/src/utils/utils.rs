use crate::core::params::{Frequency, SignalParams};
use chrono::{DateTime, Datelike, Timelike, Utc};
use std::collections::HashMap;
use std::fs::File;
use std::io::Write;
pub fn id_to_ticker(ticker: i8) -> Option<String> {
    match ticker {
        0 => Some("BTC".to_string()),
        1 => Some("ETH".to_string()),
        2 => Some("SOL".to_string()),
        // Add more tickers as needed
        _ => {
            println!("Ticker not found: {}", ticker);
            None
        }
    }
}

pub fn ticker_to_constraint() -> HashMap<String, HashMap<String, f32>> {
    let mut map = HashMap::new();
    // Example constraints for BTC
    let mut btc_constraint = HashMap::new();
    btc_constraint.insert("trailing_stop_pct".to_string(), 0.05);
    btc_constraint.insert("rebalance_threshold".to_string(), 0.1);
    map.insert("BTC".to_string(), btc_constraint);

    // Example constraints for ETH
    let mut eth_constraint = HashMap::new();
    eth_constraint.insert("trailing_stop_pct".to_string(), 0.07);
    eth_constraint.insert("rebalance_threshold".to_string(), 0.12);
    map.insert("ETH".to_string(), eth_constraint);

    // Add more tickers and their constraints as needed
    map
}

pub fn create_sample_strategies() -> Vec<Vec<SignalParams>> {
    let mut strategies = vec![];

    // BTC Strategy: Aggressive momentum with RSI and MACD
    let btc_strategy = vec![SignalParams::EmaRsiMacd {
        ema_fast: 12,
        ema_medium: 26,
        ema_slow: 50,
        rsi_period: 14,
        initial_close: None,
        rsi_ob: 70.0,
        rsi_os: 30.0,
        rsi_bull_div: 40.0,
        macd_fast: 12,
        macd_slow: 26,
        macd_signal: 9,
    }];

    // ETH Strategy: More conservative with pattern recognition
    let eth_strategy = vec![SignalParams::EmaRsiMacd {
        ema_fast: 12,
        ema_medium: 26,
        ema_slow: 50,
        rsi_period: 14,
        initial_close: None,
        rsi_ob: 70.0,
        rsi_os: 30.0,
        rsi_bull_div: 40.0,
        macd_fast: 12,
        macd_slow: 26,
        macd_signal: 9,
    }];

    strategies.push(btc_strategy);
    strategies.push(eth_strategy);

    strategies
}

/// Converts Unix timestamp (i64) to DateTime<Utc>
pub fn timestamp_to_datetime(timestamp: i64) -> DateTime<Utc> {
    DateTime::from_timestamp(timestamp, 0).unwrap_or_else(|| Utc::now())
}

/// Converts Unix timestamp (i64) to EST date string
pub fn timestamp_to_est_date(timestamp: i64) -> String {
    let utc_datetime = timestamp_to_datetime(timestamp);

    // Convert UTC to EST (UTC-5) or EDT (UTC-4) depending on daylight saving time
    // For simplicity, we'll use a fixed offset of -5 hours (EST)
    // In a production environment, you might want to use a proper timezone library
    // like chrono-tz for accurate DST handling

    let est_datetime = utc_datetime - chrono::Duration::hours(5);

    // Format as YYYY-MM-DD
    est_datetime.format("%Y-%m-%d").to_string()
}

/// Converts Unix timestamp (i64) to EST datetime string with time
pub fn timestamp_to_est_datetime(timestamp: i64) -> String {
    let utc_datetime = timestamp_to_datetime(timestamp);

    // Convert UTC to EST (UTC-5)
    let est_datetime = utc_datetime - chrono::Duration::hours(5);

    // Format as YYYY-MM-DD HH:MM:SS
    est_datetime.format("%Y-%m-%d %H:%M:%S").to_string()
}

pub fn is_end_of_period(timestamp: i64, frequency: &Frequency) -> bool {
    match frequency {
        Frequency::Daily => {
            // Check if timestamp is in the last hour of a day (23:00-23:59)
            // 86400 seconds per day, 3600 seconds per hour
            (timestamp % 86400) >= 82800 // 23 * 3600 = 82800
        }
        Frequency::Weekly => {
            // Unix timestamp epoch started on Thursday, so Sunday is (timestamp / 86400 + 4) % 7 == 0
            // But we want end of week, so check if it's late Sunday
            let days_since_epoch = timestamp / 86400;
            let day_of_week = (days_since_epoch + 4) % 7; // 0 = Sunday, 1 = Monday, etc.
            day_of_week == 0 && (timestamp % 86400) >= 82800 // Sunday and late in day
        }
        // For monthly, quarterly, yearly we still need DateTime conversion for accuracy
        _ => {
            let datetime = timestamp_to_datetime(timestamp);
            _is_end_of_period(datetime, frequency)
        }
    }
}

/// Determines if the current timestamp represents the end of a period based on frequency
pub fn _is_end_of_period(timestamp: DateTime<Utc>, frequency: &Frequency) -> bool {
    match frequency {
        Frequency::Daily => {
            // End of day: check if it's close to midnight (within the last hour of the day)
            let hour = timestamp.hour();
            hour == 23
        }
        Frequency::Weekly => {
            // End of week: Sunday (weekday 6 in chrono)
            let weekday = timestamp.weekday();
            weekday.num_days_from_sunday() == 6
        }
        Frequency::Monthly => {
            // End of month: last day of the month
            let current_month = timestamp.month();
            let current_year = timestamp.year();

            // Get the first day of next month and subtract 1 day to get last day of current month
            let next_month = if current_month == 12 {
                1
            } else {
                current_month + 1
            };
            let next_year = if current_month == 12 {
                current_year + 1
            } else {
                current_year
            };

            if let Some(first_of_next_month) =
                chrono::NaiveDate::from_ymd_opt(next_year, next_month, 1)
            {
                let last_day_of_month = first_of_next_month.pred_opt().unwrap().day();
                timestamp.day() == last_day_of_month
            } else {
                false
            }
        }
        Frequency::Quarterly => {
            // End of quarter: last day of March, June, September, or December
            let month = timestamp.month();
            let is_quarter_end_month = matches!(month, 3 | 6 | 9 | 12);
            is_quarter_end_month
        }
        Frequency::Yearly => {
            // End of year: December 31st
            timestamp.month() == 12 && timestamp.day() == 31
        }
    }
}

// for auditing
// Function to export array of arrays to CSV with enum conversion and proper decimal formatting
pub fn export_array_to_csv_with_enums(
    data: &[Vec<i64>],
    filename: &str,
    headers: Option<Vec<&str>>,
    convert_enums: bool,
) -> Result<(), Box<dyn std::error::Error>> {
    let mut file = File::create(filename)?;

    // Write headers if provided
    if let Some(headers) = headers {
        writeln!(file, "{}", headers.join(","))?;
    }

    // Write data rows
    for row in data {
        let row_str: Vec<String> = row
            .iter()
            .enumerate()
            .map(|(i, &val)| {
                if convert_enums {
                    // Convert enum values to strings based on position
                    match i {
                        2 => {
                            // trade_type column
                            match val {
                                0 => "SignalBuy".to_string(),
                                1 => "SignalSell".to_string(),
                                2 => "StopLoss".to_string(),
                                3 => "Liquidation".to_string(),
                                4 => "TakeProfit".to_string(),
                                _ => val.to_string(),
                            }
                        }
                        3 => {
                            // trade_status column
                            match val {
                                0 => "Pending".to_string(),
                                1 => "Executed".to_string(),
                                2 => "Failed".to_string(),
                                3 => "Rejected".to_string(),
                                _ => val.to_string(),
                            }
                        }
                        _ => {
                            // Convert i64 back to f32 and format with 4 decimal places
                            let float_val = val as f32 / 10000.0; // Assuming values were multiplied by 10000
                            format!("{:.4}", float_val)
                        }
                    }
                } else {
                    // For non-enum data, format as float with 4 decimal places
                    let float_val = val as f32 / 10000.0; // Assuming values were multiplied by 10000
                    format!("{:.4}", float_val)
                }
            })
            .collect();
        writeln!(file, "{}", row_str.join(","))?;
    }

    println!("Data exported to: {}", filename);
    Ok(())
}

// Function to export trade and portfolio data separately
pub fn export_backtest_data_to_csv(
    all_trade: &[Vec<i64>],
    all_portfolio: &[Vec<i64>],
    all_positions: &[Vec<i64>],
    base_filename: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    // Export trade data with enum conversion
    if !all_trade.is_empty() {
        let trade_headers = vec![
            "timestamp",
            "quantity",
            "trade_type",
            "trade_status",
            "generated_at",
            "execution_timestamp",
            "price",
            "cost",
            "pro_rata_buy_cost",
            "avg_entry_price",
            "holding_period",
            "realized_pnl_gross",
            "realized_return",
        ];
        export_array_to_csv_with_enums(
            all_trade,
            &format!("{}_trades.csv", base_filename),
            Some(trade_headers),
            true,
        )?;
    }

    // Export portfolio data (no enum conversion needed)
    if !all_portfolio.is_empty() {
        let portfolio_headers = vec![
            "timestamp",
            "equity",
            "cash",
            "notional",
            "cost",
            "realized_pnl",
            "unrealized_pnl",
            "peak_equity",
            "num_assets",
            "total_capital_distribution",
            "holdings",
        ];
        export_array_to_csv_with_enums(
            all_portfolio,
            &format!("{}_portfolio.csv", base_filename),
            Some(portfolio_headers),
            false,
        )?;
    }

    // Export position data (no enum conversion needed)
    if !all_positions.is_empty() {
        let position_headers = vec![
            "ticker_id",
            "price",
            "quantity",
            "avg_entry_price",
            "entry_timestamp",
            "notional",
            "peak_price",
            "trailing_stop_price",
            "take_profit_price",
            "unrealized_pnl",
            "cum_buy_proceeds",
            "cum_buy_cost",
            "last_entry_price",
            "last_entry_timestamp",
            "cum_sell_proceeds",
            "cum_sell_cost",
            "realized_pnl_gross",
            "realized_pnl_net",
            "last_exit_price",
            "last_exit_timestamp",
            "last_exit_pnl",
            "total_shares_bought",
            "total_shares_sold",
            "take_profit_gain",
            "take_profit_loss",
            "stop_loss_gain",
            "stop_loss_loss",
            "signal_sell_gain",
            "signal_sell_loss",
        ];
        export_array_to_csv_with_enums(
            all_positions,
            &format!("{}_positions.csv", base_filename),
            Some(position_headers),
            false,
        )?;
    }
    Ok(())
}

//
// let mut all_trade = Vec::new();
// let mut all_positions = Vec::new();
// let mut all_portfolio = Vec::new();

// if temp_trades.len() > 0 {
//     let mut portfolio_data = Vec::new();
//     portfolio_data.push(time);
//     portfolio_data
//         .push((portfolio.equity_curve[portfolio.equity_curve.len() - 1] * 10000.0) as i64);
//     portfolio_data
//         .push((portfolio.cash_curve[portfolio.cash_curve.len() - 1] * 10000.0) as i64);
//     portfolio_data.push(
//         (portfolio.notional_curve[portfolio.notional_curve.len() - 1] * 10000.0) as i64,
//     );
//     portfolio_data
//         .push((portfolio.cost_curve[portfolio.cost_curve.len() - 1] * 10000.0) as i64);
//     portfolio_data.push(
//         (portfolio.realized_pnl_curve[portfolio.realized_pnl_curve.len() - 1] * 10000.0)
//             as i64,
//     );
//     portfolio_data.push(
//         (portfolio.unrealized_pnl_curve[portfolio.unrealized_pnl_curve.len() - 1] * 10000.0)
//             as i64,
//     );
//     portfolio_data.push((portfolio.peak_equity * 10000.0) as i64);
//     portfolio_data.push(portfolio.num_assets as i64);
//     portfolio_data.push((portfolio.total_capital_distribution * 10000.0) as i64);
//     portfolio_data
//         .push((portfolio.holdings[portfolio.holdings.len() - 1] * 10000.0) as i64);

//     all_portfolio.push(portfolio_data);

//     let mut position_data = Vec::new();
//     let pos = portfolio.positions[0].as_ref().unwrap();
//     position_data.push(pos.ticker_id as i64);
//     position_data.push((prev_close_prices[pos.ticker_id as usize] * 10000.0) as i64);
//     position_data.push((pos.quantity * 10000.0) as i64);
//     position_data.push((pos.avg_entry_price * 10000.0) as i64);
//     position_data.push(pos.entry_timestamp as i64);
//     position_data.push((pos.notional * 10000.0) as i64);
//     position_data.push((pos.peak_price * 10000.0) as i64);
//     position_data.push((pos.trailing_stop_price * 10000.0) as i64);
//     position_data.push((pos.take_profit_price * 10000.0) as i64);
//     position_data.push((pos.unrealized_pnl * 10000.0) as i64);
//     position_data.push((pos.cum_buy_proceeds * 10000.0) as i64);
//     position_data.push((pos.cum_buy_cost * 10000.0) as i64);
//     position_data.push((pos.last_entry_price * 10000.0) as i64);
//     position_data.push(pos.last_entry_timestamp as i64);
//     position_data.push((pos.cum_sell_proceeds * 10000.0) as i64);
//     position_data.push((pos.cum_sell_cost * 10000.0) as i64);
//     position_data.push((pos.realized_pnl_gross * 10000.0) as i64);
//     position_data.push((pos.realized_pnl_net * 10000.0) as i64);
//     position_data.push((pos.last_exit_price * 10000.0) as i64);
//     position_data.push(pos.last_exit_timestamp as i64);
//     position_data.push((pos.last_exit_pnl * 10000.0) as i64);
//     position_data.push((pos.total_shares_bought * 10000.0) as i64);
//     position_data.push((pos.total_shares_sold * 10000.0) as i64);
//     position_data.push((pos.take_profit_gain * 10000.0) as i64);
//     position_data.push((pos.take_profit_loss * 10000.0) as i64);
//     position_data.push((pos.stop_loss_gain * 10000.0) as i64);
//     position_data.push((pos.stop_loss_loss * 10000.0) as i64);
//     position_data.push((pos.signal_sell_gain * 10000.0) as i64);
//     position_data.push((pos.signal_sell_loss * 10000.0) as i64);
//     all_positions.push(position_data);
// }

// for trade in pending_trades {
//     let mut trade_data = Vec::new();
//     trade_data.push(time);
//     trade_data.push((trade.quantity * 10000.0) as i64);
//     trade_data.push(trade.trade_type as i64);
//     trade_data.push(trade.trade_status as i64);
//     trade_data.push(trade.generated_at as i64);
//     trade_data.push(trade.execution_timestamp as i64);
//     trade_data.push((trade.price * 10000.0) as i64);
//     trade_data.push((trade.cost * 10000.0) as i64);
//     trade_data.push((trade.pro_rata_buy_cost * 10000.0) as i64);
//     trade_data.push((trade.avg_entry_price * 10000.0) as i64);
//     trade_data.push(trade.holding_period as i64);
//     trade_data.push((trade.realized_pnl_gross * 10000.0) as i64);
//     trade_data.push((trade.realized_return_net * 10000.0) as i64);
//     all_trade.push(trade_data);
// }

// for trade in temp_executed_trades {
//     let mut trade_data = Vec::new();
//     trade_data.push(time);
//     trade_data.push((trade.quantity * 10000.0) as i64);
//     trade_data.push(trade.trade_type as i64);
//     trade_data.push(trade.trade_status as i64);
//     trade_data.push(trade.generated_at as i64);
//     trade_data.push(trade.execution_timestamp as i64);
//     trade_data.push((trade.price * 10000.0) as i64);
//     trade_data.push((trade.cost * 10000.0) as i64);
//     trade_data.push((trade.pro_rata_buy_cost * 10000.0) as i64);
//     trade_data.push((trade.avg_entry_price * 10000.0) as i64);
//     trade_data.push(trade.holding_period as i64);
//     trade_data.push((trade.realized_pnl_gross * 10000.0) as i64);
//     trade_data.push((trade.realized_return_net * 10000.0) as i64);
//     all_trade.push(trade_data);
// }

// export_backtest_data_to_csv(
//     &all_trade,
//     &all_portfolio,
//     &all_positions,
//     &format!("{}_backtest", strategy_name),
// )
// .unwrap();
