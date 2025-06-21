use anyhow::Result;
use chrono::{DateTime, Duration, Utc};
use reqwest::{Client, Response, StatusCode};
use std::time::Duration as StdDuration;
use tokio::time::sleep;

/// HTTP-related error types and retry logic utilities
#[derive(Debug)]
pub struct RetryableError {
    pub error: anyhow::Error,
    pub is_retryable: bool,
    pub backoff_ms: u64,
}

impl RetryableError {
    pub fn new(error: anyhow::Error, is_retryable: bool, backoff_ms: u64) -> Self {
        Self {
            error,
            is_retryable,
            backoff_ms,
        }
    }

    /// Create a retryable error based on HTTP status code
    pub fn from_http_status(
        status: StatusCode,
        error: anyhow::Error,
        attempt: u32,
        initial_backoff: u64,
        multiplier: u64,
    ) -> Self {
        let is_retryable = is_retryable_status(status);
        let backoff_ms = if is_retryable {
            calculate_backoff(attempt, initial_backoff, multiplier)
        } else {
            0
        };

        Self::new(error, is_retryable, backoff_ms)
    }

    /// Create a retryable error from a response
    pub async fn from_response(
        response: Response,
        attempt: u32,
        initial_backoff: u64,
        multiplier: u64,
    ) -> Self {
        let status = response.status();
        let error_text = response
            .text()
            .await
            .unwrap_or_else(|_| "Failed to read response body".to_string());

        let error = anyhow::anyhow!("HTTP {} error: {}", status.as_u16(), error_text);
        Self::from_http_status(status, error, attempt, initial_backoff, multiplier)
    }
}

/// Configuration for HTTP retry behavior
#[derive(Debug, Clone)]
pub struct RetryConfig {
    pub max_retries: u32,
    pub initial_backoff_ms: u64,
    pub backoff_multiplier: u64,
    pub timeout_seconds: u64,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_retries: 5,
            initial_backoff_ms: 1000,
            backoff_multiplier: 2,
            timeout_seconds: 30,
        }
    }
}

/// HTTP client with built-in retry logic
pub struct HttpClient {
    client: Client,
    retry_config: RetryConfig,
}

impl HttpClient {
    /// Create a new HTTP client with default configuration
    pub fn new() -> Self {
        Self::with_config(RetryConfig::default())
    }

    /// Create a new HTTP client with custom retry configuration
    pub fn with_config(retry_config: RetryConfig) -> Self {
        let client = Client::builder()
            .timeout(StdDuration::from_secs(retry_config.timeout_seconds))
            .user_agent("port-etl/1.0.0")
            .build()
            .expect("Failed to create HTTP client");

        Self {
            client,
            retry_config,
        }
    }

    /// Get the underlying reqwest client
    pub fn client(&self) -> &Client {
        &self.client
    }

    /// Execute an HTTP request with automatic retry logic
    pub async fn execute_with_retry<F, Fut>(
        &self,
        operation_name: &str,
        request_fn: F,
    ) -> Result<Response>
    where
        F: Fn() -> Fut,
        Fut: std::future::Future<Output = Result<Response, reqwest::Error>>,
    {
        let mut attempt = 0;

        loop {
            attempt += 1;

            match request_fn().await {
                Ok(response) => {
                    if response.status().is_success() {
                        if attempt > 1 {
                            println!(
                                "🔄 {} succeeded after {} retries",
                                operation_name,
                                attempt - 1
                            );
                        }
                        return Ok(response);
                    } else {
                        // Convert error response to RetryableError
                        let retryable_error = RetryableError::from_response(
                            response,
                            attempt,
                            self.retry_config.initial_backoff_ms,
                            self.retry_config.backoff_multiplier,
                        )
                        .await;

                        if !retryable_error.is_retryable || attempt >= self.retry_config.max_retries
                        {
                            return Err(anyhow::anyhow!(
                                "Max retries exceeded for {} (attempt {}/{}): {}",
                                operation_name,
                                attempt,
                                self.retry_config.max_retries,
                                retryable_error.error
                            ));
                        }

                        println!(
                            "⚠️  {} failed (attempt {}/{}), retrying in {}ms: {}",
                            operation_name,
                            attempt,
                            self.retry_config.max_retries,
                            retryable_error.backoff_ms,
                            retryable_error.error
                        );

                        sleep(StdDuration::from_millis(retryable_error.backoff_ms)).await;
                    }
                }
                Err(e) => {
                    // Handle network/connection errors
                    let retryable_error = if is_retryable_network_error(&e) {
                        let backoff = calculate_backoff(
                            attempt,
                            self.retry_config.initial_backoff_ms,
                            self.retry_config.backoff_multiplier,
                        );
                        RetryableError::new(anyhow::anyhow!(e), true, backoff)
                    } else {
                        RetryableError::new(anyhow::anyhow!(e), false, 0)
                    };

                    if !retryable_error.is_retryable || attempt >= self.retry_config.max_retries {
                        return Err(anyhow::anyhow!(
                            "Max retries exceeded for {} (attempt {}/{}): {}",
                            operation_name,
                            attempt,
                            self.retry_config.max_retries,
                            retryable_error.error
                        ));
                    }

                    println!(
                        "⚠️  {} network error (attempt {}/{}), retrying in {}ms: {}",
                        operation_name,
                        attempt,
                        self.retry_config.max_retries,
                        retryable_error.backoff_ms,
                        retryable_error.error
                    );

                    sleep(StdDuration::from_millis(retryable_error.backoff_ms)).await;
                }
            }
        }
    }
}

