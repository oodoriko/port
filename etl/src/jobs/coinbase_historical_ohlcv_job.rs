use anyhow::Result;
use chrono::{DateTime, Utc};
use governor::{
    clock::DefaultClock,
    middleware::NoOpMiddleware,
    state::{InMemoryState, NotKeyed},
    Quota, RateLimiter,
};
use std::collections::HashMap;
use std::num::NonZeroU32;
use std::sync::Arc;
use tokio::fs;
use tokio::time::{sleep, Duration as TokioDuration};

use crate::coinbase_service::{
    fetch_ohlcv_data_multithread, CoinbaseMultiThreadConfig, MAX_TICKERS,
};
use crate::http_utils::create_time_chunks;
use crate::postgres_service::{JobProgressSummary, NeonConnection};

/// Guard to ensure lock file is cleaned up
struct LockGuard {
    lock_file: String,
}

impl Drop for LockGuard {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.lock_file);
        println!("🔓 ETL lock released");
    }
}

pub async fn fetch_coinbase_historical_multithread(
    tickers: Vec<String>,
    start_date: DateTime<Utc>,
    end_date: DateTime<Utc>,
    granularity: u32,
    config: Option<CoinbaseMultiThreadConfig>,
) -> Result<()> {
    let config = config.unwrap_or_else(|| CoinbaseMultiThreadConfig::default());

    // Validate and limit tickers
    if tickers.len() > MAX_TICKERS {
        return Err(anyhow::anyhow!(
            "Too many tickers requested: {}. Maximum allowed: {}",
            tickers.len(),
            MAX_TICKERS
        ));
    }

    let total_tickers = tickers.len();
    let max_concurrent = config.max_concurrent.min(total_tickers);

    // Create global rate limiter (5 requests per second total)
    let rate_limit = NonZeroU32::new(config.max_requests_per_second).unwrap();
    let quota = Quota::per_second(rate_limit);
    let global_rate_limiter = Arc::new(RateLimiter::direct(quota));

    // Calculate per-thread sleep interval: threads / 5 seconds
    let per_thread_sleep_ms = if max_concurrent > 0 {
        (max_concurrent as f64 / config.max_requests_per_second as f64 * 1000.0) as u64
    } else {
        1000
    };

    println!(
        "Caching historical ohlcv from coinbase: {} tickers from {} to {}\nConfig: {} concurrent, {}ms/thread sleep, {} max retries",
        total_tickers,
        start_date.format("%Y-%m-%d"),
        end_date.format("%Y-%m-%d"),
        max_concurrent,
        per_thread_sleep_ms,
        config.max_retries
    );

    // Initialize database connection for caching (if enabled)
    let db_connection = if config.enable_caching {
        match NeonConnection::new().await {
            Ok(conn) => {
                println!("📦 Database caching enabled");
                Some(Arc::new(conn))
            }
            Err(e) => {
                println!("⚠️  Database caching disabled: {}", e);
                None
            }
        }
    } else {
        println!("📦 Database caching disabled");
        None
    };

    // Create chunks of time periods
    let chunks = create_time_chunks(start_date, end_date, config.chunk_size_days);
    let total_chunks = chunks.len();

    println!(
        "📅 Processing {} time chunks of {} days each",
        total_chunks, config.chunk_size_days
    );

    let mut active_tickers = tickers.clone(); // Keep track of tickers that still have data

    // Process each time chunk sequentially (to avoid overwhelming the API), 1 month at a time!!
    for (chunk_idx, (chunk_start, chunk_end)) in chunks.iter().enumerate() {
        println!(
            "\n🔄 Processing chunk {}/{}: {} to {} ({} active tickers)",
            chunk_idx + 1,
            total_chunks,
            chunk_start.format("%Y-%m-%d %H:%M:%S"),
            chunk_end.format("%Y-%m-%d %H:%M:%S"),
            active_tickers.len()
        );

        // Skip processing if no active tickers remain
        if active_tickers.is_empty() {
            println!("ℹ️  No active tickers remaining, skipping remaining chunks");
            break;
        }

        // Process tickers concurrently for this chunk
        let chunk_results = fetch_ohlcv_data_multithread(
            &active_tickers,
            *chunk_start,
            *chunk_end,
            granularity,
            &config,
            &global_rate_limiter,
            per_thread_sleep_ms,
        )
        .await?;

        // Track tickers with no data and prepare chunk data for caching
        let mut tickers_with_no_data = Vec::new();
        let mut chunk_data_to_cache = HashMap::new();

        for (ticker, data) in chunk_results {
            if data.is_empty() {
                println!(
                    "⚠️  No data found for ticker: {} in chunk {}",
                    ticker,
                    chunk_idx + 1
                );
                tickers_with_no_data.push(ticker);
            } else {
                println!(
                    "📊 Found {} records for {} in chunk {}",
                    data.len(),
                    ticker,
                    chunk_idx + 1
                );
                chunk_data_to_cache.insert(ticker, data);
            }
        }

        // Remove tickers with no data from active list to avoid processing them in future chunks
        if !tickers_with_no_data.is_empty() {
            active_tickers.retain(|ticker| !tickers_with_no_data.contains(ticker));
            println!(
                "🗑️  Removed {} tickers with no data from future processing",
                tickers_with_no_data.len()
            );
        }

        // Cache the chunk data immediately (only current chunk, not accumulated data)
        if let Some(db) = &db_connection {
            if !chunk_data_to_cache.is_empty() {
                if let Err(e) = db
                    .cache_historical_ohlcv("coinbase", chunk_data_to_cache, None)
                    .await
                {
                    println!("⚠️  Failed to cache chunk data: {}", e);
                } else {
                    println!("💾 Chunk data cached successfully");
                }
            } else {
                println!("ℹ️  No data to cache for this chunk");
            }
        }

        // Add delay between chunks to be extra conservative
        if chunk_idx < total_chunks - 1 {
            let inter_chunk_delay = TokioDuration::from_millis(per_thread_sleep_ms * 3); // Even more conservative
            println!("⏸️  Inter-chunk delay: {:?}", inter_chunk_delay);
            sleep(inter_chunk_delay).await;
        }
    }
    Ok(())
}

