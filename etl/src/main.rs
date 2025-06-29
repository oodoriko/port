use chrono::{DateTime, Utc};
use port_etl::{fetch_coinbase_historical_resumable, CoinbaseConfig};
use std::io::{self, Write};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    run_coinbase_historical_10().await?;
    Ok(())
}

async fn run_coinbase_historical_10() -> Result<(), Box<dyn std::error::Error>> {
    dotenv::dotenv().ok();
    io::stdout().flush()?;

    let start_date = DateTime::parse_from_rfc3339("2015-07-01T00:00:00Z")
        .unwrap()
        .with_timezone(&Utc);
    let end_date = DateTime::parse_from_rfc3339("2025-06-20T23:59:00Z")
        .unwrap()
        .with_timezone(&Utc);

    let tickers = vec![
        "BTC-USDC".to_string(),
        "ETH-USDC".to_string(),
        // "SOL-USDC".to_string(),
        // "LINK-USDC".to_string(),
        // "AVAX-USDC".to_string(),
    ];

    // Create config with API credentials from environment variables
    let api_key_id =
        std::env::var("COINBASE_API_KEY_ID").expect("COINBASE_API_KEY_ID must be set in .env file");
    let private_key = std::env::var("COINBASE_PRIVATE_KEY")
        .expect("COINBASE_PRIVATE_KEY must be set in .env file");

    let config = CoinbaseConfig::with_credentials(api_key_id, private_key);

    // Process ALL tickers using the new brokerage API
    let result =
        fetch_coinbase_historical_resumable(tickers, start_date, end_date, 60, Some(config), None)
            .await;

    match result {
        Ok(_) => {
            println!();
            println!("🎉 ETL Job Completed Successfully!");
            println!("✅ All data has been fetched and cached to database");
        }
        Err(e) => {
            println!("❌ ETL Job Failed: {}", e);
        }
    }
    Ok(())
}
