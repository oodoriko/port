// nohup cargo run > etl.log 2>&1 &
use anyhow::Result;
use chrono::{DateTime, Utc};

use std::sync::Arc;
use tokio::time::{sleep, Duration as TokioDuration};

use crate::coinbase_service::{fetch_ohlcv_data_single, CoinbaseConfig};
use crate::http_utils::create_time_chunks;
use crate::postgres_service::{JobProgressSummary, NeonConnection};

/// Resumable ETL function that processes tickers sequentially
/// If table_prefix is provided, tables will be named: {prefix}_historical_coinbase_{ticker}
/// Otherwise: historical_coinbase_{ticker}
pub async fn fetch_coinbase_historical_resumable(
    tickers: Vec<String>,
    start_date: DateTime<Utc>,
    end_date: DateTime<Utc>,
    granularity: u32,
    config: Option<CoinbaseConfig>,
    table_prefix: Option<&str>,
) -> Result<()> {
    let config = config.unwrap_or_else(|| CoinbaseConfig::default());

    println!(
        "🚀 Starting ETL job for {} tickers from {} to {}",
        tickers.len(),
        start_date.format("%Y-%m-%d"),
        end_date.format("%Y-%m-%d")
    );

    // Initialize database connection
    let db_connection = if config.enable_caching {
        match NeonConnection::new().await {
            Ok(conn) => {
                println!("📦 Database caching enabled");

                // Ensure the ETL progress table exists
                if let Err(e) = conn.create_etl_progress_table().await {
                    return Err(anyhow::anyhow!(
                        "Failed to create ETL progress table: {}",
                        e
                    ));
                }

                Arc::new(conn)
            }
            Err(e) => {
                return Err(anyhow::anyhow!("Failed to connect to database: {}", e));
            }
        }
    } else {
        return Err(anyhow::anyhow!("Caching must be enabled for resumable ETL"));
    };

    // Simple sequential processing - no complex rate limiting needed

    // Process each ticker independently for better resume granularity
    for ticker in tickers {
        println!("\n🎯 Processing ticker: {}", ticker);

        let job_id = format!(
            "coinbase_{}_{}_{}",
            ticker.replace("-", "_").to_lowercase(),
            granularity,
            start_date.format("%Y%m%d")
        );

        // Create chunks for this ticker
        let all_chunks = create_time_chunks(start_date, end_date, config.chunk_size_days);

        // Initialize job plan (creates entries if they don't exist)
        db_connection
            .create_etl_job_plan(&job_id, "coinbase", &ticker, granularity, &all_chunks)
            .await?;

        // Get current progress
        let progress = db_connection.get_job_progress_summary(&job_id).await?;
        print_progress_summary(&progress);

        // Get pending chunks (resume capability!)
        let pending_chunks = db_connection.get_pending_chunks(&job_id).await?;

        if pending_chunks.is_empty() {
            println!("✅ Ticker {} already completed!", ticker);
            continue;
        }

        println!(
            "🔄 Processing {} pending chunks for {} ({}% complete)",
            pending_chunks.len(),
            ticker,
            ((progress.completed as f32 / progress.total_chunks as f32) * 100.0) as u32
        );

        // Process pending chunks sequentially
        for (chunk_idx, (chunk_start, chunk_end)) in pending_chunks.iter().enumerate() {
            println!(
                "🔄 Processing chunk {}/{}: {} to {}",
                chunk_idx + 1,
                pending_chunks.len(),
                chunk_start.format("%Y-%m-%d %H:%M:%S"),
                chunk_end.format("%Y-%m-%d %H:%M:%S")
            );

            // Mark chunk as in progress
            db_connection
                .mark_chunk_in_progress(&job_id, *chunk_start)
                .await?;

            // Process the chunk
            match process_single_chunk(
                &ticker,
                *chunk_start,
                *chunk_end,
                granularity,
                &config,
                &db_connection,
                table_prefix,
            )
            .await
            {
                Ok((records_fetched, records_cached)) => {
                    // Mark as completed
                    db_connection
                        .mark_chunk_completed(
                            &job_id,
                            *chunk_start,
                            records_fetched,
                            records_cached,
                        )
                        .await?;
                }
                Err(e) => {
                    // Mark as failed
                    db_connection
                        .mark_chunk_failed(&job_id, *chunk_start, &e.to_string())
                        .await?;

                    println!("❌ Failed chunk: {}", e);

                    // Continue with other chunks instead of failing entire job
                    continue;
                }
            }

            // Add delay between chunks
            if chunk_idx < pending_chunks.len() - 1 {
                let inter_chunk_delay =
                    TokioDuration::from_millis(config.delay_between_requests_ms);
                sleep(inter_chunk_delay).await;
            }
        }

        // Retry failed chunks with exponential backoff
        println!("\n🔄 Checking for failed chunks to retry...");
        retry_failed_chunks(
            &job_id,
            &ticker,
            granularity,
            &config,
            &db_connection,
            3, // max retries
            table_prefix,
        )
        .await?;

        // Final progress summary
        let final_progress = db_connection.get_job_progress_summary(&job_id).await?;
        print_progress_summary(&final_progress);

        if final_progress.failed > 0 {
            println!(
                "⚠️  Ticker {} completed with {} failed chunks",
                ticker, final_progress.failed
            );
        } else {
            println!("✅ Ticker {} completed successfully!", ticker);
        }
    }

    println!("🎉 All tickers processed!");
    Ok(())
}

