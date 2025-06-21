use anyhow::Result;
use dotenv::dotenv;
use log::info;
use port_etl::neon_connection::NeonConnection;
use tokio;

// Regular function that can be called from anywhere
pub async fn neon_connection_test() -> Result<()> {
    dotenv().ok();

    info!("Testing Neon connection...");

    let conn = NeonConnection::new().await?;

    // Test basic connection
    conn.test_connection().await?;

    // Get database stats
    let stats = conn.get_database_stats().await?;
    println!("📊 Database: {}", stats.database_name);
    println!("💾 Size: {} bytes", stats.database_size);
    println!("🔗 Active connections: {}", stats.active_connections);
    println!("🐘 PostgreSQL version: {}", stats.postgres_version);

    // List existing tables
    let tables = conn.get_table_names().await?;
    println!("📋 Tables in database: {:?}", tables);

    // Simple query test
    let row = conn
        .query_one(
            "SELECT NOW() as current_time, 'Hello from Neon!' as message",
            &[],
        )
        .await?;
    let current_time: chrono::DateTime<chrono::Utc> = row.get("current_time");
    let message: String = row.get("message");

    println!("⏰ Current time: {}", current_time);
    println!("💬 Message: {}", message);

    conn.close().await;

    println!("✅ Simple connection test passed!");
    Ok(())
}

// Test wrapper that calls the regular function
#[tokio::test]
async fn test_neon_connection() {
    neon_connection_test()
        .await
        .expect("Neon connection test failed");
}

#[tokio::test]
async fn test_neon_query() {
    dotenv().ok();

    let conn = NeonConnection::new()
        .await
        .expect("Failed to create connection");

    // Test simple query
    let row = conn
        .query_one("SELECT 42 as answer", &[])
        .await
        .expect("Simple query failed");
    let answer: i32 = row.get("answer");
    assert_eq!(answer, 42);

    conn.close().await;
    println!("✅ Basic query test passed!");
}
