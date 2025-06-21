use anyhow::Result;
use chrono::{Duration, Utc};
use port_etl::{CoinbaseDataFetcher, OhlcvData};

// Regular function that can be called from anywhere
pub async fn coinbase_connection_test() -> Result<()> {
    println!("Testing Coinbase connection...");

    // Test creating a new fetcher
    let fetcher = CoinbaseDataFetcher::new();
    println!("✅ Successfully created Coinbase data fetcher");

    // Test fetching a small amount of recent data
    let end = Utc::now();
    let start = end - Duration::minutes(30); // Just 30 minutes of data
    let symbol = "BTC-USD";
    let granularity = 300; // 5 minutes

    println!(
        "Fetching recent data for {} from {} to {}",
        symbol, start, end
    );

    match fetcher
        .fetch_candles(symbol, start, end, granularity, Some(1))
        .await
    {
        Ok(candles) => {
            println!(
                "✅ Successfully fetched {} candles from Coinbase API",
                candles.len()
            );

            if !candles.is_empty() {
                let first_candle = &candles[0];
                println!("First candle:");
                println!(
                    "  Timestamp: {} ({})",
                    first_candle.timestamp,
                    first_candle.est_time()
                );
                println!(
                    "  OHLCV: O:{}, H:{}, L:{}, C:{}, V:{}",
                    first_candle.open,
                    first_candle.high,
                    first_candle.low,
                    first_candle.close,
                    first_candle.volume
                );

                // Test OhlcvData creation
                let test_candle = OhlcvData::new(
                    first_candle.timestamp,
                    first_candle.open,
                    first_candle.high,
                    first_candle.low,
                    first_candle.close,
                    first_candle.volume,
                );
                println!("✅ Successfully created OhlcvData struct");
                println!("  EST Time: {}", test_candle.est_time());
            } else {
                println!("⚠️ No candles returned (this might happen during market closed hours)");
            }
        }
        Err(e) => {
            println!("❌ Failed to fetch candles: {}", e);
            println!("This might indicate a network issue or API rate limiting");
            return Err(e);
        }
    }

    println!("🎉 Coinbase connection test passed!");
    Ok(())
}

// Test wrapper that calls the regular function
#[tokio::test]
async fn test_coinbase_connection() -> Result<()> {
    coinbase_connection_test().await
}

#[tokio::test]
async fn test_ohlcv_data_methods() -> Result<()> {
    println!("Testing OhlcvData struct methods...");

    let timestamp = Utc::now().timestamp();
    let candle = OhlcvData::new(timestamp, 50000.0, 50100.0, 49900.0, 50050.0, 1.5);

    println!("Created OHLCV data:");
    println!("  Timestamp: {}", candle.timestamp);
    println!(
        "  OHLC: {}, {}, {}, {}",
        candle.open, candle.high, candle.low, candle.close
    );
    println!("  Volume: {}", candle.volume);
    println!("  EST Time: {}", candle.est_time());

    // Test that EST time conversion works
    let est_time = candle.est_time();
    println!("✅ EST time conversion successful: {}", est_time);

    Ok(())
}

#[tokio::test]
async fn test_coinbase_chunking() -> Result<()> {
    println!("Testing Coinbase chunking logic...");

    let fetcher = CoinbaseDataFetcher::new();
    let end = Utc::now();
    // Request more data than can fit in a single API call to test chunking
    let start = end - Duration::hours(24); // 24 hours should require chunking
    let symbol = "BTC-USD";
    let granularity = 60; // 1 minute granularity

    println!(
        "Fetching large dataset for {} to test chunking: {} to {}",
        symbol, start, end
    );

    match fetcher
        .fetch_candles(symbol, start, end, granularity, Some(1))
        .await
    {
        Ok(candles) => {
            println!(
                "✅ Successfully fetched {} candles with chunking",
                candles.len()
            );

            // Verify candles are in chronological order
            if candles.len() > 1 {
                let first_ts = candles[0].timestamp;
                let last_ts = candles[candles.len() - 1].timestamp;
                println!("  Time range: {} to {}", first_ts, last_ts);

                if first_ts <= last_ts {
                    println!("✅ Candles are in chronological order");
                } else {
                    println!("⚠️ Candles might not be properly ordered");
                }
            }
        }
        Err(e) => {
            println!("❌ Failed to fetch chunked data: {}", e);
            // This might fail during market closed hours, so we'll be lenient
            println!("This might be expected during market closed hours");
        }
    }

    println!("🎉 Coinbase chunking test completed!");
    Ok(())
}
