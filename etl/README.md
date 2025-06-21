# 🚀 Port ETL - Enhanced Multi-Ticker OHLCV Data Caching System

A robust, production-ready ETL system for fetching cryptocurrency market data from Coinbase with advanced safety features, chunked processing, and database caching.

## 🌟 Key Features

### 🛡️ Conservative Rate Limiting

- **Global rate limit**: Maximum 5 requests per second across all threads
- **Per-thread sleep intervals**: Calculated as `threads / 5 seconds` to distribute load
- **Ticker limit enforcement**: Maximum 5 tickers per run to avoid overwhelming the API
- **Inter-chunk delays**: Additional delays between time chunks for extra safety

### 📦 Chunked Processing

- **Time-based chunking**: Processes data in configurable chunks (default: 30 days)
- **Sequential chunk processing**: Processes one time chunk at a time to avoid API overload
- **Automatic caching**: Each chunk is cached to database after processing
- **Progress tracking**: Real-time progress updates with chunk completion status

### 🔄 Robust Retry Logic

- **Smart error detection**: Automatically retries on HTTP 429 (rate limit) and 5xx errors
- **Exponential backoff**: Retry delays grow exponentially (1s → 2s → 4s → 8s → 16s)
- **Maximum retry attempts**: Configurable retry limit (default: 5 attempts)
- **Circuit breaker**: Stops processing entirely if a ticker consistently fails

### 🌐 HTTP Utilities Module

- **Centralized HTTP handling**: Reusable HTTP client with built-in retry logic
- **Configurable retry behavior**: Customizable retry attempts, backoff timing, and timeouts
- **Status code utilities**: Smart detection of retryable vs non-retryable errors
- **Network error handling**: Automatic retry for timeouts and connection issues

### 💾 Database Caching

- **PostgreSQL integration**: Stores fetched data for reuse and analysis
- **Duplicate prevention**: Handles data deduplication automatically
- **Incremental updates**: Only fetches missing data on subsequent runs
- **Connection pooling**: Efficient database connection management

## 🚀 Quick Start

### Demo Mode (Recommended for Testing)

```bash
cargo run -- --demo
```

- Fetches 2 months of data for BTC-USD and ETH-USD
- Uses 1-hour candles
- Completes in 10-15 minutes
- Database caching disabled for simplicity

### Production Mode

```bash
cargo run
```

- Fetches 2 years of data for up to 5 tickers
- Uses 5-minute candles
- Takes 2-4 hours with conservative rate limiting
- Database caching enabled

## 🔧 HTTP Utilities Usage

The HTTP utilities module provides reusable components for robust HTTP operations:

```rust
use port_etl::http_utils::{HttpClient, RetryConfig};

// Create a client with default configuration
let client = HttpClient::new();

// Or with custom retry behavior
let custom_config = RetryConfig {
    max_retries: 3,
    initial_backoff_ms: 500,
    backoff_multiplier: 2,
    timeout_seconds: 30,
};
let client = HttpClient::with_config(custom_config);

// Make requests with automatic retry logic
let response = client.execute_with_retry("api_call", || {
    client.client()
        .get("https://api.example.com/data")
        .send()
}).await?;
```

### HTTP Utility Functions

```rust
use port_etl::http_utils::*;
use reqwest::StatusCode;

// Check if a status code is retryable
let retryable = is_retryable_status(StatusCode::TOO_MANY_REQUESTS); // true
let not_retryable = is_retryable_status(StatusCode::NOT_FOUND);     // false

// Calculate exponential backoff delays
let delay_1 = calculate_backoff(1, 1000, 2); // 1000ms
let delay_2 = calculate_backoff(2, 1000, 2); // 2000ms
let delay_3 = calculate_backoff(3, 1000, 2); // 4000ms

// Check specific error types
let is_rate_limited = is_rate_limited(StatusCode::TOO_MANY_REQUESTS);
let is_server_error = is_server_error(StatusCode::INTERNAL_SERVER_ERROR);
```

## ⚙️ Configuration

### Environment Variables

```bash
# Database connection (required for caching)
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
# or
export NEON_DATABASE_URL="postgresql://user:pass@host:5432/dbname"
```

### Custom Configuration