/// ===== RESUMABLE ETL WITH PROGRESS TRACKING =====

/// Resumable ETL function that can pick up where it left off
/// If table_prefix is provided, tables will be named: {prefix}_historical_coinbase_{ticker}
/// Otherwise: historical_coinbase_{ticker}
pub async fn fetch_coinbase_historical_resumable(
    tickers: Vec<String>,
    start_date: DateTime<Utc>,
    end_date: DateTime<Utc>,
    granularity: u32,
    config: Option<CoinbaseMultiThreadConfig>,
    table_prefix: Option<&str>,
) -> Result<()> {
    let config = config.unwrap_or_else(|| CoinbaseMultiThreadConfig::default());

    // Simple process lock to prevent concurrent ETL runs
    let lock_file = "/tmp/coinbase_etl.lock";
    if fs::metadata(lock_file).await.is_ok() {
        return Err(anyhow::anyhow!(
            "Another ETL process is already running. Lock file exists: {}",
            lock_file
        ));
    }

    // Create lock file
    fs::write(lock_file, std::process::id().to_string()).await?;
    println!("🔒 ETL lock acquired");

    // Ensure lock file is cleaned up on exit
    let _lock_guard = LockGuard {
        lock_file: lock_file.to_string(),
    };

    // Validate and limit tickers
    if tickers.len() > MAX_TICKERS {
        return Err(anyhow::anyhow!(
            "Too many tickers requested: {}. Maximum allowed: {}",
            tickers.len(),
            MAX_TICKERS
        ));
    }

    // Initialize database connection for progress tracking and caching
    let db_connection = match NeonConnection::new().await {
        Ok(conn) => Arc::new(conn),
        Err(e) => {
            return Err(anyhow::anyhow!("Failed to connect to database: {}", e));
        }
    };

    // Ensure progress tracking table exists
    db_connection.create_etl_progress_table().await?;

    // Create global rate limiter
    let rate_limit = NonZeroU32::new(config.max_requests_per_second).unwrap();
    let quota = Quota::per_second(rate_limit);
    let global_rate_limiter = Arc::new(RateLimiter::direct(quota));

    let max_concurrent = config.max_concurrent.min(tickers.len());
    let per_thread_sleep_ms = if max_concurrent > 0 {
        (max_concurrent as f64 / config.max_requests_per_second as f64 * 1000.0) as u64
    } else {
        1000
    };

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

        // Process pending chunks
        let active_tickers = vec![ticker.clone()];

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
                &active_tickers,
                *chunk_start,
                *chunk_end,
                granularity,
                &config,
                &global_rate_limiter,
                per_thread_sleep_ms,
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
                let inter_chunk_delay = TokioDuration::from_millis(per_thread_sleep_ms * 2);
                sleep(inter_chunk_delay).await;
            }
        }

        // Retry failed chunks with exponential backoff
        println!("\n🔄 Checking for failed chunks to retry...");
        retry_failed_chunks(
            &job_id,
            &active_tickers,
            granularity,
            &config,
            &global_rate_limiter,
            per_thread_sleep_ms,
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

/// Process a single chunk with optional table prefix and return (records_fetched, records_cached)
async fn process_single_chunk(
    tickers: &[String],
    chunk_start: DateTime<Utc>,
    chunk_end: DateTime<Utc>,
    granularity: u32,
    config: &CoinbaseMultiThreadConfig,
    global_rate_limiter: &Arc<RateLimiter<NotKeyed, InMemoryState, DefaultClock, NoOpMiddleware>>,
    per_thread_sleep_ms: u64,
    db_connection: &Arc<NeonConnection>,
    table_prefix: Option<&str>,
) -> Result<(usize, usize)> {
    // Fetch data using existing multithread function
    let chunk_results = fetch_ohlcv_data_multithread(
        tickers,
        chunk_start,
        chunk_end,
        granularity,
        config,
        global_rate_limiter,
        per_thread_sleep_ms,
    )
    .await?;

    let mut total_fetched = 0;
    let mut chunk_data_to_cache = HashMap::new();

    for (ticker, data) in chunk_results {
        if !data.is_empty() {
            total_fetched += data.len();
            chunk_data_to_cache.insert(ticker, data);
        }
    }

    // Cache the data
    let mut total_cached = 0;
    if !chunk_data_to_cache.is_empty() {
        // Count total records before caching
        for data in chunk_data_to_cache.values() {
            total_cached += data.len();
        }

        db_connection
            .cache_historical_ohlcv("coinbase", chunk_data_to_cache, table_prefix)
            .await
            .map_err(|e| anyhow::anyhow!("Caching failed: {}", e))?;
    }

    Ok((total_fetched, total_cached))
}

/// Retry failed chunks with exponential backoff
async fn retry_failed_chunks(
    job_id: &str,
    tickers: &[String],
    granularity: u32,
    config: &CoinbaseMultiThreadConfig,
    global_rate_limiter: &Arc<RateLimiter<NotKeyed, InMemoryState, DefaultClock, NoOpMiddleware>>,
    per_thread_sleep_ms: u64,
    db_connection: &Arc<NeonConnection>,
    max_retries: u32,
    table_prefix: Option<&str>,
) -> Result<()> {
    let retryable_chunks = db_connection
        .get_retryable_chunks(job_id, max_retries)
        .await?;

    if retryable_chunks.is_empty() {
        println!("ℹ️  No failed chunks to retry");
        return Ok(());
    }

    println!("🔄 Retrying {} failed chunks", retryable_chunks.len());

    for (chunk_start, chunk_end, retry_count) in retryable_chunks {
        // Exponential backoff: 2^retry_count seconds
        let backoff_delay = TokioDuration::from_secs(2_u64.pow(retry_count));
        println!(
            "⏳ Retrying chunk {} (attempt {}/{}) after {:?} delay",
            chunk_start.format("%Y-%m-%d %H:%M:%S"),
            retry_count + 1,
            max_retries,
            backoff_delay
        );

        sleep(backoff_delay).await;

        // Mark as in progress
        db_connection
            .mark_chunk_in_progress(job_id, chunk_start)
            .await?;

        // Retry the chunk
        match process_single_chunk(
            tickers,
            chunk_start,
            chunk_end,
            granularity,
            config,
            global_rate_limiter,
            per_thread_sleep_ms,
            db_connection,
            table_prefix,
        )
        .await
        {
            Ok((records_fetched, records_cached)) => {
                db_connection
                    .mark_chunk_completed(job_id, chunk_start, records_fetched, records_cached)
                    .await?;

                println!("✅ Retry successful: {} records cached", records_cached);
            }
            Err(e) => {
                db_connection
                    .mark_chunk_failed(job_id, chunk_start, &e.to_string())
                    .await?;

                println!("❌ Retry failed: {}", e);
            }
        }
    }

    Ok(())
}

/// Print a nicely formatted progress summary
fn print_progress_summary(progress: &JobProgressSummary) {
    let percentage = if progress.total_chunks > 0 {
        (progress.completed as f32 / progress.total_chunks as f32) * 100.0
    } else {
        0.0
    };

    println!("📊 Progress Summary for {}", progress.job_id);
    println!("   Total chunks: {}", progress.total_chunks);
    println!(
        "   ✅ Completed: {} ({:.1}%)",
        progress.completed, percentage
    );
    println!("   ❌ Failed: {}", progress.failed);
    println!("   🔄 In Progress: {}", progress.in_progress);
    println!("   ⏳ Pending: {}", progress.pending);
    println!("   📊 Total Records: {}", progress.total_records);
}
