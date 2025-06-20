use crate::params::{Frequency, SignalParams};
use chrono::{DateTime, Datelike, Timelike, Utc};
use std::collections::HashMap;

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
    let btc_strategy = vec![
        SignalParams::EmaRsiMacd {
            ema_fast: 12,
            ema_medium: 26,
            ema_slow: 50,
            rsi_period: 14,
            initial_close: 50000.0,
            rsi_ob: 70.0,
            rsi_os: 30.0,
            rsi_bull_div: 40.0,
            macd_fast: 12,
            macd_slow: 26,
            macd_signal: 9,
        },
        // SignalParams::BbRsiOversold {
        //     name: "BTC_BB_RSI".to_string(),
        //     std_dev: 2.0,
        //     initial_close: 50000.0,
        //     rsi_period: 14,
        //     rsi_ob: 70.0,
        //     rsi_os: 30.0,
        //     rsi_bull_div: 35.0,
        // },
    ];

    // ETH Strategy: More conservative with pattern recognition
    let eth_strategy = vec![
        SignalParams::EmaRsiMacd {
            ema_fast: 12,
            ema_medium: 26,
            ema_slow: 50,
            rsi_period: 14,
            initial_close: 50000.0,
            rsi_ob: 70.0,
            rsi_os: 30.0,
            rsi_bull_div: 40.0,
            macd_fast: 12,
            macd_slow: 26,
            macd_signal: 9,
        },
        // SignalParams::TripleEmaPatternMacdRsi {
        //     SignalParams::EmaRsiMacd {
        //     ema_fast: 12,
        //     ema_medium: 26,
        //     ema_slow: 50,
        //     rsi_period: 14,
        //     initial_close: 50000.0,
        //     rsi_ob: 70.0,
        //     rsi_os: 30.0,
        //     rsi_bull_div: 40.0,
        //     macd_fast: 12,
        //     macd_slow: 26,
        //     macd_signal: 9,
        // },
        //     name: "ETH_TRIPLE_EMA".to_string(),
        //     ema_fast: 9,
        //     ema_medium: 21,
        //     ema_slow: 55,
        //     resistance_threshold: 0.02,
        //     support_threshold: 0.02,
        //     initial_high: 3500.0,
        //     initial_low: 3000.0,
        //     initial_close: 3250.0,
        //     macd_fast: 12,
        //     macd_slow: 26,
        //     macd_signal: 9,
        //     rsi_period: 14,
        //     rsi_ob: 75.0,
        //     rsi_os: 25.0,
        //     rsi_bull_div: 35.0,
        // },
        // SignalParams::RsiOversoldReversal {
        //     name: "ETH_RSI_REVERSAL".to_string(),
        //     rsi_period: 14,
        //     initial_close: 3250.0,
        //     rsi_ob: 75.0,
        //     rsi_os: 25.0,
        //     rsi_bull_div: 30.0,
        //     ema_fast: 12,
        //     ema_medium: 26,
        //     ema_slow: 50,
        // },
    ];

    strategies.push(btc_strategy);
    strategies.push(eth_strategy);

    strategies
}

/// Converts Unix timestamp (i64) to DateTime<Utc>
pub fn timestamp_to_datetime(timestamp: i64) -> DateTime<Utc> {
    DateTime::from_timestamp(timestamp, 0).unwrap_or_else(|| Utc::now())
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
