use deadpool_postgres::{Config, Pool, PoolError, Runtime};
use serde::{Deserialize, Serialize};
use std::env;
use std::error::Error;
use std::fmt;
use tokio_postgres::Row;
use tokio_postgres_rustls::MakeRustlsConnect;

/// Custom error type for Neon database operations
#[derive(Debug)]
pub enum NeonError {
    ConnectionError(String),
    QueryError(String),
    ConfigError(String),
    PoolError(String),
}

impl fmt::Display for NeonError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            NeonError::ConnectionError(msg) => write!(f, "Connection error: {}", msg),
            NeonError::QueryError(msg) => write!(f, "Query error: {}", msg),
            NeonError::ConfigError(msg) => write!(f, "Configuration error: {}", msg),
            NeonError::PoolError(msg) => write!(f, "Pool error: {}", msg),
        }
    }
}

impl Error for NeonError {}

impl From<tokio_postgres::Error> for NeonError {
    fn from(error: tokio_postgres::Error) -> Self {
        NeonError::QueryError(error.to_string())
    }
}

impl From<PoolError> for NeonError {
    fn from(error: PoolError) -> Self {
        NeonError::PoolError(error.to_string())
    }
}

/// Configuration for Neon database connection
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NeonConfig {
    pub host: String,
    pub port: u16,
    pub database: String,
    pub username: String,
    pub password: String,
    pub max_connections: usize,
    pub min_connections: usize,
}

impl Default for NeonConfig {
    fn default() -> Self {
        Self {
            host: "localhost".to_string(),
            port: 5432,
            database: "neondb".to_string(),
            username: "postgres".to_string(),
            password: "".to_string(),
            max_connections: 10,
            min_connections: 1,
        }
    }
}

impl NeonConfig {
    /// Load configuration from environment variables
    pub fn from_env() -> Result<Self, NeonError> {
        let database_url = env::var("DATABASE_URL")
            .or_else(|_| env::var("NEON_DATABASE_URL"))
            .map_err(|_| {
                NeonError::ConfigError(
                    "DATABASE_URL or NEON_DATABASE_URL environment variable not found".to_string(),
                )
            })?;

        Self::from_url(&database_url)
    }

    /// Parse configuration from connection URL
    pub fn from_url(url: &str) -> Result<Self, NeonError> {
        let parsed = url::Url::parse(url)
            .map_err(|e| NeonError::ConfigError(format!("Invalid URL: {}", e)))?;

        let host = parsed
            .host_str()
            .ok_or_else(|| NeonError::ConfigError("No host in URL".to_string()))?
            .to_string();

        let port = parsed.port().unwrap_or(5432);

        let database = parsed.path().trim_start_matches('/').to_string();

        let username = parsed.username().to_string();

        let password = parsed
            .password()
            .ok_or_else(|| NeonError::ConfigError("No password in URL".to_string()))?
            .to_string();

        Ok(Self {
            host,
            port,
            database,
            username,
            password,
            max_connections: 10,
            min_connections: 1,
        })
    }

    /// Build connection string
    pub fn connection_string(&self) -> String {
        format!(
            "postgresql://{}:{}@{}:{}/{}?sslmode=require",
            self.username, self.password, self.host, self.port, self.database
        )
    }
}

/// Neon database connection manager
pub struct NeonConnection {
    pool: Pool,
}

impl NeonConnection {
    /// Create a new connection manager with default configuration from environment
    pub async fn new() -> Result<Self, NeonError> {
        let config = NeonConfig::from_env()?;
        Self::with_config(config).await
    }

    /// Create a new connection manager with custom configuration
    pub async fn with_config(config: NeonConfig) -> Result<Self, NeonError> {
        let mut pool_config = Config::new();
        pool_config.host = Some(config.host.clone());
        pool_config.port = Some(config.port);
        pool_config.dbname = Some(config.database.clone());
        pool_config.user = Some(config.username.clone());
        pool_config.password = Some(config.password.clone());

        // Set pool configuration
        pool_config.manager = Some(deadpool_postgres::ManagerConfig {
            recycling_method: deadpool_postgres::RecyclingMethod::Fast,
        });

        let tls = MakeRustlsConnect::new(
            rustls::ClientConfig::builder()
                .with_root_certificates(rustls::RootCertStore::from_iter(
                    webpki_roots::TLS_SERVER_ROOTS.iter().cloned(),
                ))
                .with_no_client_auth(),
        );

        let pool = pool_config
            .create_pool(Some(Runtime::Tokio1), tls)
            .map_err(|e| NeonError::PoolError(format!("Failed to create pool: {}", e)))?;

        Ok(Self { pool })
    }

    /// Get a connection from the pool
    pub async fn get_client(&self) -> Result<deadpool_postgres::Client, NeonError> {
        self.pool.get().await.map_err(|e| e.into())
    }

    /// Execute a query and return rows
    pub async fn query(
        &self,
        query: &str,
        params: &[&(dyn tokio_postgres::types::ToSql + Sync)],
    ) -> Result<Vec<Row>, NeonError> {
        let client = self.get_client().await?;
        let rows = client.query(query, params).await?;
        Ok(rows)
    }

