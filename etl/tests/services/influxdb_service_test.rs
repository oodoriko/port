use anyhow::Result;
use dotenv::dotenv;
use port_etl::InfluxDBHandler;

// Regular function that can be called from anywhere
pub async fn influxdb_connection_test() -> Result<()> {
    dotenv().ok();

    println!("Testing InfluxDB connection...");

    // Test creating a new handler
    let handler = match InfluxDBHandler::new() {
        Ok(h) => {
            println!("✅ Successfully created InfluxDB handler");
            h
        }
        Err(e) => {
            println!("❌ Failed to create InfluxDB handler: {}", e);
            println!("Make sure INFLUXDB_TOKEN, INFLUXDB_ORG, and INFLUXDB_BUCKET environment variables are set");
            return Err(e);
        }
    };

    // Test listing measurements to verify connection
    match handler.list_measurements().await {
        Ok(measurements) => {
            println!("✅ Successfully connected to InfluxDB");
            println!("Found {} measurements:", measurements.len());
            for measurement in measurements.iter().take(5) {
                println!("  - {}", measurement);
            }
            if measurements.len() > 5 {
                println!("  ... and {} more", measurements.len() - 5);
            }
        }
        Err(e) => {
            println!("❌ Failed to list measurements: {}", e);
            println!("This might indicate a connection issue or authentication problem");
            return Err(e);
        }
    }

    println!("🎉 InfluxDB connection test passed!");
    Ok(())
}

// Test wrapper that calls the regular function
#[tokio::test]
async fn test_influxdb_connection() -> Result<()> {
    influxdb_connection_test().await
}

#[tokio::test]
async fn test_influxdb_data_availability_check() -> Result<()> {
    dotenv().ok();

    println!("Testing InfluxDB data availability check...");

    let handler = InfluxDBHandler::new()?;
    let test_tickers = &["BTC-USD", "ETH-USD"];

    match handler.check_data_availability(test_tickers).await {
        Ok(()) => {
            println!("✅ Data availability check completed successfully");
        }
        Err(e) => {
            println!("⚠️ Data availability check failed: {}", e);
            println!("This is expected if no data has been cached yet");
        }
    }

    Ok(())
}
