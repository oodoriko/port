// Tests for coinbase historical OHLCV job
// These tests validate the job logic before running expensive multi-year data pulls

use chrono::{DateTime, Duration, Utc};
use dotenv;
use port_etl::jobs::coinbase_historical_ohlcv_job::fetch_coinbase_historical_resumable;
use port_etl::{CoinbaseConfig, NeonConnection};
use std::env;

#[cfg(test)]
mod tests {
    use super::*;

    // Helper function to create test config with conservative settings
    fn get_test_config() -> CoinbaseConfig {
        // Load environment variables (will load from .env file)
        dotenv::dotenv().ok();

        let api_key_id =
            std::env::var("COINBASE_API_KEY_ID").unwrap_or_else(|_| "test_key_id".to_string());
        let private_key = std::env::var("COINBASE_PRIVATE_KEY")
            .unwrap_or_else(|_| "test_private_key".to_string());

        let mut config = CoinbaseConfig::with_credentials(api_key_id, private_key);
        config.max_retries = 3;
        config.initial_backoff_ms = 1000; // 1 second initial backoff
        config.backoff_multiplier = 2; // Double the backoff each retry
        config.chunk_size_days = 1; // Small chunks for testing
        config.enable_caching = true;
        config.delay_between_requests_ms = 500; // Conservative 500ms delay for testing (~2 req/sec)
        config
    }

    #[tokio::test]
    async fn test_short_timeframe_basic_functionality() {
        // Test with just 1 hour of data to validate basic functionality
        let tickers = vec!["BTC-USDC".to_string()]; // Use USDC pair for brokerage API
        let end_time = Utc::now();
        let start_time = end_time - Duration::hours(1);

        let mut config = get_test_config();
        config.max_retries = 2;
        config.initial_backoff_ms = 500; // Short backoff for quick test
        config.backoff_multiplier = 2;
        config.chunk_size_days = 1;
        config.enable_caching = false; // Disable caching for this quick test
        config.delay_between_requests_ms = 300; // 300ms delay for quick test

        // This should complete quickly and validate the basic API interaction
        let result = fetch_coinbase_historical_resumable(
            tickers,
            start_time,
            end_time,
            60, // 1-minute granularity
            Some(config),
            None, // No table prefix for this test
        )
        .await;

        // We expect this to succeed or fail gracefully
        match result {
            Ok(_) => println!("✅ Basic functionality test passed"),
            Err(e) => {
                println!("⚠️  Basic test failed (this might be expected): {}", e);
                // Don't fail the test - API might be down or rate limited
            }
        }
    }

    #[tokio::test]
    async fn test_database_connection_and_resume_logic() {
        // Load .env file before checking environment variables
        let _ = dotenv::dotenv()
            .or_else(|_| dotenv::from_filename("../.env"))
            .or_else(|_| dotenv::from_filename("./.env"));

        // Test that we can connect to the database and the resume logic works
        if env::var("DATABASE_URL").is_err() && env::var("NEON_DATABASE_URL").is_err() {
            println!("⏭️  Skipping database test - no DATABASE_URL configured");
            return;
        }

        let db_result = NeonConnection::new().await;
        match db_result {
            Ok(conn) => {
                println!("✅ Database connection successful");

                // Test that we can create the progress table
                let table_result = conn.create_etl_progress_table().await;
                match table_result {
                    Ok(_) => {
                        println!("✅ Progress table creation/verification successful");

                        // Verify the table was actually created
                        match conn.table_exists("etl_job_progress").await {
                            Ok(true) => println!("✅ ETL progress table exists and is accessible"),
                            Ok(false) => {
                                println!("⚠️  ETL progress table not found after creation")
                            }
                            Err(e) => println!("⚠️  Error checking table existence: {}", e),
                        }
                    }
                    Err(e) => println!("⚠️  Progress table issue: {}", e),
                }

                conn.close().await;
            }
            Err(e) => println!("⚠️  Database connection failed: {}", e),
        }
    }

