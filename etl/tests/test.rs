use anyhow::Result;

// Import the test functions from other files
mod coinbase_test;
mod influxdb_test;
mod neon_test;

use coinbase_test::coinbase_connection_test;
use influxdb_test::influxdb_connection_test;
use neon_test::neon_connection_test;

#[tokio::test]
async fn test_etl() -> Result<()> {
    coinbase_connection_test().await?;
    influxdb_connection_test().await?;
    neon_connection_test().await?;
    Ok(())
}
