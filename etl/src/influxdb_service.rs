use anyhow::Result;
use chrono::{DateTime, TimeZone, Utc};
use chrono_tz::America::New_York;
use dotenv::dotenv;
use futures::stream;
use influxdb2::models::DataPoint;
use influxdb2::models::Query;
use influxdb2::Client;
use influxdb2_structmap::value::Value;
use reqwest;
use std::env;

use crate::coinbase_service::OhlcvData;

pub struct InfluxDBHandler {
    client: Client,
    bucket: String,
}

impl InfluxDBHandler {
    pub fn new() -> Result<Self> {
        // Try to load .env from multiple possible locations
        let _ = dotenv()
            .or_else(|_| dotenv::from_filename("../etl/.env"))
            .or_else(|_| dotenv::from_filename("etl/.env"))
            .or_else(|_| dotenv::from_filename("./.env"));

        let host = env::var("INFLUXDB_URL").unwrap_or_else(|_| "http://localhost:8086".to_string());
        let token = env::var("INFLUXDB_TOKEN").expect("INFLUXDB_TOKEN must be set");
        let org = env::var("INFLUXDB_ORG").expect("INFLUXDB_ORG must be set");
        let bucket = env::var("INFLUXDB_BUCKET").expect("INFLUXDB_BUCKET must be set");

        let client = Client::new(host, org, token);

        Ok(Self { client, bucket })
    }

    pub async fn cache_ohlcv_data(
        &self,
        exchange: &str,
        ticker: &str,
        candles: &[OhlcvData],
    ) -> Result<()> {
        let asset = ticker.split('-').next().unwrap().to_lowercase();
        let measurement = format!("sample_{}_{}", exchange.to_lowercase(), asset);

        println!(
            "Caching {} candles for {} on {}",
            candles.len(),
            ticker,
            exchange
        );

        let mut points = Vec::with_capacity(candles.len());

        for candle in candles {
            let utc_time = Utc.timestamp_opt(candle.timestamp, 0).unwrap();
            let est_time = utc_time.with_timezone(&New_York);

            let point = DataPoint::builder(measurement.as_str())
                .field("open", candle.open as f64)
                .field("high", candle.high as f64)
                .field("low", candle.low as f64)
                .field("close", candle.close as f64)
                .field("volume", candle.volume as f64)
                .field("est_timestamp", est_time.timestamp())
                .timestamp(candle.timestamp * 1_000_000_000)
                .build()
                .unwrap();

            points.push(point);
        }

        self.client
            .write(&self.bucket, stream::iter(points))
            .await?;

        println!(
            "Successfully cached {} candles for {}",
            candles.len(),
            ticker
        );
        Ok(())
    }

    pub async fn drop_measurement(&self, measurement_name: &str) -> Result<()> {
        println!("Dropping measurement: {}", measurement_name);

        let delete_body = format!(
            r#"{{"start":"1970-01-01T00:00:00Z","stop":"2030-01-01T00:00:00Z","predicate":"_measurement=\"{}\""}}"#,
            measurement_name
        );

        let url = format!("http://localhost:8086/api/v2/delete?org=bikini-bottom&bucket=patrick");

        let response = reqwest::Client::new()
            .post(&url)
            .header(
                "Authorization",
                format!(
                    "Token {}",
                    env::var("INFLUXDB_TOKEN").expect("INFLUXDB_TOKEN must be set")
                ),
            )
            .header("Content-Type", "application/json")
            .body(delete_body)
            .send()
            .await?;

        if response.status().is_success() {
            println!("Successfully dropped measurement: {}", measurement_name);
        } else {
            let error_text = response.text().await?;
            println!(
                "Failed to drop measurement {}: {}",
                measurement_name, error_text
            );
        }

        Ok(())
    }

    pub async fn list_measurements(&self) -> Result<Vec<String>> {
        let flux_query = format!(
            r#"import "influxdata/influxdb/schema" schema.measurements(bucket: "{}")"#,
            self.bucket
        );

        let query = Query::new(flux_query);
        let records = self.client.query_raw(Some(query)).await?;

        let mut measurements = Vec::new();
        for record in records {
            if let Some(Value::String(measurement)) = record.values.get("_value") {
                measurements.push(measurement.clone());
            }
        }

        Ok(measurements)
    }