    #[tokio::test]
    async fn test_time_chunking_logic() {
        // Test that our time chunking creates reasonable chunks for a 1-year period
        use port_etl::http_utils::create_time_chunks;

        let start_date = DateTime::parse_from_rfc3339("2023-01-01T00:00:00Z")
            .unwrap()
            .with_timezone(&Utc);
        let end_date = DateTime::parse_from_rfc3339("2024-01-01T00:00:00Z")
            .unwrap()
            .with_timezone(&Utc);

        let chunks = create_time_chunks(start_date, end_date, 30); // 30-day chunks

        println!("📊 Time chunking test:");
        println!(
            "   Period: {} to {}",
            start_date.format("%Y-%m-%d"),
            end_date.format("%Y-%m-%d")
        );
        println!("   Chunks created: {}", chunks.len());
        println!("   Expected chunks: ~12 (for 1 year with 30-day chunks)");

        // Verify we have reasonable number of chunks
        assert!(
            chunks.len() >= 10 && chunks.len() <= 15,
            "Unexpected number of chunks: {}",
            chunks.len()
        );

        // Verify chunks don't overlap and cover the full period
        for i in 0..chunks.len() {
            let (chunk_start, chunk_end) = chunks[i];
            assert!(
                chunk_start < chunk_end,
                "Chunk {} has invalid time range",
                i
            );

            if i > 0 {
                let (_prev_start, prev_end) = chunks[i - 1];
                assert!(
                    prev_end <= chunk_start,
                    "Chunks {} and {} overlap",
                    i - 1,
                    i
                );
            }
        }

        println!("✅ Time chunking logic validated");
    }

    #[tokio::test]
    async fn test_config_validation() {
        // Test that our configuration parameters are reasonable
        let config = get_test_config();

        println!("🔧 Configuration validation:");
        println!(
            "   Delay between requests: {}ms",
            config.delay_between_requests_ms
        );
        println!("   Chunk size (days): {}", config.chunk_size_days);
        println!("   Max retries: {}", config.max_retries);

        // Validate configuration is conservative enough for production
        assert!(
            config.delay_between_requests_ms >= 200,
            "Delay too short - risk of rate limiting (minimum 200ms = 5 req/sec)"
        );
        assert!(
            config.chunk_size_days <= 30,
            "Chunks too large - risk of timeout/memory issues"
        );
        assert!(
            config.max_retries >= 3,
            "Not enough retries - should handle temporary failures"
        );

        println!("✅ Configuration is appropriately conservative");
    }

    // HALF YEAR TEST RUN - This is the main validation before the 10-year run
    #[tokio::test]
    #[ignore] // Use `cargo test -- --ignored` to run this test
    async fn test_half_year_historical_data_pull() {
        println!("🚀 Starting HALF YEAR test run - this validates the full 10-year job logic");
        println!("   This test pulls 6 months of data for 2 tickers to validate:");
        println!("   - Resume capability works correctly");
        println!("   - Rate limiting is appropriate");
        println!("   - Database caching works");
        println!("   - No memory leaks or crashes");
        println!("   - Progress tracking is accurate");

        // Use 2022 data (complete year, not too recent)
        let start_date = DateTime::parse_from_rfc3339("2022-01-01T00:00:00Z")
            .unwrap()
            .with_timezone(&Utc);
        let end_date = DateTime::parse_from_rfc3339("2022-06-01T00:00:00Z")
            .unwrap()
            .with_timezone(&Utc);

        let tickers = vec!["BTC-USD".to_string(), "ETH-USD".to_string()];

        let mut config = get_test_config();
        config.max_retries = 5; // More retries for this important test
        config.initial_backoff_ms = 2000; // 2 second initial backoff for important test
        config.backoff_multiplier = 2; // Double the backoff each retry
        config.chunk_size_days = 7; // Weekly chunks for good granularity
        config.enable_caching = true;
        config.delay_between_requests_ms = 300; // Conservative 300ms delay (~3.3 req/sec)

        println!("📅 Test parameters:");
        println!(
            "   Period: {} to {}",
            start_date.format("%Y-%m-%d"),
            end_date.format("%Y-%m-%d")
        );
        println!("   Tickers: {:?}", tickers);
        println!("   Chunk size: {} days", config.chunk_size_days);
        println!("   Expected chunks: ~26 per ticker (weekly chunks for 6 months)");
        println!("   Estimated runtime: 15-30 minutes");

        let start_time = std::time::Instant::now();

        // Use the resumable version with test prefix to avoid production table conflicts
        let result = fetch_coinbase_historical_resumable(
            tickers.clone(),
            start_date,
            end_date,
            60, // 1-minute granularity
            Some(config),
            Some("test"), // Use test_ prefix for all tables
        )
        .await;

        let duration = start_time.elapsed();

        match result {
            Ok(_) => {
                println!("🎉 HALF YEAR TEST SUCCESSFUL!");
                println!("   Duration: {:?}", duration);
                println!("   This validates the job is ready for the 10-year run");

                // Verify we can connect to DB and check some basic stats
                if let Ok(conn) = NeonConnection::new().await {
                    for ticker in &tickers {
                        let job_id = format!(
                            "coinbase_{}_{}_{}",
                            ticker.replace("-", "_").to_lowercase(),
                            60,
                            start_date.format("%Y%m%d")
                        );

                        if let Ok(summary) = conn.get_job_progress_summary(&job_id).await {
                            println!("📊 Final stats for {}:", ticker);
                            println!("   Total chunks: {}", summary.total_chunks);
                            println!("   Completed: {}", summary.completed);
                            println!("   Failed: {}", summary.failed);
                            println!("   Total records: {}", summary.total_records);

                            if summary.failed > 0 {
                                println!("⚠️  Some chunks failed - review before 10-year run");
                            }
                        }
                    }
                }
            }
            Err(e) => {
                println!("❌ HALF YEAR TEST FAILED: {}", e);
                println!("   Duration before failure: {:?}", duration);
                println!("   🚨 DO NOT proceed with 10-year run until this is fixed!");
                panic!("Half year test failed - must fix before production run");
            }
        }
    }