/// Process a single chunk and return (records_fetched, records_cached)
async fn process_single_chunk(
    ticker: &str,
    chunk_start: DateTime<Utc>,
    chunk_end: DateTime<Utc>,
    granularity: u32,
    config: &CoinbaseConfig,
    db_connection: &Arc<NeonConnection>,
    table_prefix: Option<&str>,
) -> Result<(usize, usize)> {
    // Fetch data for single ticker
    let data = fetch_ohlcv_data_single(ticker, chunk_start, chunk_end, granularity, config).await?;

    let records_fetched = data.len();

    // Cache the data
    let records_cached = if !data.is_empty() {
        let mut chunk_data_to_cache = std::collections::HashMap::new();
        chunk_data_to_cache.insert(ticker.to_string(), data);

        db_connection
            .cache_historical_ohlcv("coinbase", chunk_data_to_cache, table_prefix)
            .await
            .map_err(|e| anyhow::anyhow!("Caching failed: {}", e))?;

        records_fetched
    } else {
        0
    };

    Ok((records_fetched, records_cached))
}

/// Retry failed chunks with exponential backoff
async fn retry_failed_chunks(
    job_id: &str,
    ticker: &str,
    granularity: u32,
    config: &CoinbaseConfig,
    db_connection: &Arc<NeonConnection>,
    max_retries: u32,
    table_prefix: Option<&str>,
) -> Result<()> {
    let retryable_chunks = db_connection
        .get_retryable_chunks(job_id, max_retries)
        .await?;

    if retryable_chunks.is_empty() {
        println!("✅ No failed chunks to retry");
        return Ok(());
    }

    println!("🔄 Retrying {} failed chunks", retryable_chunks.len());

    for (chunk_start, chunk_end, retry_count) in retryable_chunks {
        let backoff_ms = config.initial_backoff_ms * config.backoff_multiplier.pow(retry_count);
        println!(
            "🔄 Retrying chunk: {} to {} (attempt {}/{})",
            chunk_start.format("%Y-%m-%d %H:%M:%S"),
            chunk_end.format("%Y-%m-%d %H:%M:%S"),
            retry_count + 1,
            max_retries
        );

        // Exponential backoff delay
        sleep(TokioDuration::from_millis(backoff_ms)).await;

        // Mark chunk as in progress
        db_connection
            .mark_chunk_in_progress(job_id, chunk_start)
            .await?;

        // Retry processing the chunk
        match process_single_chunk(
            ticker,
            chunk_start,
            chunk_end,
            granularity,
            config,
            db_connection,
            table_prefix,
        )
        .await
        {
            Ok((records_fetched, records_cached)) => {
                // Mark as completed
                db_connection
                    .mark_chunk_completed(job_id, chunk_start, records_fetched, records_cached)
                    .await?;
                println!("✅ Successfully retried chunk");
            }
            Err(e) => {
                // Mark as failed again
                db_connection
                    .mark_chunk_failed(job_id, chunk_start, &e.to_string())
                    .await?;
                println!("❌ Retry failed: {}", e);
            }
        }
    }

    Ok(())
}

fn print_progress_summary(progress: &JobProgressSummary) {
    println!(
        "📊 Progress: {} completed, {} pending, {} failed, {} in progress (total: {})",
        progress.completed,
        progress.pending,
        progress.failed,
        progress.in_progress,
        progress.total_chunks
    );
}
