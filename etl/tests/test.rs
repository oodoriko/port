use anyhow::Result;

// Import the test functions from other files
#[path = "jobs/coin_historical_test.rs"]
mod coin_historical_test;
#[path = "services/coinbase_service_test.rs"]
mod coinbase_service_test;
#[path = "services/influxdb_service_test.rs"]
mod influxdb_service_test;
#[path = "services/postgres_service_test.rs"]
mod postgres_service_test;

use coinbase_service_test::coinbase_connection_test;
use influxdb_service_test::influxdb_connection_test;
use postgres_service_test::neon_connection_test;

#[tokio::test]
async fn test_service_connections() -> Result<()> {
    coinbase_connection_test().await?;
    influxdb_connection_test().await?;
    neon_connection_test().await?;
    Ok(())
}
