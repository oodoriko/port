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

use crate::analysis::backtest::backtest;
use crate::analysis::metric::KeyMetrics;
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
pub struct TradeTypeCount {
    pub executed: i32,
    pub failed_insufficient_cash: i32,
    pub failed_short_sell_prohibited: i32,
    pub failed_cool_down_period: i32,
    pub rejected_holding_period_too_short: i32,
    pub rejected_cool_down_after_loss: i32,
    pub rejected_trade_size_too_small: i32,
    pub rejected_short_sell_prohibited: i32,
}

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
    pub tickers: Vec<String>,
    // New KeyMetrics fields
    pub key_metrics: KeyMetricsResponse,
    pub risk_free_rate: f32,
    pub trade_type_count: TradeTypeCount,
}

// Response structure for KeyMetrics
#[derive(Debug, Serialize)]
pub struct KeyMetricsResponse {
    // Portfolio level metrics
    pub status: String,
    pub portfolio_name: String,
    pub num_trades: f32,
    pub duration: f32, // Duration in years

    // Overview
    pub market_value: f32,
    pub peak_equity: f32,
    pub cash_injection: f32,
    pub net_realized_pnl: f32,
    pub composition: Vec<f32>,

    // Return metrics
    pub gross_return: f32,
    pub net_return: f32,
    pub annualized_return: f32,
    pub win_rate: f32,
    pub profit_factor: f32,

    // Risk metrics
    pub max_drawdown: f32,
    pub max_drawdown_duration: f32,
    pub sharpe_ratio: f32,
    pub sortino_ratio: f32,
    pub calmar_ratio: f32,
    pub risk_free_rate: f32,

    // Position metrics
    pub position_metrics: Vec<PositionMetricsResponse>,
}

// Response structure for PositionMetrics
#[derive(Debug, Serialize)]
pub struct PositionMetricsResponse {
    pub status: String,
    pub asset_name: u32,
    pub num_trades: f32,

    // Overview
    pub realized_pnl_net: f32,
    pub unrealized_pnl_net: f32,
    pub alpha: f32,
    pub beta: f32,

    // Return metrics
    pub gross_return: f32,
    pub net_return: f32,
    pub annualized_return: f32,
    pub win_rate: f32,
    pub profit_factor: f32,

    // Contribution metrics
    pub take_profit_gain_pct: f32,
    pub take_profit_loss_pct: f32,
    pub stop_loss_gain_pct: f32,
    pub stop_loss_loss_pct: f32,
    pub signal_sell_gain_pct: f32,
    pub signal_sell_loss_pct: f32,

    // Trade metrics
    pub take_profit_trades_pct: f32,
    pub stop_loss_trades_pct: f32,
    pub signal_sell_trades_pct: f32,
    pub sell_pct: f32,
    pub buy_pct: f32,

