mod postgres_service;

use crate::postgres_service::{NeonConnection, NeonError};
use dotenv::dotenv;
use env_logger;
use log::{error, info};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize logging
    env_logger::init();

    // Load environment variables from .env file
    dotenv().ok();

    info!("Starting ETL process...");

    // Run the ETL process
    match run_etl_process().await {
        Ok(_) => info!("ETL process completed successfully!"),
        Err(e) => error!("ETL process failed: {}", e),
    }

    Ok(())
}

/// Main ETL process - extract, transform, load
async fn run_etl_process() -> Result<(), NeonError> {
    let conn = NeonConnection::new().await?;

    // Clean up any existing table with old schema
    info!("Cleaning up existing table...");
    let _ = conn
        .execute("DROP TABLE IF EXISTS etl_target CASCADE", &[])
        .await;

    // ETL Extract phase - get data from source
    info!("ETL Extract phase...");
    let source_data = extract_data_from_source().await?;

    // ETL Transform phase - process data
    info!("ETL Transform phase...");
    let transformed_data = transform_data(source_data);

    // ETL Load phase - insert into Neon
    info!("ETL Load phase...");
    load_data_to_neon(&conn, transformed_data).await?;

    conn.close().await;
    Ok(())
}

async fn extract_data_from_source() -> Result<Vec<SourceRecord>, NeonError> {
    // In a real ETL process, this would connect to your data source
    // (API, CSV file, another database, etc.)

    // Simulated data extraction for demonstration
    info!("Extracting data from source...");

    Ok(vec![
        SourceRecord {
            id: "1".to_string(),
            name: "Sample Record 1".to_string(),
            value: 100.0,
            category: "Type A".to_string(),
        },
        SourceRecord {
            id: "2".to_string(),
            name: "Sample Record 2".to_string(),
            value: 200.0,
            category: "Type B".to_string(),
        },
        SourceRecord {
            id: "3".to_string(),
            name: "Sample Record 3".to_string(),
            value: 150.0,
            category: "Type A".to_string(),
        },
    ])
}

fn transform_data(source_data: Vec<SourceRecord>) -> Vec<TransformedRecord> {
    info!("Transforming {} records...", source_data.len());

    source_data
        .into_iter()
        .map(|record| TransformedRecord {
            external_id: record.id,
            processed_name: record.name.to_uppercase(),
            calculated_value: record.value * 1.1, // Add 10% markup
            category: record.category,
            processed_at: chrono::Utc::now(),
        })
        .collect()
}

async fn load_data_to_neon(
    conn: &NeonConnection,
    data: Vec<TransformedRecord>,
) -> Result<(), NeonError> {
    info!("Loading {} records to Neon...", data.len());

    // Create target table if it doesn't exist
    let table_schema = "
        id SERIAL PRIMARY KEY,
        external_id VARCHAR(50) UNIQUE NOT NULL,
        processed_name VARCHAR(255) NOT NULL,
        calculated_value FLOAT8,
        category VARCHAR(100),
        processed_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    ";

    conn.create_table_if_not_exists("etl_target", table_schema)
        .await?;

    // Insert transformed data with upsert logic
    for record in data {
        let query = "
            INSERT INTO etl_target (external_id, processed_name, calculated_value, category, processed_at)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (external_id) 
            DO UPDATE SET 
                processed_name = EXCLUDED.processed_name,
                calculated_value = EXCLUDED.calculated_value,
                category = EXCLUDED.category,
                processed_at = EXCLUDED.processed_at
        ";

        conn.execute(
            query,
            &[
                &record.external_id,
                &record.processed_name,
                &record.calculated_value,
                &record.category,
                &record.processed_at,
            ],
        )
        .await?;
    }

    info!("Data successfully loaded to Neon database");
    Ok(())
}

// Data structures for ETL process
#[derive(Debug)]
struct SourceRecord {
    id: String,
    name: String,
    value: f64,
    category: String,
}

#[derive(Debug)]
struct TransformedRecord {
    external_id: String,
    processed_name: String,
    calculated_value: f64,
    category: String,
    processed_at: chrono::DateTime<chrono::Utc>,
}
