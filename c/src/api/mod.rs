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
use crate::analysis::metric::{PositionPerformance, TradeMetrics};
use crate::core::params::{
    PortfolioConstraintParams, PortfolioParams, PositionConstraintParams, SignalParams,
};
use crate::data::database_service;
use crate::trading::position::PositionStatus;

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
    pub tickers: Vec<String>,
    // New metric fields
    pub position_performances: Option<Vec<PositionPerformanceResponse>>,
    pub trade_metrics: Option<TradeMetricsResponse>,
}

// Response structures for metrics (to handle serialization properly)
#[derive(Debug, Serialize)]
pub struct PositionPerformanceResponse {
    pub ticker_id: u32,
    pub ticker_name: String,
    pub quantity: f32,
    pub sell_cost_ratio: f32,
    pub buy_cost_ratio: f32,
    pub total_cum_cost: f32,
    pub realized_pnl: f32,
    pub take_profit_gain: f32,
    pub take_profit_loss: f32,
    pub stop_loss_gain: f32,
    pub stop_loss_loss: f32,
    pub signal_sell_gain: f32,
    pub signal_sell_loss: f32,
    pub position_status: String, // "Open" or "Closed"
    pub take_profit_gain_pct: f32,
    pub take_profit_loss_pct: f32,
    pub stop_loss_gain_pct: f32,
    pub stop_loss_loss_pct: f32,
    pub signal_sell_gain_pct: f32,
    pub signal_sell_loss_pct: f32,
    pub realized_ratio: f32,
    pub gross_realized_return: f32,
    pub net_realized_return: f32,
    pub gross_unrealized_return: f32,
    pub net_unrealized_return: f32,
}

#[derive(Debug, Serialize)]
pub struct TickerTradeMetricsResponse {
    pub ticker_id: usize,
    pub ticker_name: String,
    pub total_trades: usize,
    pub buy_trades: usize,
    pub sell_trades: usize,
    pub avg_trades_per_day: f32,
    pub avg_buy_trades_per_day: f32,
    pub avg_sell_trades_per_day: f32,
    pub buy_trade_pct: f32,
    pub sell_trade_pct: f32,
    pub executed_trades: usize,
    pub failed_trades: usize,
    pub rejected_trades: usize,
    pub pending_trades: usize,
    pub executed_pct: f32,
    pub failed_pct: f32,
    pub rejected_pct: f32,
    pub pending_pct: f32,
    pub sell_trades_with_holding_period: usize,
    pub avg_holding_period_minutes: f32,
    pub max_holding_period_minutes: f32,
    pub min_holding_period_minutes: f32,
    pub sell_trades_with_returns: usize,
    pub avg_gross_return: f32,
    pub avg_net_return: f32,
    pub win_rate: f32,
    pub trading_days: usize,
    pub avg_win_rate_per_day: f32,
}

