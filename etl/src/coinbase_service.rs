use anyhow::Result;
use chrono::{DateTime, TimeZone, Utc};
use chrono_tz::America::New_York;
use governor::{
    clock::DefaultClock,
    middleware::NoOpMiddleware,
    state::{InMemoryState, NotKeyed},
    Quota, RateLimiter,
};
use reqwest;
use std::cmp::min;
use std::num::NonZeroU32;
use std::sync::Arc;

const MAX_CANDLES_PER_REQUEST: u32 = 250;

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
    rate_limiter: Arc<RateLimiter<NotKeyed, InMemoryState, DefaultClock, NoOpMiddleware>>,
}

impl CoinbaseDataFetcher {
    pub fn new() -> Self {
        let rate = NonZeroU32::new(3).unwrap();
        let quota = Quota::per_second(rate);
        let rate_limiter = Arc::new(RateLimiter::direct(quota));
        Self { rate_limiter }
    }

    async fn fetch_single_chunk(
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

        self.rate_limiter.until_ready().await;

        let response = reqwest::Client::new()
            .get(&url)
            .header("User-Agent", "bikini-bottom/0.1.0")
            .query(&[
                ("start", start.to_rfc3339()),
                ("end", end.to_rfc3339()),
                ("granularity", granularity.to_string()),
            ])
            .send()
            .await?;

        if !response.status().is_success() {
            let error_text = response.text().await?;
            return Err(anyhow::anyhow!("Coinbase API error: {}", error_text));
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
    ) -> Result<Vec<OhlcvData>> {
        println!("Fetching candles for {} from {} to {}", symbol, start, end);

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

            // Add delay between chunks to respect rate limits
            tokio::time::sleep(tokio::time::Duration::from_secs(1)).await;
        }

        println!("Total {} candles fetched for {}", all_candles.len(), symbol);
        Ok(all_candles)
    }

    pub async fn fetch_historical_data(
        &self,
        tickers: &[&str],
        start: DateTime<Utc>,
        end: DateTime<Utc>,
        granularity: u32,
    ) -> Result<Vec<(String, Vec<OhlcvData>)>> {
        let mut all_ticker_data = Vec::new();

        for ticker in tickers {
            println!("Fetching historical data for {}", ticker);

            let candles = self.fetch_candles(ticker, start, end, granularity).await?;

            println!(
                "Completed fetching {} candles for {}",
                candles.len(),
                ticker
            );
            all_ticker_data.push((ticker.to_string(), candles));

            // Add delay between tickers to be respectful
            tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
        }

        Ok(all_ticker_data)
    }
}