    pub net_position: Vec<f32>,
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

// Helper function to convert KeyMetrics to response format
fn key_metrics_to_response(metrics: &KeyMetrics, tickers: &[String]) -> KeyMetricsResponse {
    let position_metrics_response: Vec<PositionMetricsResponse> = metrics
        .position_metrics
        .iter()
        .map(|pos_metrics| {
            let _ticker_name = tickers
                .get(pos_metrics.asset_name as usize)
                .cloned()
                .unwrap_or_else(|| format!("Ticker-{}", pos_metrics.asset_name));

            PositionMetricsResponse {
                status: match pos_metrics.status {
                    crate::trading::position::PositionStatus::Open => "Open".to_string(),
                    crate::trading::position::PositionStatus::Closed => "Closed".to_string(),
                },
                asset_name: pos_metrics.asset_name,
                num_trades: pos_metrics.num_trades,
                realized_pnl_net: pos_metrics.realized_pnl_net,
                unrealized_pnl_net: pos_metrics.unrealized_pnl_net,
                alpha: pos_metrics.alpha,
                beta: pos_metrics.beta,
                gross_return: pos_metrics.gross_return,
                net_return: pos_metrics.net_return,
                annualized_return: pos_metrics.annualized_return,
                win_rate: pos_metrics.win_rate,
                profit_factor: pos_metrics.profit_factor,
                take_profit_gain_pct: pos_metrics.take_profit_gain_pct,
                take_profit_loss_pct: pos_metrics.take_profit_loss_pct,
                stop_loss_gain_pct: pos_metrics.stop_loss_gain_pct,
                stop_loss_loss_pct: pos_metrics.stop_loss_loss_pct,
                signal_sell_gain_pct: pos_metrics.signal_sell_gain_pct,
                signal_sell_loss_pct: pos_metrics.signal_sell_loss_pct,
                take_profit_trades_pct: pos_metrics.take_profit_trades_pct,
                stop_loss_trades_pct: pos_metrics.stop_loss_trades_pct,
                signal_sell_trades_pct: pos_metrics.signal_sell_trades_pct,
                sell_pct: pos_metrics.sell_pct,
                buy_pct: pos_metrics.buy_pct,
                net_position: pos_metrics.net_position.clone(),
            }
        })
        .collect();

    KeyMetricsResponse {
        status: metrics.status.clone(),
        portfolio_name: metrics.portfolio_name.clone(),
        num_trades: metrics.num_trades,
        duration: metrics.duration,
        market_value: metrics.market_value,
        peak_equity: metrics.peak_equity,
        cash_injection: metrics.cash_injection,
        net_realized_pnl: metrics.net_realized_pnl,
        composition: metrics.composition.clone(),
        gross_return: metrics.gross_return,
        net_return: metrics.net_return,
        annualized_return: metrics.annualized_return,
        win_rate: metrics.win_rate,
        profit_factor: metrics.profit_factor,
        max_drawdown: metrics.max_drawdown,
        max_drawdown_duration: metrics.max_drawdown_duration,
        sharpe_ratio: metrics.sharpe_ratio,
        sortino_ratio: metrics.sortino_ratio,
        calmar_ratio: metrics.calmar_ratio,
        position_metrics: position_metrics_response,
        risk_free_rate: metrics.risk_free_rate,
    }
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

    // Store tickers for use in response
    let tickers = request.tickers.clone();

    // Run the backtest
    let backtest_result = backtest(
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

    // Calculate KeyMetrics with 5% risk-free rate
    let key_metrics = KeyMetrics::new(&backtest_result, 0.05);

    // Convert Portfolio to BacktestResponse
    let portfolio = &backtest_result.portfolio;
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
    let timestamps = backtest_result
        .executed_trades_by_date
        .values()
        .flatten()
        .map(|t| t.execution_timestamp as i64)
        .collect();

    let response = BacktestResponse {
        backtest_id: request.backtest_id,
        portfolio_name: portfolio.name.clone(),
        initial_value,
        final_value,
        total_return,
        max_value,
        min_value,
        peak_equity: portfolio.peak_equity,
        equity_curve: portfolio.equity_curve.clone(),
        cash_curve: portfolio.cash_curve.clone(),
        notional_curve: portfolio.notional_curve.clone(),
        cost_curve: portfolio.cost_curve.clone(),
        realized_pnl_curve: portfolio.realized_pnl_curve.clone(),
        unrealized_pnl_curve: portfolio.unrealized_pnl_curve.clone(),
        timestamps: timestamps,
        trade_timestamps: backtest_result
            .executed_trades_by_date
            .keys()
            .cloned()
            .collect(),
        total_records,
        tickers: tickers.clone(),
        key_metrics: key_metrics_to_response(&key_metrics, &tickers),
        risk_free_rate: 0.05,
        trade_type_count: TradeTypeCount {
            executed: backtest_result
                .trades_type_count
                .get(0)
                .copied()
                .unwrap_or(0),
            failed_insufficient_cash: backtest_result
                .trades_type_count
                .get(1)
                .copied()
                .unwrap_or(0),
            failed_short_sell_prohibited: backtest_result
                .trades_type_count
                .get(2)
                .copied()
                .unwrap_or(0),
            failed_cool_down_period: backtest_result
                .trades_type_count
                .get(3)
                .copied()
                .unwrap_or(0),
            rejected_holding_period_too_short: backtest_result
                .trades_type_count
                .get(4)
                .copied()
                .unwrap_or(0),
            rejected_cool_down_after_loss: backtest_result
                .trades_type_count
                .get(5)
                .copied()
                .unwrap_or(0),
            rejected_trade_size_too_small: backtest_result
                .trades_type_count
                .get(6)
                .copied()
                .unwrap_or(0),
            rejected_short_sell_prohibited: backtest_result
                .trades_type_count
                .get(7)
                .copied()
                .unwrap_or(0),
        },
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