#[derive(Debug, Serialize)]
pub struct TradeMetricsResponse {
    pub ticker_metrics: HashMap<String, TickerTradeMetricsResponse>, // String key for JSON serialization
    pub total_trades: usize,
    pub total_buy_trades: usize,
    pub total_sell_trades: usize,
    pub overall_win_rate: f32,
    pub overall_avg_gross_return: f32,
    pub overall_avg_net_return: f32,
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

// Helper function to convert PositionPerformance to response format
fn position_performance_to_response(
    perf: &PositionPerformance,
    tickers: &[String],
) -> PositionPerformanceResponse {
    let ticker_name = tickers
        .get(perf.ticker_id as usize)
        .cloned()
        .unwrap_or_else(|| format!("Ticker-{}", perf.ticker_id));

    PositionPerformanceResponse {
        ticker_id: perf.ticker_id,
        ticker_name,
        quantity: perf.quantity,
        sell_cost_ratio: perf.sell_cost_ratio,
        buy_cost_ratio: perf.buy_cost_ratio,
        total_cum_cost: perf.total_cum_cost,
        realized_pnl: perf.realized_pnl,
        take_profit_gain: perf.take_profit_gain,
        take_profit_loss: perf.take_profit_loss,
        stop_loss_gain: perf.stop_loss_gain,
        stop_loss_loss: perf.stop_loss_loss,
        signal_sell_gain: perf.signal_sell_gain,
        signal_sell_loss: perf.signal_sell_loss,
        position_status: match perf.position_status {
            PositionStatus::Open => "Open".to_string(),
            PositionStatus::Closed => "Closed".to_string(),
        },
        take_profit_gain_pct: perf.take_profit_gain_pct,
        take_profit_loss_pct: perf.take_profit_loss_pct,
        stop_loss_gain_pct: perf.stop_loss_gain_pct,
        stop_loss_loss_pct: perf.stop_loss_loss_pct,
        signal_sell_gain_pct: perf.signal_sell_gain_pct,
        signal_sell_loss_pct: perf.signal_sell_loss_pct,
        realized_ratio: perf.realized_ratio,
        gross_realized_return: perf.gross_realized_return,
        net_realized_return: perf.net_realized_return,
        gross_unrealized_return: perf.gross_unrealized_return,
        net_unrealized_return: perf.net_unrealized_return,
    }
}

// Helper function to convert TradeMetrics to response format
fn trade_metrics_to_response(metrics: &TradeMetrics, tickers: &[String]) -> TradeMetricsResponse {
    let mut ticker_metrics_response = HashMap::new();

    for (ticker_id, ticker_metrics) in &metrics.ticker_metrics {
        let ticker_name = tickers
            .get(*ticker_id)
            .cloned()
            .unwrap_or_else(|| format!("Ticker-{}", ticker_id));

        ticker_metrics_response.insert(
            ticker_id.to_string(),
            TickerTradeMetricsResponse {
                ticker_id: ticker_metrics.ticker_id,
                ticker_name,
                total_trades: ticker_metrics.total_trades,
                buy_trades: ticker_metrics.buy_trades,
                sell_trades: ticker_metrics.sell_trades,
                avg_trades_per_day: ticker_metrics.avg_trades_per_day,
                avg_buy_trades_per_day: ticker_metrics.avg_buy_trades_per_day,
                avg_sell_trades_per_day: ticker_metrics.avg_sell_trades_per_day,
                buy_trade_pct: ticker_metrics.buy_trade_pct,
                sell_trade_pct: ticker_metrics.sell_trade_pct,
                executed_trades: ticker_metrics.executed_trades,
                failed_trades: ticker_metrics.failed_trades,
                rejected_trades: ticker_metrics.rejected_trades,
                pending_trades: ticker_metrics.pending_trades,
                executed_pct: ticker_metrics.executed_pct,
                failed_pct: ticker_metrics.failed_pct,
                rejected_pct: ticker_metrics.rejected_pct,
                pending_pct: ticker_metrics.pending_pct,
                sell_trades_with_holding_period: ticker_metrics.sell_trades_with_holding_period,
                avg_holding_period_minutes: ticker_metrics.avg_holding_period_minutes,
                max_holding_period_minutes: ticker_metrics.max_holding_period_minutes,
                min_holding_period_minutes: ticker_metrics.min_holding_period_minutes,
                sell_trades_with_returns: ticker_metrics.sell_trades_with_returns,
                avg_gross_return: ticker_metrics.avg_gross_return,
                avg_net_return: ticker_metrics.avg_net_return,
                win_rate: ticker_metrics.win_rate,
                trading_days: ticker_metrics.trading_days,
                avg_win_rate_per_day: ticker_metrics.avg_win_rate_per_day,
            },
        );
    }

    TradeMetricsResponse {
        ticker_metrics: ticker_metrics_response,
        total_trades: metrics.total_trades,
        total_buy_trades: metrics.total_buy_trades,
        total_sell_trades: metrics.total_sell_trades,
        overall_win_rate: metrics.overall_win_rate,
        overall_avg_gross_return: metrics.overall_avg_gross_return,
        overall_avg_net_return: metrics.overall_avg_net_return,
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

    // Calculate position performances
    let position_performances: Vec<PositionPerformance> = portfolio
        .positions
        .iter()
        .enumerate()
        .filter_map(|(ticker_id, position_opt)| {
            position_opt
                .as_ref()
                .map(|position| PositionPerformance::from_position(position))
        })
        .collect();

    // Calculate trade metrics
    let all_trades: Vec<_> = executed_trades_by_date
        .values()
        .flatten()
        .cloned()
        .collect();
    let trade_metrics = TradeMetrics::from_trades(&all_trades);

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
    let timestamps = executed_trades_by_date
        .values()
        .flatten()
        .map(|t| t.execution_timestamp as i64)
        .collect();

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
        timestamps: timestamps,
        trade_timestamps: executed_trades_by_date.keys().cloned().collect(),
        total_records,
        tickers: tickers.clone(),
        position_performances: Some(
            position_performances
                .iter()
                .map(|perf| position_performance_to_response(perf, &tickers))
                .collect(),
        ),
        trade_metrics: Some(trade_metrics_to_response(&trade_metrics, &tickers)),
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
