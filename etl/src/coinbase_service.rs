use anyhow::Result;
use base64::{engine::general_purpose, Engine as _};
use chrono::{DateTime, TimeZone, Utc};
use chrono_tz::America::New_York;
use hmac::{Hmac, Mac};
use sha2::Sha256;
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
    pub api_key_id: String,
    pub private_key: String,
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
            api_key_id: String::new(),
            private_key: String::new(),
        }
    }
}

impl CoinbaseConfig {
    pub fn with_credentials(api_key_id: String, private_key: String) -> Self {
        Self {
            chunk_size_days: CHUNK_SIZE_DAYS,
            max_retries: MAX_RETRY_ATTEMPTS,
            initial_backoff_ms: INITIAL_BACKOFF_MS,
            backoff_multiplier: BACKOFF_MULTIPLIER,
            enable_caching: true,
            delay_between_requests_ms: 250,
            api_key_id,
            private_key,
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
    config: CoinbaseConfig,
}

impl CoinbaseDataFetcher {
    pub fn new(config: CoinbaseConfig) -> Self {
        Self {
            http_client: HttpClient::with_config(RetryConfig {
                max_retries: config.max_retries,
                initial_backoff_ms: config.initial_backoff_ms,
                backoff_multiplier: config.backoff_multiplier,
                timeout_seconds: 30,
            }),
            config,
        }
    }

    pub fn with_retry_config(retry_config: RetryConfig, config: CoinbaseConfig) -> Self {
        Self {
            http_client: HttpClient::with_config(retry_config),
            config,
        }
    }

    fn generate_signature(
        &self,
        timestamp: u64,
        method: &str,
        path: &str,
        body: &str,
    ) -> Result<String> {
        let message = format!("{}{}{}{}", timestamp, method, path, body);
        let decoded_key = general_purpose::STANDARD.decode(&self.config.private_key)?;

        let mut mac = Hmac::<Sha256>::new_from_slice(&decoded_key)
            .map_err(|e| anyhow::anyhow!("Invalid key: {}", e))?;
        mac.update(message.as_bytes());
        let signature = mac.finalize().into_bytes();

        Ok(general_purpose::STANDARD.encode(signature))
    }

    // Convert numeric granularity to brokerage API format
    fn convert_granularity_to_brokerage_format(&self, granularity: u32) -> String {
        match granularity {
            60 => "ONE_MINUTE".to_string(),
            300 => "FIVE_MINUTE".to_string(),
            900 => "FIFTEEN_MINUTE".to_string(),
            3600 => "ONE_HOUR".to_string(),
            21600 => "SIX_HOUR".to_string(),
            86400 => "ONE_DAY".to_string(),
            _ => granularity.to_string(), // Fallback to numeric value
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
            "https://api.coinbase.com/api/v3/brokerage/market/products/{}/candles",
            symbol
        );
        let path = format!("/api/v3/brokerage/market/products/{}/candles", symbol);
        let method = "GET";
        let body = "";

        // Generate timestamp for authentication
        let timestamp = Utc::now().timestamp() as u64;

        // Generate signature for authentication
        let signature = self.generate_signature(timestamp, method, &path, body)?;

        // Convert granularity to brokerage API format
        let granularity_str = self.convert_granularity_to_brokerage_format(granularity);

        println!("Requesting URL: {}", url);
        println!(
            "Query params for {}: start={}, end={}, granularity={}",
            symbol,
            start.timestamp(),
            end.timestamp(),
            granularity_str
        );

        let operation_name = format!("fetch_single_chunk({})", symbol);

        let response = self
            .http_client
            .execute_with_retry(&operation_name, || {
                self.http_client
                    .client()
                    .get(&url)
                    .header("User-Agent", "bikini-bottom/0.1.0")
                    .header("CB-ACCESS-KEY", &self.config.api_key_id)
                    .header("CB-ACCESS-SIGN", &signature)
                    .header("CB-ACCESS-TIMESTAMP", timestamp.to_string())
                    .query(&[
                        ("start", &start.timestamp().to_string()),
                        ("end", &end.timestamp().to_string()),
                        ("granularity", &granularity_str),
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

        // The brokerage API returns a JSON object with a "candles" array
        let api_response: serde_json::Value = response.json().await?;
        let candles_array = api_response["candles"]
            .as_array()
            .ok_or_else(|| anyhow::anyhow!("No candles array found in response"))?;

        println!("Received {} candles from API", candles_array.len());

        let candles = candles_array
            .iter()
            .filter_map(|candle_obj| {
                let candle = candle_obj.as_object()?;
                Some(OhlcvData {
                    timestamp: candle.get("start")?.as_str()?.parse::<i64>().ok()?,
                    open: candle.get("open")?.as_str()?.parse::<f32>().ok()?,
                    high: candle.get("high")?.as_str()?.parse::<f32>().ok()?,
                    low: candle.get("low")?.as_str()?.parse::<f32>().ok()?,
                    close: candle.get("close")?.as_str()?.parse::<f32>().ok()?,
                    volume: candle.get("volume")?.as_str()?.parse::<f32>().ok()?,
                })
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
        Self::new(CoinbaseConfig::default())
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
    let fetcher = CoinbaseDataFetcher::with_retry_config(retry_config, config.clone());
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