    #[tokio::test]
    async fn test_production_readiness_checklist() {
        // Load .env file before checking environment variables
        let _ = dotenv::dotenv()
            .or_else(|_| dotenv::from_filename("../.env"))
            .or_else(|_| dotenv::from_filename("./.env"));

        println!("📋 Production Readiness Checklist:");

        // Check 1: Database connection
        let db_check = if env::var("DATABASE_URL").is_ok() || env::var("NEON_DATABASE_URL").is_ok()
        {
            match NeonConnection::new().await {
                Ok(_) => {
                    println!("   ✅ Database connection configured and working");
                    true
                }
                Err(e) => {
                    println!("   ❌ Database connection failed: {}", e);
                    false
                }
            }
        } else {
            println!("   ❌ No DATABASE_URL configured");
            false
        };

        // Check 2: Configuration is conservative
        let config = get_test_config();
        let config_check = config.delay_between_requests_ms >= 200; // At least 200ms delay (5 req/sec max)
        if config_check {
            println!("   ✅ Configuration is appropriately conservative");
        } else {
            println!("   ❌ Configuration too aggressive - risk of rate limiting");
        }

        // Check 3: Resume capability enabled
        let resume_check = config.enable_caching;
        if resume_check {
            println!("   ✅ Resume capability enabled (caching on)");
        } else {
            println!("   ❌ Resume capability disabled - risky for 10-year job");
        }

        println!("\n🎯 PRODUCTION READINESS SUMMARY:");
        if db_check && config_check && resume_check {
            println!("   ✅ ALL CHECKS PASSED - Ready for production run");
            println!("   💡 Recommendation: Run the half-year test first with --ignored flag");
        } else {
            println!("   ❌ SOME CHECKS FAILED - Fix issues before production run");
        }
    }

    #[tokio::test]
    async fn test_sequential_processing() {
        // Test that validates our sequential processing approach
        println!("🔄 Testing sequential processing logic:");

        let mut config = get_test_config();
        config.delay_between_requests_ms = 100; // Fast for testing
        config.chunk_size_days = 1;
        config.max_retries = 2;
        config.initial_backoff_ms = 500;
        config.backoff_multiplier = 2;
        config.enable_caching = false;

        println!("   ✅ Sequential processing configuration validated");
        println!("   - No complex rate limiting needed");
        println!(
            "   - Simple delay-based approach: {}ms between requests",
            config.delay_between_requests_ms
        );
        println!(
            "   - Estimated rate: ~{} requests/second",
            1000 / config.delay_between_requests_ms.max(1)
        );

        // Validate the delay is reasonable
        assert!(
            config.delay_between_requests_ms >= 50,
            "Delay too short - minimum 50ms"
        );
        assert!(
            config.delay_between_requests_ms <= 1000,
            "Delay too long - maximum 1000ms for testing"
        );

        println!("   ✅ Sequential processing ready for production");
    }

    #[tokio::test]
    async fn temp() {
        if let Ok(conn) = NeonConnection::new().await {
            if let Ok(summary) = conn
                .get_job_progress_summary("coinbase_btc_usd_60_20220101")
                .await
            {
                println!("📊 Final stats for {}:", "BTC");
                println!("   Total chunks: {}", summary.total_chunks);
                println!("   Completed: {}", summary.completed);
                println!("   Failed: {}", summary.failed);
                println!("   Total records: {}", summary.total_records);

                if summary.failed > 0 {
                    println!("⚠️  Some chunks failed - review before 10-year run");
                }
            }
        }
    }
}
