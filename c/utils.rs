use std::collections::HashMap;

pub fn ticker_to_id(ticker: &str) -> Option<usize> {
    match ticker {
        "BTC" => Some(0),
        "ETH" => Some(1),
        // Add more tickers as needed
        _ => {
            println!("Ticker not found: {}", ticker);
            None
        }
    }
}

pub fn ticker_to_constraint() -> HashMap<String, HashMap<String, f64>> {
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