    /// Execute a query and return the first row
    pub async fn query_one(
        &self,
        query: &str,
        params: &[&(dyn tokio_postgres::types::ToSql + Sync)],
    ) -> Result<Row, NeonError> {
        let client = self.get_client().await?;
        let row = client.query_one(query, params).await?;
        Ok(row)
    }

    /// Execute a query and return an optional row
    pub async fn query_opt(
        &self,
        query: &str,
        params: &[&(dyn tokio_postgres::types::ToSql + Sync)],
    ) -> Result<Option<Row>, NeonError> {
        let client = self.get_client().await?;
        let row = client.query_opt(query, params).await?;
        Ok(row)
    }

    /// Execute a statement (INSERT, UPDATE, DELETE)
    pub async fn execute(
        &self,
        query: &str,
        params: &[&(dyn tokio_postgres::types::ToSql + Sync)],
    ) -> Result<u64, NeonError> {
        let client = self.get_client().await?;
        let count = client.execute(query, params).await?;
        Ok(count)
    }

    /// Execute a batch of statements in a transaction
    pub async fn execute_batch(
        &self,
        statements: Vec<(&str, Vec<&(dyn tokio_postgres::types::ToSql + Sync)>)>,
    ) -> Result<Vec<u64>, NeonError> {
        let mut client = self.get_client().await?;
        let transaction = client.transaction().await?;

        let mut results = Vec::new();

        for (query, params) in statements {
            let count = transaction.execute(query, &params).await?;
            results.push(count);
        }

        transaction.commit().await?;
        Ok(results)
    }

    /// Test the database connection
    pub async fn test_connection(&self) -> Result<(), NeonError> {
        let client = self.get_client().await?;
        client.query_one("SELECT 1", &[]).await?;
        println!("✅ Successfully connected to Neon database");
        Ok(())
    }

    /// Get database statistics
    pub async fn get_database_stats(&self) -> Result<DatabaseStats, NeonError> {
        let client = self.get_client().await?;

        let row = client.query_one(
            "SELECT 
                pg_database_size(current_database()) as database_size,
                (SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()) as active_connections,
                current_database() as database_name,
                version() as postgres_version",
            &[]
        ).await?;

        Ok(DatabaseStats {
            database_name: row.get("database_name"),
            database_size: row.get("database_size"),
            active_connections: row.get("active_connections"),
            postgres_version: row.get("postgres_version"),
        })
    }

    /// Close all connections in the pool
    pub async fn close(&self) {
        self.pool.close();
    }
}

/// Database statistics structure
#[derive(Debug, Serialize, Deserialize)]
pub struct DatabaseStats {
    pub database_name: String,
    pub database_size: i64,
    pub active_connections: i64,
    pub postgres_version: String,
}

/// Utility functions for common database operations
impl NeonConnection {
    /// Create a table if it doesn't exist
    pub async fn create_table_if_not_exists(
        &self,
        table_name: &str,
        schema: &str,
    ) -> Result<(), NeonError> {
        let query = format!("CREATE TABLE IF NOT EXISTS {} ({})", table_name, schema);
        self.execute(&query, &[]).await?;
        Ok(())
    }

    /// Check if a table exists
    pub async fn table_exists(&self, table_name: &str) -> Result<bool, NeonError> {
        let row = self
            .query_opt(
                "SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = $1
            )",
                &[&table_name],
            )
            .await?;

        Ok(row.map(|r| r.get::<_, bool>(0)).unwrap_or(false))
    }

    /// Get all table names in the database
    pub async fn get_table_names(&self) -> Result<Vec<String>, NeonError> {
        let rows = self
            .query(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'",
                &[],
            )
            .await?;

        Ok(rows.into_iter().map(|row| row.get(0)).collect())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use dotenv::dotenv;

    fn init_test() {
        dotenv().ok();
        let _ = env_logger::try_init();
    }

    #[test]
    fn test_connection_string() {
        let config = NeonConfig {
            host: "localhost".to_string(),
            port: 5432,
            database: "test".to_string(),
            username: "user".to_string(),
            password: "pass".to_string(),
            max_connections: 5,
            min_connections: 1,
        };

        let conn_str = config.connection_string();
        assert!(conn_str.contains("postgresql://"));
        assert!(conn_str.contains("localhost"));
        assert!(conn_str.contains("5432"));
    }

    #[test]
    fn test_neon_config_from_url() {
        let url = "postgresql://user:pass@host:5432/dbname";
        let config = NeonConfig::from_url(url).unwrap();

        assert_eq!(config.host, "host");
        assert_eq!(config.port, 5432);
        assert_eq!(config.database, "dbname");
        assert_eq!(config.username, "user");
        assert_eq!(config.password, "pass");
    }

    #[tokio::test]
    async fn test_live_connection() {
        init_test();

        // Only run if DATABASE_URL is set
        if let Ok(_) = std::env::var("DATABASE_URL") {
            let conn = NeonConnection::new()
                .await
                .expect("Failed to create connection");
            conn.test_connection()
                .await
                .expect("Connection test failed");
            conn.close().await;
        }
    }
}
