use crate::params::SignalParams;
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

pub fn create_sample_strategies() -> HashMap<String, Vec<SignalParams>> {
    let mut strategies = HashMap::new();

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

    strategies.insert("BTC-USD".to_string(), btc_strategy);
    strategies.insert("ETH-USD".to_string(), eth_strategy);

    strategies
}
