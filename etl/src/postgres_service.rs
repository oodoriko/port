use chrono::{DateTime, Utc};
use deadpool_postgres::{Config, Pool, PoolError, Runtime};
use dotenv;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::env;
use std::error::Error;
use std::fmt;
use tokio_postgres::Row;
use tokio_postgres_rustls::MakeRustlsConnect;

use crate::coinbase_service::OhlcvData;

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

    /// Load read-only configuration from environment variables
    pub fn from_env_read_only() -> Result<Self, NeonError> {
        let database_url = env::var("NEON_READ_ONLY").map_err(|_| {
            NeonError::ConfigError("NEON_READ_ONLY environment variable not found".to_string())
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
}

/// Neon database connection manager
pub struct NeonConnection {
    pool: Pool,
}

impl NeonConnection {
    /// Create a new connection manager with default configuration from environment
    pub async fn new() -> Result<Self, NeonError> {
        // Load environment variables from .env file if present
        let _ = dotenv::dotenv()
            .or_else(|_| dotenv::from_filename("../etl/.env"))
            .or_else(|_| dotenv::from_filename("etl/.env"))
            .or_else(|_| dotenv::from_filename("./.env"));

        let config = NeonConfig::from_env()?;
        Self::with_config(config).await
    }

    /// Create a new read-only connection manager with configuration from NEON_READ_ONLY env var
    pub async fn new_read_only() -> Result<Self, NeonError> {
        // Load environment variables from .env file if present
        let _ = dotenv::dotenv()
            .or_else(|_| dotenv::from_filename("../etl/.env"))
            .or_else(|_| dotenv::from_filename("etl/.env"))
            .or_else(|_| dotenv::from_filename("./.env"));

        let config = NeonConfig::from_env_read_only()?;
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

    // ===== UTILITY FUNCTIONS =====
    /// Create a table if it doesn't exist
    pub async fn create_table_if_not_exists(
        &self,
        table_name: &str,
        schema: &str,
    ) -> Result<(), NeonError> {
        let query = format!(
            "CREATE TABLE IF NOT EXISTS historical.{} ({})",
            table_name, schema
        );
        self.execute(&query, &[]).await?;
        Ok(())
    }

    /// Check if a table exists
    pub async fn table_exists(&self, table_name: &str) -> Result<bool, NeonError> {
        let row = self
            .query_opt(
                "SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'historical' 
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
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'historical'",
                &[],
            )
            .await?;

        Ok(rows.into_iter().map(|row| row.get(0)).collect())
    }

    /// Cache historical OHLCV data for multiple tickers from an exchange
    /// If prefix is provided, tables will be named: {prefix}_historical_{exchange}_{ticker}
    /// Otherwise: historical_{exchange}_{ticker}
    pub async fn cache_historical_ohlcv(
        &self,
        exchange: &str,
        data: HashMap<String, Vec<OhlcvData>>,
        prefix: Option<&str>,
    ) -> Result<(), NeonError> {
        for (ticker, ohlcv_data) in data {
            if ohlcv_data.is_empty() {
                continue; // Skip empty data
            }

            let table_name = if let Some(prefix) = prefix {
                format!(
                    "{}_historical_{}_{}",
                    prefix,
                    exchange.to_lowercase().replace("-", "_"),
                    ticker.to_lowercase().replace("-", "_")
                )
            } else {
                format!(
                    "historical_{}_{}",
                    exchange.to_lowercase().replace("-", "_"),
                    ticker.to_lowercase().replace("-", "_")
                )
            };

            // Check if table exists, create if not
            if !self.table_exists(&table_name).await? {
                self.create_ohlcv_table(&table_name).await?;
                if prefix.is_some() {
                    println!("✅ Created {} table: {}", prefix.unwrap_or(""), table_name);
                } else {
                    println!("✅ Created table: {}", table_name);
                }
            }

            // Insert OHLCV data
            let inserted_count = self.insert_ohlcv_data(&table_name, &ohlcv_data).await?;
            if prefix.is_some() {
                println!(
                    "💾 Inserted {} records into {} table {}",
                    inserted_count,
                    prefix.unwrap_or(""),
                    table_name
                );
            } else {
                println!("💾 Inserted {} records into {}", inserted_count, table_name);
            }
        }

        Ok(())
    }

    /// Create OHLCV table with proper schema
    async fn create_ohlcv_table(&self, table_name: &str) -> Result<(), NeonError> {
        let schema = r#"
            timestamp BIGINT PRIMARY KEY,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        "#;

        self.create_table_if_not_exists(table_name, schema).await?;

        // Create index on timestamp for better query performance
        let index_query = format!(
            "CREATE INDEX IF NOT EXISTS idx_{}_timestamp ON historical.{} (timestamp)",
            table_name.replace("-", "_"),
            table_name
        );
        self.execute(&index_query, &[]).await?;

        Ok(())
    }

    /// Insert OHLCV data using batch INSERT for much better performance
    async fn insert_ohlcv_data(
        &self,
        table_name: &str,
        ohlcv_data: &[OhlcvData],
    ) -> Result<usize, NeonError> {
        if ohlcv_data.is_empty() {
            return Ok(0);
        }

        // Deduplicate data by timestamp to avoid ON CONFLICT issues within the same batch
        let mut unique_data: std::collections::HashMap<i64, &OhlcvData> =
            std::collections::HashMap::new();
        for ohlcv in ohlcv_data {
            // Keep the last occurrence of each timestamp (most recent data)
            unique_data.insert(ohlcv.timestamp, ohlcv);
        }

        // Convert back to vector and sort by timestamp for consistent ordering
        let mut deduplicated_data: Vec<&OhlcvData> = unique_data.into_values().collect();
        deduplicated_data.sort_by_key(|ohlcv| ohlcv.timestamp);

        // For very large batches, chunk them to avoid hitting PostgreSQL parameter limits (65535)
        const BATCH_SIZE: usize = 1000; // 1000 records * 6 params = 6000 params per batch
        let mut total_inserted = 0;

        for chunk in deduplicated_data.chunks(BATCH_SIZE) {
            total_inserted += self.insert_ohlcv_batch_refs(table_name, chunk).await?;
        }

        Ok(total_inserted)
    }

    /// Insert a single batch of OHLCV data using multi-value INSERT (for references)
    async fn insert_ohlcv_batch_refs(
        &self,
        table_name: &str,
        ohlcv_data: &[&OhlcvData],
    ) -> Result<usize, NeonError> {
        if ohlcv_data.is_empty() {
            return Ok(0);
        }

        let mut client = self.get_client().await?;
        let transaction = client.transaction().await?;

        // Build multi-value INSERT query
        let mut query = format!(
            "INSERT INTO historical.{} (timestamp, open, high, low, close, volume) VALUES ",
            table_name
        );

        let mut params: Vec<&(dyn tokio_postgres::types::ToSql + Sync)> = Vec::new();
        let mut value_groups = Vec::new();

        for (i, ohlcv) in ohlcv_data.iter().enumerate() {
            let base_idx = i * 6;
            value_groups.push(format!(
                "(${}, ${}, ${}, ${}, ${}, ${})",
                base_idx + 1,
                base_idx + 2,
                base_idx + 3,
                base_idx + 4,
                base_idx + 5,
                base_idx + 6
            ));

            params.push(&ohlcv.timestamp);
            params.push(&ohlcv.open);
            params.push(&ohlcv.high);
            params.push(&ohlcv.low);
            params.push(&ohlcv.close);
            params.push(&ohlcv.volume);
        }

        query.push_str(&value_groups.join(", "));
        query.push_str(
            " ON CONFLICT (timestamp) 
             DO UPDATE SET 
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume",
        );

        let inserted_count = transaction.execute(&query, &params).await?;
        transaction.commit().await?;

        Ok(inserted_count as usize)
    }

    /// ===== ETL PROGRESS TRACKING METHODS =====

    /// Create the ETL progress tracking table if it doesn't exist
    pub async fn create_etl_progress_table(&self) -> Result<(), NeonError> {
        let schema = r#"
            id SERIAL PRIMARY KEY,
            job_id VARCHAR(100) NOT NULL,
            exchange VARCHAR(50) NOT NULL,
            ticker VARCHAR(50) NOT NULL,
            granularity INTEGER NOT NULL,
            chunk_start TIMESTAMP WITH TIME ZONE NOT NULL,
            chunk_end TIMESTAMP WITH TIME ZONE NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            records_fetched INTEGER DEFAULT 0,
            records_cached INTEGER DEFAULT 0,
            retry_count INTEGER DEFAULT 0,
            error_message TEXT,
            started_at TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(job_id, chunk_start, chunk_end)
        "#;

        self.create_table_if_not_exists("etl_job_progress", schema)
            .await?;

        // Create indexes for better query performance
        let indexes = vec![
            "CREATE INDEX IF NOT EXISTS idx_etl_progress_job_id ON historical.etl_job_progress (job_id)",
            "CREATE INDEX IF NOT EXISTS idx_etl_progress_status ON historical.etl_job_progress (status)",
            "CREATE INDEX IF NOT EXISTS idx_etl_progress_job_status ON historical.etl_job_progress (job_id, status)",
        ];

        for index_query in indexes {
            self.execute(index_query, &[]).await?;
        }

        println!("✅ ETL progress tracking table ready");
        Ok(())
    }

    /// Create ETL job plan by inserting all chunks as 'pending'
    pub async fn create_etl_job_plan(
        &self,
        job_id: &str,
        exchange: &str,
        ticker: &str,
        granularity: u32,
        chunks: &[(DateTime<Utc>, DateTime<Utc>)],
    ) -> Result<(), NeonError> {
        let mut client = self.get_client().await?;
        let transaction = client.transaction().await?;

        let insert_query = "
            INSERT INTO historical.etl_job_progress 
            (job_id, exchange, ticker, granularity, chunk_start, chunk_end, status) 
            VALUES ($1, $2, $3, $4, $5, $6, 'pending') 
            ON CONFLICT (job_id, chunk_start, chunk_end) DO NOTHING";

        let stmt = transaction.prepare(insert_query).await?;

        for (chunk_start, chunk_end) in chunks {
            transaction
                .execute(
                    &stmt,
                    &[
                        &job_id,
                        &exchange,
                        &ticker,
                        &(granularity as i32),
                        chunk_start,
                        chunk_end,
                    ],
                )
                .await?;
        }

        transaction.commit().await?;
        println!(
            "📋 Created job plan: {} chunks for {}",
            chunks.len(),
            job_id
        );
        Ok(())
    }

    /// Get pending chunks for a job (enables resume capability)
    pub async fn get_pending_chunks(
        &self,
        job_id: &str,
    ) -> Result<Vec<(DateTime<Utc>, DateTime<Utc>)>, NeonError> {
        let rows = self
            .query(
                "SELECT chunk_start, chunk_end FROM historical.etl_job_progress 
             WHERE job_id = $1 AND status IN ('pending', 'failed') 
             ORDER BY chunk_start",
                &[&job_id],
            )
            .await?;

        Ok(rows
            .into_iter()
            .map(|row| (row.get(0), row.get(1)))
            .collect())
    }

    /// Get failed chunks that can be retried
    pub async fn get_retryable_chunks(
        &self,
        job_id: &str,
        max_retries: u32,
    ) -> Result<Vec<(DateTime<Utc>, DateTime<Utc>, u32)>, NeonError> {
        let rows = self
            .query(
                "SELECT chunk_start, chunk_end, retry_count FROM historical.etl_job_progress 
             WHERE job_id = $1 AND status = 'failed' AND retry_count < $2
             ORDER BY chunk_start",
                &[&job_id, &(max_retries as i32)],
            )
            .await?;

        Ok(rows
            .into_iter()
            .map(|row| (row.get(0), row.get(1), row.get::<_, i32>(2) as u32))
            .collect())
    }

    /// Mark chunk as in progress
    pub async fn mark_chunk_in_progress(
        &self,
        job_id: &str,
        chunk_start: DateTime<Utc>,
    ) -> Result<(), NeonError> {
        self.execute(
            "UPDATE historical.etl_job_progress 
             SET status = 'in_progress', started_at = NOW() 
             WHERE job_id = $1 AND chunk_start = $2",
            &[&job_id, &chunk_start],
        )
        .await?;
        Ok(())
    }

    /// Mark chunk as completed
    pub async fn mark_chunk_completed(
        &self,
        job_id: &str,
        chunk_start: DateTime<Utc>,
        records_fetched: usize,
        records_cached: usize,
    ) -> Result<(), NeonError> {
        self.execute(
            "UPDATE historical.etl_job_progress 
             SET status = 'completed', 
                 records_fetched = $1, 
                 records_cached = $2, 
                 completed_at = NOW() 
             WHERE job_id = $3 AND chunk_start = $4",
            &[
                &(records_fetched as i32),
                &(records_cached as i32),
                &job_id,
                &chunk_start,
            ],
        )
        .await?;
        Ok(())
    }

    /// Mark chunk as failed and increment retry count
    pub async fn mark_chunk_failed(
        &self,
        job_id: &str,
        chunk_start: DateTime<Utc>,
        error_message: &str,
    ) -> Result<(), NeonError> {
        self.execute(
            "UPDATE historical.etl_job_progress 
             SET status = 'failed', 
                 retry_count = retry_count + 1,
                 error_message = $1,
                 completed_at = NOW()
             WHERE job_id = $2 AND chunk_start = $3",
            &[&error_message, &job_id, &chunk_start],
        )
        .await?;
        Ok(())
    }

    /// Get job progress summary
    pub async fn get_job_progress_summary(
        &self,
        job_id: &str,
    ) -> Result<JobProgressSummary, NeonError> {
        let row = self
            .query_one(
                "SELECT 
                COUNT(*) as total_chunks,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                SUM(records_cached) FILTER (WHERE status = 'completed') as total_records
             FROM historical.etl_job_progress 
             WHERE job_id = $1",
                &[&job_id],
            )
            .await?;

        Ok(JobProgressSummary {
            job_id: job_id.to_string(),
            total_chunks: row.get::<_, i64>(0) as u32,
            completed: row.get::<_, i64>(1) as u32,
            failed: row.get::<_, i64>(2) as u32,
            in_progress: row.get::<_, i64>(3) as u32,
            pending: row.get::<_, i64>(4) as u32,
            total_records: row.get::<_, Option<i64>>(5).unwrap_or(0) as u32,
        })
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

/// Job progress summary structure
#[derive(Debug, Serialize, Deserialize)]
pub struct JobProgressSummary {
    pub job_id: String,
    pub total_chunks: u32,
    pub completed: u32,
    pub failed: u32,
    pub in_progress: u32,
    pub pending: u32,
    pub total_records: u32,
}