    pub async fn load_ohlcv_data(
        &self,
        tickers: &[&str],
        start: DateTime<Utc>,
        end: DateTime<Utc>,
        cadence_minutes: Option<u64>, // New parameter for cadence in minutes
    ) -> Result<(Vec<Vec<Vec<f32>>>, Vec<i64>)> {
        let mut coin_data = Vec::with_capacity(tickers.len());
        let mut timestamps = Vec::new();

        for (ticker_idx, ticker) in tickers.iter().enumerate() {
            let asset = ticker.split('-').next().unwrap().to_lowercase();
            let measurement = format!("sample_coinbase_{}", asset);

            // println!("\nLoading cached data for {}", ticker);

            // Build the Flux query with optional cadence sampling
            let flux_query = if let Some(cadence) = cadence_minutes {
                format!(
                    r#"
                    from(bucket:"{}")
                        |> range(start: {}, stop: {})
                        |> filter(fn: (r) => r["_measurement"] == "{}")
                        |> window(every: {}m, createEmpty: false)
                        |> first()
                        |> duplicate(column: "_time", as: "_time_orig")
                        |> window(every: inf, createEmpty: false)
                        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                        |> sort(columns: ["_time"])
                    "#,
                    self.bucket,
                    start.to_rfc3339(),
                    end.to_rfc3339(),
                    measurement,
                    cadence
                )
            } else {
                format!(
                    r#"
                    from(bucket:"{}")
                        |> range(start: {}, stop: {})
                        |> filter(fn: (r) => r["_measurement"] == "{}")
                        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                        |> sort(columns: ["_time"])
                    "#,
                    self.bucket,
                    start.to_rfc3339(),
                    end.to_rfc3339(),
                    measurement
                )
            };

            let query = Query::new(flux_query);
            let records = self.client.query_raw(Some(query)).await?;

            // println!("Found {} candles in cache", records.len());

            let mut asset_data = Vec::with_capacity(records.len());

            for record in records {
                let get_float = |key: &str| -> f32 {
                    record
                        .values
                        .get(key)
                        .map(|v| match v {
                            Value::Double(f) => f.into_inner() as f32,
                            Value::Long(i) => *i as f32,
                            Value::UnsignedLong(u) => *u as f32,
                            Value::String(s) => s.parse().unwrap_or(0.0),
                            _ => 0.0,
                        })
                        .unwrap_or(0.0)
                };

                if ticker_idx == 0 {
                    let timestamp = record
                        .values
                        .get("est_timestamp")
                        .and_then(|v| match v {
                            Value::Long(ts) => Some(*ts),
                            Value::UnsignedLong(ts) => Some(*ts as i64),
                            Value::Double(f) => Some(f.into_inner() as i64),
                            Value::String(s) => s.parse::<i64>().ok(),
                            _ => None,
                        })
                        .unwrap_or(0);
                    timestamps.push(timestamp);
                }

                let ohlcv = vec![
                    get_float("open"),
                    get_float("high"),
                    get_float("low"),
                    get_float("close"),
                    get_float("volume"),
                ];

                asset_data.push(ohlcv);
            }

            coin_data.push(asset_data);
        }

        if coin_data.is_empty() {
            return Ok((Vec::new(), Vec::new()));
        }

        let num_time_points = coin_data[0].len();
        let num_coins = coin_data.len();
        let mut transposed_data = Vec::with_capacity(num_time_points);

        for time_idx in 0..num_time_points {
            let mut time_slice = Vec::with_capacity(num_coins);
            for coin_idx in 0..num_coins {
                time_slice.push(coin_data[coin_idx][time_idx].clone());
            }
            transposed_data.push(time_slice);
        }

        Ok((transposed_data, timestamps))
    }

    pub async fn check_data_availability(&self, tickers: &[&str]) -> Result<()> {
        println!("=== Checking Data Availability ===\n");

        // List all measurements
        println!("Available measurements:");
        let measurements = self.list_measurements().await?;
        for measurement in &measurements {
            println!("  - {}", measurement);
        }
        println!();

        // Check date ranges for each ticker
        for ticker in tickers {
            let asset = ticker.split('-').next().unwrap().to_lowercase();
            let measurement = format!("sample_coinbase_{}", asset);

            println!(
                "Checking data range for {} (measurement: {})",
                ticker, measurement
            );

            // Query for earliest and latest timestamps
            let flux_query = format!(
                r#"
                from(bucket:"{}")
                    |> range(start: 1970-01-01T00:00:00Z)
                    |> filter(fn: (r) => r["_measurement"] == "{}")
                    |> first()
                    |> keep(columns: ["_time"])
                "#,
                self.bucket, measurement
            );

            // Get first timestamp
            let query = Query::new(flux_query);
            let first_records = self.client.query_raw(Some(query)).await?;

            // Query for latest timestamp
            let last_flux_query = format!(
                r#"
                from(bucket:"{}")
                    |> range(start: 1970-01-01T00:00:00Z)
                    |> filter(fn: (r) => r["_measurement"] == "{}")
                    |> last()
                    |> keep(columns: ["_time"])
                "#,
                self.bucket, measurement
            );
            let last_query = Query::new(last_flux_query);
            let last_records = self.client.query_raw(Some(last_query)).await?;

            // Count total records
            let count_flux_query = format!(
                r#"
                from(bucket:"{}")
                    |> range(start: 1970-01-01T00:00:00Z)
                    |> filter(fn: (r) => r["_measurement"] == "{}")
                    |> count()
                "#,
                self.bucket, measurement
            );
            let count_query = Query::new(count_flux_query);
            let count_records = self.client.query_raw(Some(count_query)).await?;

            if first_records.is_empty() {
                println!("  ❌ No data found for {}", ticker);
            } else {
                // Get record count
                let record_count = if let Some(count_record) = count_records.first() {
                    if let Some(Value::Long(count)) = count_record.values.get("_value") {
                        *count
                    } else if let Some(Value::UnsignedLong(count)) =
                        count_record.values.get("_value")
                    {
                        *count as i64
                    } else {
                        0
                    }
                } else {
                    0
                };

                println!("  ✅ Found {} records", record_count);

                // Get first timestamp
                if let Some(first_record) = first_records.first() {
                    if let Some(Value::String(time_str)) = first_record.values.get("_time") {
                        println!("  📅 Earliest: {}", time_str);
                    }
                }

                // Get last timestamp
                if let Some(last_record) = last_records.first() {
                    if let Some(Value::String(time_str)) = last_record.values.get("_time") {
                        println!("  📅 Latest: {}", time_str);
                    }
                }
            }
            println!();
        }

        Ok(())
    }
}
