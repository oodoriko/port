use axum::{
    extract::Json,
    http::StatusCode,
    response::Json as ResponseJson,
    routing::{get, post, Router},
};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tower_http::cors::CorsLayer;

use crate::analysis::backtest::{backtest, backtest_result};
use crate::core::params::{
    PortfolioConstraintParams, PortfolioParams, PositionConstraintParams, SignalParams,
};
use crate::data::database_service;

// App state to hold database connection
#[derive(Clone)]
pub struct AppState {
    // Database connection is handled directly in the service functions
}

// Request structure that matches the frontend expectations
#[derive(Debug, Serialize, Deserialize)]
pub struct BacktestRequest {
    pub backtest_id: String,
    pub strategy_name: String,
    pub portfolio_name: String,
    pub start: String, // ISO string
    pub end: String,   // ISO string
    pub tickers: Vec<String>,
    pub strategies: Vec<Vec<SignalParams>>,
    pub portfolio_params: PortfolioParams,
    pub portfolio_constraints_params: PortfolioConstraintParams,
    pub position_constraints_params: Vec<PositionConstraintParams>,
    pub warm_up_period: usize,
    pub cadence: u64, // in minutes
}

// Response structure that matches the frontend expectations
#[derive(Debug, Serialize)]
pub struct BacktestResponse {
    pub backtest_id: String,
    pub portfolio_name: String,
    pub initial_value: f32,
    pub final_value: f32,
    pub total_return: f32,
    pub max_value: f32,
    pub min_value: f32,
    pub peak_equity: f32,
    pub equity_curve: Vec<f32>,
    pub cash_curve: Vec<f32>,
    pub notional_curve: Vec<f32>,
    pub cost_curve: Vec<f32>,
    pub realized_pnl_curve: Vec<f32>,
    pub unrealized_pnl_curve: Vec<f32>,
    pub timestamps: Vec<i64>,
    pub trade_timestamps: Vec<i64>,
    pub total_records: usize,
}

// Error response structure
#[derive(Debug, Serialize)]
pub struct ErrorResponse {
    pub error: String,
    pub message: String,
}

// Data API response structures
#[derive(Debug, Serialize)]
pub struct TradingPairsResponse {
    pub pairs: Vec<String>,
}

#[derive(Debug, Serialize)]
pub struct DateRangesResponse {
    pub date_ranges: HashMap<String, (i64, i64)>,
}

// Data API handlers
pub async fn get_trading_pairs_handler(
) -> Result<ResponseJson<TradingPairsResponse>, (StatusCode, ResponseJson<ErrorResponse>)> {
    let pairs = database_service::list_available_historical()
        .await
        .map_err(|e| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                ResponseJson(ErrorResponse {
                    error: "Failed to get trading pairs".to_string(),
                    message: e.to_string(),
                }),
            )
        })?;

    Ok(ResponseJson(TradingPairsResponse { pairs }))
}

pub async fn get_date_ranges_handler(
) -> Result<ResponseJson<DateRangesResponse>, (StatusCode, ResponseJson<ErrorResponse>)> {
    let date_ranges = database_service::get_historicals_date_range()
        .await
        .map_err(|e| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                ResponseJson(ErrorResponse {
                    error: "Failed to get date ranges".to_string(),
                    message: e.to_string(),
                }),
            )
        })?;

    Ok(ResponseJson(DateRangesResponse { date_ranges }))
}

// Handler for the backtest endpoint
pub async fn backtest_handler(
    Json(request): Json<BacktestRequest>,
) -> Result<ResponseJson<BacktestResponse>, (StatusCode, ResponseJson<ErrorResponse>)> {
    // Parse dates
    let start_date = DateTime::parse_from_rfc3339(&request.start)
        .map_err(|e| {
            (
                StatusCode::BAD_REQUEST,
                ResponseJson(ErrorResponse {
                    error: "Invalid start date".to_string(),
                    message: e.to_string(),
                }),
            )
        })?
        .with_timezone(&Utc);

    let end_date = DateTime::parse_from_rfc3339(&request.end)
        .map_err(|e| {
            (
                StatusCode::BAD_REQUEST,
                ResponseJson(ErrorResponse {
                    error: "Invalid end date".to_string(),
                    message: e.to_string(),
                }),
            )
        })?
        .with_timezone(&Utc);

    // Run the backtest
    let (portfolio, executed_trades_by_date, exited_early) = backtest(
        request.strategy_name,
        request.portfolio_name,
        start_date,
        end_date,
        request.tickers,
        request.strategies,
        request.portfolio_params,
        request.portfolio_constraints_params,
        request.position_constraints_params,
        request.warm_up_period,
        request.cadence,
        false,
    )
    .await
    .map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            ResponseJson(ErrorResponse {
                error: "Backtest failed".to_string(),
                message: e.to_string(),
            }),
        )
    })?;
    backtest_result(&portfolio, &executed_trades_by_date, exited_early);

    // Convert Portfolio to BacktestResponse
    let initial_value = portfolio.equity_curve.first().copied().unwrap_or(0.0);
    let final_value = portfolio.equity_curve.last().copied().unwrap_or(0.0);
    let total_return = if initial_value != 0.0 {
        (final_value - initial_value) / initial_value * 100.0
    } else {
        0.0
    };

    let max_value = portfolio
        .equity_curve
        .iter()
        .fold(f32::NEG_INFINITY, |a, &b| a.max(b));
    let min_value = portfolio
        .equity_curve
        .iter()
        .fold(f32::INFINITY, |a, &b| a.min(b));

    let total_records = portfolio.equity_curve.len();

    let response = BacktestResponse {
        backtest_id: request.backtest_id,
        portfolio_name: portfolio.name,
        initial_value,
        final_value,
        total_return,
        max_value,
        min_value,
        peak_equity: portfolio.peak_equity,
        equity_curve: portfolio.equity_curve,
        cash_curve: portfolio.cash_curve,
        notional_curve: portfolio.notional_curve,
        cost_curve: portfolio.cost_curve,
        realized_pnl_curve: portfolio.realized_pnl_curve,
        unrealized_pnl_curve: portfolio.unrealized_pnl_curve,
        timestamps: portfolio.timestamps,
        trade_timestamps: executed_trades_by_date.keys().cloned().collect(),
        total_records,
    };

    Ok(ResponseJson(response))
}

// Create the API router
pub fn create_router() -> Router {
    Router::new()
        .route("/api/backtest", post(backtest_handler))
        .route("/api/trading-pairs", get(get_trading_pairs_handler))
        .route("/api/date-ranges", get(get_date_ranges_handler))
        .layer(CorsLayer::permissive())
}

#[cfg(test)]
mod test;
