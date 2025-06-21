use anyhow::Result;
use chrono::{DateTime, TimeZone, Utc};
use chrono_tz::America::New_York;
use std::cmp::min;
use tokio::time::{sleep, Duration as TokioDuration};

use crate::http_utils::{HttpClient, RetryConfig};

const MAX_CANDLES_PER_REQUEST: u32 = 250;
const MAX_RETRY_ATTEMPTS: u32 = 3;
const INITIAL_BACKOFF_MS: u64 = 1000;
const BACKOFF_MULTIPLIER: u64 = 2;
const CHUNK_SIZE_DAYS: i64 = 30;

#[derive(Debug, Clone)]
pub struct CoinbaseConfig {
    pub chunk_size_days: i64,
    pub max_retries: u32,
    pub initial_backoff_ms: u64,
    pub backoff_multiplier: u64,
    pub enable_caching: bool,
    pub delay_between_requests_ms: u64,
}

impl Default for CoinbaseConfig {
    fn default() -> Self {
        Self {
            chunk_size_days: CHUNK_SIZE_DAYS,
            max_retries: MAX_RETRY_ATTEMPTS,
            initial_backoff_ms: INITIAL_BACKOFF_MS,
            backoff_multiplier: BACKOFF_MULTIPLIER,
            enable_caching: true,
            delay_between_requests_ms: 250, // Simple 250ms delay between requests (~4 requests/second)
        }
    }
}

#[derive(Debug, Clone)]
pub struct OhlcvData {
    pub timestamp: i64,
    pub open: f32,
    pub high: f32,
    pub low: f32,
    pub close: f32,
    pub volume: f32,
}

impl OhlcvData {
    pub fn new(timestamp: i64, open: f32, high: f32, low: f32, close: f32, volume: f32) -> Self {
        Self {
            timestamp,
            open,
            high,
            low,
            close,
            volume,
        }
    }

    pub fn est_time(&self) -> DateTime<chrono_tz::Tz> {
        let utc_time = Utc.timestamp_opt(self.timestamp, 0).unwrap();
        utc_time.with_timezone(&New_York)
    }
}

pub struct CoinbaseDataFetcher {
    http_client: HttpClient,
}

impl CoinbaseDataFetcher {
    pub fn new() -> Self {
        Self {
            http_client: HttpClient::with_config(RetryConfig {
                max_retries: 3,
                initial_backoff_ms: 1000,
                backoff_multiplier: 2,
                timeout_seconds: 30,
            }),
        }
    }

    pub fn with_retry_config(retry_config: RetryConfig) -> Self {
        Self {
            http_client: HttpClient::with_config(retry_config),
        }
    }

    pub async fn fetch_single_chunk(
        &self,
        symbol: &str,
        start: DateTime<Utc>,
        end: DateTime<Utc>,
        granularity: u32,
    ) -> Result<Vec<OhlcvData>> {
        let url = format!(
            "https://api.exchange.coinbase.com/products/{}/candles",
            symbol
        );

        println!("Requesting URL: {}", url);
        println!(
            "Query params: start={}, end={}, granularity={}",
            start.to_rfc3339(),
            end.to_rfc3339(),
            granularity
        );

        let operation_name = format!("fetch_single_chunk({})", symbol);

        let response = self
            .http_client
            .execute_with_retry(&operation_name, || {
                self.http_client
                    .client()
                    .get(&url)
                    .header("User-Agent", "bikini-bottom/0.1.0")
                    .query(&[
                        ("start", start.to_rfc3339()),
                        ("end", end.to_rfc3339()),
                        ("granularity", granularity.to_string()),
                    ])
                    .send()
            })
            .await?;

        // Check for rate limiting status codes
        if response.status().as_u16() == 429 {
            return Err(anyhow::anyhow!(
                "Rate limited by Coinbase API (429). Consider increasing delays."
            ));
        }

        let candles: Vec<Vec<f32>> = response.json().await?;
        println!("Received {} candles from API", candles.len());

        let candles = candles
            .into_iter()
            .map(|candle| OhlcvData {
                timestamp: candle[0] as i64,
                open: candle[3],
                high: candle[2],
                low: candle[1],
                close: candle[4],
                volume: candle[5],
            })
            .collect();

        Ok(candles)
    }

    pub async fn fetch_candles(
        &self,
        symbol: &str,
        start: DateTime<Utc>,
        end: DateTime<Utc>,
        granularity: u32,
        delay_ms: Option<u64>,
    ) -> Result<Vec<OhlcvData>> {
        println!("Fetching candles for {} from {} to {}", symbol, start, end);
        let delay_ms = delay_ms.unwrap_or(250);

        let mut all_candles = Vec::new();
        let mut current_start = start;

        while current_start < end {
            let chunk_duration_seconds = (MAX_CANDLES_PER_REQUEST * granularity) as i64;
            let chunk_end = min(
                current_start + chrono::Duration::seconds(chunk_duration_seconds),
                end,
            );

            let chunk_candles = self
                .fetch_single_chunk(symbol, current_start, chunk_end, granularity)
                .await?;

            println!("Fetched {} candles for chunk", chunk_candles.len());
            all_candles.extend(chunk_candles);

            current_start = chunk_end;

            // Simple delay between chunks
            sleep(TokioDuration::from_millis(delay_ms)).await;
        }

        println!("Total {} candles fetched for {}", all_candles.len(), symbol);
        Ok(all_candles)
    }
}

impl Default for CoinbaseDataFetcher {
    fn default() -> Self {
        Self::new()
    }
}

pub async fn fetch_ohlcv_data_single(
    ticker: &str,
    start_date: DateTime<Utc>,
    end_date: DateTime<Utc>,
    granularity: u32,
    config: &CoinbaseConfig,
) -> Result<Vec<OhlcvData>> {
    // Create retry configuration based on ETL config
    let retry_config = RetryConfig {
        max_retries: config.max_retries,
        initial_backoff_ms: config.initial_backoff_ms,
        backoff_multiplier: config.backoff_multiplier,
        timeout_seconds: 30,
    };

    // Create fetcher with custom retry configuration
    let fetcher = CoinbaseDataFetcher::with_retry_config(retry_config);
    let result = fetcher
        .fetch_candles(
            ticker,
            start_date,
            end_date,
            granularity,
            Some(config.delay_between_requests_ms),
        )
        .await;

    match result {
        Ok(candles) => {
            println!("✅ {}: {} candles", ticker, candles.len());
            Ok(candles)
        }
        Err(e) => {
            println!("❌ {}: {}", ticker, e);
            Err(e)
        }
    }
}
