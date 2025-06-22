use chrono::{DateTime, Utc};
use port_etl::postgres_service::NeonConnection;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

fn parse_historical_table_name(table_name: &str) -> Option<String> {
    let parts: Vec<&str> = table_name.split('_').collect();
    if parts.len() >= 4 && parts[0] == "historical" {
        let coin1 = parts[parts.len() - 2];
        let coin2 = parts[parts.len() - 1];
        Some(format!("{}-{}", coin1.to_uppercase(), coin2.to_uppercase()))
    } else {
        None
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct OhlcvData {
    pub timestamp: i64,
    pub open: f32,
    pub high: f32,
    pub low: f32,
    pub close: f32,
    pub volume: f32,
}

pub async fn get_all_historical(
) -> Result<HashMap<String, String>, Box<dyn std::error::Error + Send + Sync>> {
    let connection = NeonConnection::new_read_only().await?;

    let rows = connection.query(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'historical' AND tablename NOT LIKE 'etl_%' ORDER BY tablename",
        &[]
    ).await?;

    let mut tables = HashMap::new();
    for row in rows {
        let table: String = row.get("tablename");

        if let Some(pair) = parse_historical_table_name(&table) {
            tables.insert(pair, table);
        }
    }

    Ok(tables)
}

pub async fn list_available_historical(
) -> Result<Vec<String>, Box<dyn std::error::Error + Send + Sync>> {
    let connection = NeonConnection::new_read_only().await?;

    let rows = connection.query(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'historical' AND tablename NOT LIKE 'etl_%' ORDER BY tablename",
        &[]
    ).await?;

    let mut pairs = Vec::new();
    for row in rows {
        let table: String = row.get("tablename");

        if let Some(pair) = parse_historical_table_name(&table) {
            pairs.push(pair);
        }
    }

    Ok(pairs)
}

pub async fn get_historicals_date_range(
) -> Result<HashMap<String, (i64, i64)>, Box<dyn std::error::Error + Send + Sync>> {
    let connection = NeonConnection::new_read_only().await?;

    let rows = connection.query(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'historical' AND tablename NOT LIKE 'etl_%' ORDER BY tablename",
        &[]
    ).await?;

    let mut date_ranges = HashMap::new();
    for row in rows {
        let table: String = row.get("tablename");

        if let Some(pair) = parse_historical_table_name(&table) {
            // Get first and last timestamp from the table
            let range_query = format!(
                "SELECT 
                    (SELECT timestamp FROM historical.{} ORDER BY timestamp ASC LIMIT 1) as start_ts,
                    (SELECT timestamp FROM historical.{} ORDER BY timestamp DESC LIMIT 1) as end_ts",
                table, table
            );

            if let Ok(range_rows) = connection.query(&range_query, &[]).await {
                if let Some(range_row) = range_rows.first() {
                    let start_ts: i64 = range_row.get("start_ts");
                    let end_ts: i64 = range_row.get("end_ts");
                    // Add one day (86400 seconds) to the start timestamp for buffer
                    let adjusted_start_ts = start_ts + 86400;
                    date_ranges.insert(pair, (adjusted_start_ts, end_ts));
                }
            }
        }
    }

    Ok(date_ranges)
}

pub async fn get_historical_data(
    start_date: DateTime<Utc>,
    end_date: DateTime<Utc>,
    trading_pairs: Vec<String>,
) -> Result<HashMap<String, Vec<OhlcvData>>, Box<dyn std::error::Error + Send + Sync>> {
    let connection = NeonConnection::new_read_only().await?;

    // Convert dates to timestamps
    let start_timestamp = start_date.timestamp();
    let end_timestamp = end_date.timestamp();

    let mut result = HashMap::new();

    for trading_pair in trading_pairs {
        // Parse trading pair (e.g., "BTC-USD") and construct table name
        let parts: Vec<&str> = trading_pair.split('-').collect();
        if parts.len() == 2 {
            let coin1 = parts[0].to_lowercase();
            let coin2 = parts[1].to_lowercase();
            let table_name = format!("historical_coinbase_{}_{}", coin1, coin2);

            // Query the historical data for this trading pair
            let query = format!(
                "SELECT timestamp, open, high, low, close, volume 
                 FROM historical.{} 
                 WHERE timestamp >= $1 AND timestamp <= $2 
                 ORDER BY timestamp ASC",
                table_name
            );

            let rows = connection
                .query(&query, &[&start_timestamp, &end_timestamp])
                .await?;

            let mut ohlcv_data = Vec::new();
            for row in rows {
                ohlcv_data.push(OhlcvData {
                    timestamp: row.get("timestamp"),
                    open: row.get("open"),
                    high: row.get("high"),
                    low: row.get("low"),
                    close: row.get("close"),
                    volume: row.get("volume"),
                });
            }

            result.insert(trading_pair, ohlcv_data);
        }
    }

    Ok(result)
}
