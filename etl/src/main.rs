use chrono::{DateTime, Utc};
use port_etl::fetch_coinbase_historical_resumable;
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
        "BTC-USD".to_string(),
        "ETH-USD".to_string(),
        "SOL-USD".to_string(),
        "LINK-USD".to_string(),
        "AVAX-USD".to_string(),
    ];

    // Process ALL tickers in parallel for maximum speed
    let result =
        fetch_coinbase_historical_resumable(tickers, start_date, end_date, 60, None, None).await;

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