```rust
use port_etl::etl_service::{fetch_historical_data_chunked, EtlConfig};

let config = EtlConfig {
    max_concurrent: 3,        // Max concurrent tickers
    chunk_size_days: 30,      // Days per chunk
    max_retries: 5,           // Max retry attempts
    initial_backoff_ms: 1000, // Initial retry delay
    backoff_multiplier: 2,    // Backoff growth factor
    enable_caching: true,     // Enable database caching
};

let results = fetch_historical_data_chunked(
    vec!["BTC-USD".to_string()],
    start_date,
    end_date,
    300, // 5-minute granularity
    Some(config),
).await?;
```

## 📊 Safety Metrics

| Metric             | Value          | Purpose                    |
| ------------------ | -------------- | -------------------------- |
| Max Tickers        | 5              | Prevents API overwhelming  |
| Global Rate Limit  | 5 req/sec      | Respects Coinbase limits   |
| Default Chunk Size | 30 days        | Manageable data sizes      |
| Max Retries        | 5 attempts     | Handles temporary failures |
| Backoff Growth     | 2x exponential | Reduces API pressure       |
| Concurrent Limit   | 3 threads      | Conservative processing    |

## 🔍 Example Output

```
🚀 Enhanced ETL: 2 tickers, 4 chunks from 2023-01-01 to 2023-04-01
⚙️  Config: 2 concurrent, 400ms/thread sleep, 5 max retries
📦 Database caching enabled
📅 Processing 4 time chunks of 30 days each

🔄 Processing chunk 1/4: 2023-01-01 to 2023-01-31
✅ BTC-USD: 8640 candles
✅ ETH-USD: 8640 candles
💾 Chunk data cached successfully
⏸️  Inter-chunk delay: 800ms

🔄 Processing chunk 2/4: 2023-01-31 to 2023-03-02
✅ BTC-USD: 8928 candles
✅ ETH-USD: 8928 candles
💾 Chunk data cached successfully
⏸️  Inter-chunk delay: 800ms

🎉 Enhanced ETL Process Completed!
📊 Final Results Summary:
  📈 BTC-USD: 35136 candles
  📈 ETH-USD: 35136 candles

🎯 Final Statistics:
  - Processed chunks: 4
  - Successful tickers: 2
  - Total candles fetched: 70272
  - Average candles per ticker: 35136

✨ Enhanced Features Used:
  - ✅ Chunked processing (avoids overwhelming API)
  - ✅ Conservative rate limiting (5 req/sec max)
  - ✅ Exponential backoff retry logic
  - ✅ Per-thread sleep intervals
  - ✅ Maximum 5 tickers enforced
  - ✅ Database caching (when enabled)
```

## 🚨 Error Handling

The system handles various error scenarios gracefully:

- **HTTP 429 (Rate Limited)**: Automatic retry with exponential backoff
- **HTTP 5xx (Server Errors)**: Retry logic with increasing delays
- **Network Timeouts**: Automatic retry with backoff
- **Database Failures**: Graceful degradation, continues without caching
- **Persistent Failures**: Circuit breaker stops processing after max retries

## 🛠️ Architecture

### Core Components

1. **ETL Service** (`etl_service.rs`): Main orchestration and chunking logic
2. **Coinbase Service** (`coinbase_service.rs`): API interaction with proper error handling
3. **HTTP Utilities** (`http_utils.rs`): Centralized HTTP client with retry logic
4. **PostgreSQL Service** (`postgres_service.rs`): Database caching and connection management
5. **Rate Limiting**: Global governor-based rate limiting across all threads

### Data Flow

```
Tickers → Time Chunks → Concurrent Processing → HTTP Utils → Database Cache
    ↓           ↓              ↓                    ↓             ↓
  Max 5    30-day chunks   Rate limited     Retry Logic    PostgreSQL
                          5 req/sec         & Backoff      caching
```

## 🔧 Development

### Build

```bash
cargo build --release
```

### Test

```bash
cargo test
```

### Run HTTP Utils Example

```bash
cargo run --example http_utils_example
```

### Run with Logging

```bash
RUST_LOG=debug cargo run -- --demo
```

## 📝 API Compliance

This ETL system is designed to be respectful of Coinbase's API:

- **Rate Limiting**: Stays well below documented limits
- **Error Handling**: Proper backoff on rate limit responses
- **User Agent**: Identifies requests appropriately
- **Chunking**: Avoids large single requests
- **Caching**: Reduces redundant API calls

## 🤝 Contributing

1. Follow the existing pattern for conservative rate limiting
2. Add tests for new retry scenarios
3. Update configuration documentation
4. Ensure database migrations are backward compatible
5. Use the HTTP utilities module for all external API calls

## 📄 License

This project is part of the Port trading system.