impl Default for HttpClient {
    fn default() -> Self {
        Self::new()
    }
}

/// Check if an HTTP status code is retryable
pub fn is_retryable_status(status: StatusCode) -> bool {
    matches!(
        status,
        StatusCode::TOO_MANY_REQUESTS
            | StatusCode::INTERNAL_SERVER_ERROR
            | StatusCode::BAD_GATEWAY
            | StatusCode::SERVICE_UNAVAILABLE
            | StatusCode::GATEWAY_TIMEOUT
            | StatusCode::REQUEST_TIMEOUT
    )
}

/// Check if a network error is retryable
pub fn is_retryable_network_error(error: &reqwest::Error) -> bool {
    error.is_timeout() || error.is_connect() || error.is_request()
}

/// Calculate exponential backoff delay
pub fn calculate_backoff(attempt: u32, initial_backoff: u64, multiplier: u64) -> u64 {
    initial_backoff * multiplier.pow(attempt.saturating_sub(1))
}

/// Check if an HTTP status indicates a rate limit
pub fn is_rate_limited(status: StatusCode) -> bool {
    status == StatusCode::TOO_MANY_REQUESTS
}

/// Check if an HTTP status indicates a server error
pub fn is_server_error(status: StatusCode) -> bool {
    status.is_server_error()
}

/// Check if an HTTP status indicates a client error (non-retryable)
pub fn is_client_error(status: StatusCode) -> bool {
    status.is_client_error() && status != StatusCode::TOO_MANY_REQUESTS
}

/// Format HTTP error message with status code
pub fn format_http_error(status: StatusCode, body: &str) -> String {
    format!("HTTP {} error: {}", status.as_u16(), body)
}

/// Extract relevant error information from HTTP response
pub async fn extract_error_info(response: Response) -> (StatusCode, String) {
    let status = response.status();
    let body = response
        .text()
        .await
        .unwrap_or_else(|_| "Failed to read response body".to_string());
    (status, body)
}

pub fn create_time_chunks(
    start: DateTime<Utc>,
    end: DateTime<Utc>,
    chunk_days: i64,
) -> Vec<(DateTime<Utc>, DateTime<Utc>)> {
    let mut chunks = Vec::new();

    // Normalize start to beginning of day (00:00:00)
    let start_date = start.date_naive();
    let mut current_start = start_date.and_hms_opt(0, 0, 0).unwrap().and_utc();

    // Normalize end to end of day (23:59:59)
    let end_date = end.date_naive();
    let normalized_end = end_date.and_hms_opt(23, 59, 59).unwrap().and_utc();

    while current_start < normalized_end {
        // Calculate chunk end: add chunk_days and align to end of that day
        let chunk_end_date = current_start.date_naive() + Duration::days(chunk_days);
        let chunk_end = chunk_end_date
            .and_hms_opt(23, 59, 59)
            .unwrap()
            .and_utc()
            .min(normalized_end);

        chunks.push((current_start, chunk_end));

        // Move to start of next day after the chunk
        current_start = (chunk_end_date + Duration::days(1))
            .and_hms_opt(0, 0, 0)
            .unwrap()
            .and_utc();
    }

    chunks
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_retryable_status() {
        assert!(is_retryable_status(StatusCode::TOO_MANY_REQUESTS));
        assert!(is_retryable_status(StatusCode::INTERNAL_SERVER_ERROR));
        assert!(is_retryable_status(StatusCode::BAD_GATEWAY));
        assert!(is_retryable_status(StatusCode::SERVICE_UNAVAILABLE));
        assert!(is_retryable_status(StatusCode::GATEWAY_TIMEOUT));

        assert!(!is_retryable_status(StatusCode::BAD_REQUEST));
        assert!(!is_retryable_status(StatusCode::UNAUTHORIZED));
        assert!(!is_retryable_status(StatusCode::FORBIDDEN));
        assert!(!is_retryable_status(StatusCode::NOT_FOUND));
    }

    #[test]
    fn test_calculate_backoff() {
        assert_eq!(calculate_backoff(1, 1000, 2), 1000);
        assert_eq!(calculate_backoff(2, 1000, 2), 2000);
        assert_eq!(calculate_backoff(3, 1000, 2), 4000);
        assert_eq!(calculate_backoff(4, 1000, 2), 8000);
        assert_eq!(calculate_backoff(5, 1000, 2), 16000);
    }

    #[test]
    fn test_is_rate_limited() {
        assert!(is_rate_limited(StatusCode::TOO_MANY_REQUESTS));
        assert!(!is_rate_limited(StatusCode::INTERNAL_SERVER_ERROR));
        assert!(!is_rate_limited(StatusCode::OK));
    }

    #[test]
    fn test_is_server_error() {
        assert!(is_server_error(StatusCode::INTERNAL_SERVER_ERROR));
        assert!(is_server_error(StatusCode::BAD_GATEWAY));
        assert!(!is_server_error(StatusCode::BAD_REQUEST));
        assert!(!is_server_error(StatusCode::OK));
    }

    #[test]
    fn test_format_http_error() {
        let error_msg = format_http_error(StatusCode::BAD_REQUEST, "Invalid request");
        assert_eq!(error_msg, "HTTP 400 error: Invalid request");
    }
}
