use crate::analysis::backtest::BacktestResult;
use crate::trading::position::{Position, PositionStatus};
use crate::trading::trade::{Trade, TradeType};
use crate::utils::utils::timestamp_to_est_date;
use std::collections::HashMap;
use std::time::Instant;

#[derive(Debug, Clone)]
pub struct PositionMetrics {
    // position level metrics
    pub status: PositionStatus,
    pub asset_name: u32,
    pub num_trades: f32,
    // overview
    pub realized_pnl_net: f32,
    pub unrealized_pnl_net: f32,
    pub alpha: f32,
    pub beta: f32,

    //return metrics
    pub gross_return: f32,
    pub net_return: f32,
    pub annualized_return: f32,
    pub win_rate: f32,
    pub profit_factor: f32,

    // contribution metrics - against realized pnl
    pub take_profit_gain_pct: f32,
    pub take_profit_loss_pct: f32,
    pub stop_loss_gain_pct: f32,
    pub stop_loss_loss_pct: f32,
    pub signal_sell_gain_pct: f32,
    pub signal_sell_loss_pct: f32,
    pub liquidation_gain_pct: f32,
    pub liquidation_loss_pct: f32,

    // trade metrics
    pub take_profit_trades_pct: f32,
    pub stop_loss_trades_pct: f32,
    pub signal_sell_trades_pct: f32,
    pub liquidation_trades_pct: f32,
    pub sell_pct: f32,
    pub buy_pct: f32,

    pub net_position: Vec<f32>,
}

impl PositionMetrics {
    pub fn from_position(
        position: &Position,
        price: f32,
        backtest_end_timestamp: u64,
        aggregate_trades: TradeMetrics,
    ) -> Self {
        let curr_mv = position.quantity * price;
        let ticker_id = position.ticker_id as usize;
        let num_trades = aggregate_trades.position_sell_count[ticker_id]
            + aggregate_trades.position_buy_count[ticker_id];
        let profiting_trades_cnt = aggregate_trades.position_total_win_trades[ticker_id] as f32;
        let realized_pnl_net = position.realized_pnl_net;
        let net_return = (position.cum_sell_proceeds + curr_mv
            - position.cum_buy_proceeds
            - position.cum_buy_cost
            - position.cum_sell_cost)
            / (position.cum_buy_proceeds + position.cum_buy_cost);

        let position_metrics = Self {
            status: position.position_status,
            asset_name: ticker_id as u32,
            num_trades: num_trades,

            realized_pnl_net: realized_pnl_net,
            unrealized_pnl_net: curr_mv
                - position.cum_buy_proceeds * (position.quantity / position.total_shares_bought)
                - curr_mv * 0.001,
            alpha: 0.0,
            beta: 0.0,

            gross_return: (position.cum_sell_proceeds + curr_mv - position.cum_buy_proceeds)
                / position.cum_buy_proceeds,
            net_return: net_return,
            annualized_return: calculate_annualized_return(
                net_return,
                position.entry_timestamp as u64,
                if position.position_status == PositionStatus::Closed {
                    position.last_exit_timestamp as u64
                } else {
                    backtest_end_timestamp as u64
                },
            ),
            win_rate: profiting_trades_cnt / aggregate_trades.position_sell_count[ticker_id],
            profit_factor: if aggregate_trades.total_gross_loss > 0.0 {
                aggregate_trades.total_gross_gain / aggregate_trades.total_gross_loss
            } else {
                f32::INFINITY
            },
            take_profit_gain_pct: position.take_profit_gain / realized_pnl_net,
            take_profit_loss_pct: position.take_profit_loss / realized_pnl_net,
            stop_loss_gain_pct: position.stop_loss_gain / realized_pnl_net,
            stop_loss_loss_pct: position.stop_loss_loss / realized_pnl_net,
            signal_sell_gain_pct: position.signal_sell_gain / realized_pnl_net,
            signal_sell_loss_pct: position.signal_sell_loss / realized_pnl_net,
            liquidation_gain_pct: position.liquidation_gain / realized_pnl_net,
            liquidation_loss_pct: position.liquidation_loss / realized_pnl_net,

            take_profit_trades_pct: aggregate_trades.position_take_profit_count[ticker_id]
                / aggregate_trades.position_sell_count[ticker_id],
            stop_loss_trades_pct: aggregate_trades.position_stop_loss_count[ticker_id]
                / aggregate_trades.position_sell_count[ticker_id],
            signal_sell_trades_pct: aggregate_trades.position_signal_sell_count[ticker_id]
                / aggregate_trades.position_sell_count[ticker_id],
            liquidation_trades_pct: aggregate_trades.position_liquidation_count[ticker_id]
                / aggregate_trades.position_sell_count[ticker_id],
            sell_pct: aggregate_trades.position_sell_count[ticker_id] / num_trades,
            buy_pct: aggregate_trades.position_buy_count[ticker_id] / num_trades,

            net_position: position.net_position.clone(),
        };

        position_metrics
    }
}

#[derive(Debug, Clone)]
pub struct TradeMetrics {
    pub daily_net_return: Vec<f32>,
    pub position_gross_loss: Vec<f32>,
    pub position_gross_gain: Vec<f32>,
    pub position_buy_count: Vec<f32>,
    pub position_sell_count: Vec<f32>,
    pub position_take_profit_count: Vec<f32>,
    pub position_stop_loss_count: Vec<f32>,
    pub position_signal_sell_count: Vec<f32>,
    pub position_liquidation_count: Vec<f32>,
    pub position_total_win_trades: Vec<f32>,
    pub position_first_trade: Vec<u64>,
    pub position_last_trade: Vec<u64>,
    pub total_gross_loss: f32,
    pub total_gross_gain: f32,
}

impl TradeMetrics {
    pub fn to_hashmap(&self) -> HashMap<String, Vec<f32>> {
        let mut map = HashMap::with_capacity(10);
        map.insert(
            "daily_net_return".to_string(),
            self.daily_net_return.clone(),
        );
        map.insert(
            "position_gross_loss".to_string(),
            self.position_gross_loss.clone(),
        );
        map.insert(
            "position_gross_gain".to_string(),
            self.position_gross_gain.clone(),
        );
        map.insert(
            "position_buy_count".to_string(),
            self.position_buy_count.clone(),
        );
        map.insert(
            "position_sell_count".to_string(),
            self.position_sell_count.clone(),
        );
        map.insert(
            "position_take_profit_count".to_string(),
            self.position_take_profit_count.clone(),
        );
        map.insert(
            "position_stop_loss_count".to_string(),
            self.position_stop_loss_count.clone(),
        );
        map.insert(
            "position_signal_sell_count".to_string(),
            self.position_signal_sell_count.clone(),
        );
        map.insert(
            "position_liquidation_count".to_string(),
            self.position_liquidation_count.clone(),
        );
        map.insert(
            "position_total_win_trades".to_string(),
            self.position_total_win_trades.clone(),
        );
        map.insert(
            "position_first_trade".to_string(),
            self.position_first_trade
                .iter()
                .map(|&x| x as f32)
                .collect(),
        );
        map.insert(
            "position_last_trade".to_string(),
            self.position_last_trade.iter().map(|&x| x as f32).collect(),
        );
        map
    }
}

#[derive(Debug, Clone)]
pub struct KeyMetrics {
    // overview
    pub status: String,
    pub portfolio_name: String,
    pub num_trades: f32,
    pub duration: f32, // Duration in years

    // overview
    pub market_value: f32,
    pub peak_equity: f32,
    pub cash_injection: f32,
    pub net_realized_pnl: f32,
    pub composition: Vec<f32>,

    // return metrics
    pub gross_return: f32,
    pub net_return: f32,
    pub annualized_return: f32,
    pub win_rate: f32,
    pub profit_factor: f32,

    // cash utilization ratio
    pub cash_utilization_ratio: f32,

    // risk metrics
    pub max_drawdown: f32,
    pub max_drawdown_duration: f32,
    pub sharpe_ratio: f32,
    pub sortino_ratio: f32,
    pub calmar_ratio: f32,

    // position
    pub position_metrics: Vec<PositionMetrics>,
    pub risk_free_rate: f32,
}

impl KeyMetrics {
    pub fn new(backtest_result: &BacktestResult, risk_free_rate: f32) -> Self {
        let timer = Instant::now();
        let portfolio = &backtest_result.portfolio;

        // aggregate trades
        let trades = backtest_result
            .executed_trades_by_date
            .values()
            .flatten()
            .cloned()
            .collect::<Vec<_>>();

        let latest_prices = &backtest_result.exit_price;
        let aggregate_trades = Self::aggregate_trades(&trades, portfolio.num_assets);

        // get position level metrics
        let mut position_metrics = Vec::new();
        for position_option in &portfolio.positions {
            if let Some(position) = position_option {
                position_metrics.push(PositionMetrics::from_position(
                    position,
                    latest_prices[position.ticker_id as usize],
                    backtest_result.end_timestamp,
                    aggregate_trades.clone(),
                ));
            }
        }

        // precalculate intermediate metrics for portfolio level metrics

        let market_value = portfolio
            .holdings
            .iter()
            .zip(latest_prices)
            .map(|(h, p)| h * p)
            .sum::<f32>();
        let total_win_trades = aggregate_trades
            .daily_net_return
            .iter()
            .filter(|&&x| x > 0.0)
            .count() as f32;

        let (max_drawdown, max_drawdown_duration) = calculate_max_drawdown(&portfolio.equity_curve);
        let (sharpe_ratio, sortino_ratio, calmar_ratio) = calculate_risk_metrics(
            &aggregate_trades.daily_net_return,
            risk_free_rate,
            max_drawdown,
        );

        // Calculate duration in years
        let duration = if backtest_result.start_timestamp < backtest_result.end_timestamp {
            let time_diff_seconds =
                (backtest_result.end_timestamp - backtest_result.start_timestamp) as f64;
            (time_diff_seconds / (365.25 * 24.0 * 60.0 * 60.0)) as f32
        } else {
            0.0
        };

        // adding more metrics
        let cash_utilization_ratio = 1.0
            - (if portfolio.status == "Open" {
                portfolio.cash_curve.last().unwrap()
            } else {
                &portfolio.cash_curve[portfolio.cash_curve.len() - 2]
            }) / &portfolio.equity_curve[portfolio.equity_curve.len() - 2];

        let net_return = (portfolio.equity_curve.last().unwrap()
            - portfolio.cost_curve.iter().sum::<f32>()
            - portfolio.total_capital_distribution)
            / portfolio.equity_curve.first().unwrap()
            - 1.0;
        let result = Self {
            gross_return: (portfolio.equity_curve.last().unwrap()
                - portfolio.total_capital_distribution)
                / portfolio.equity_curve.first().unwrap()
                - 1.0,
            net_return: net_return,
            annualized_return: calculate_annualized_return(
                net_return,
                backtest_result.start_timestamp as u64,
                backtest_result.end_timestamp as u64,
            ),

            status: portfolio.status.clone(),
            portfolio_name: portfolio.name.clone(),
            num_trades: aggregate_trades.position_buy_count.iter().sum::<f32>()
                + aggregate_trades.position_sell_count.iter().sum::<f32>(),
            duration,
            market_value: market_value,
            peak_equity: portfolio.peak_equity,
            cash_injection: portfolio.total_capital_distribution,
            net_realized_pnl: portfolio.realized_pnl_curve.iter().sum::<f32>(),
            composition: if market_value > 0.0 {
                portfolio
                    .holdings
                    .iter()
                    .zip(latest_prices)
                    .map(|(h, p)| h * p / market_value)
                    .collect()
            } else {
                vec![0.0; portfolio.num_assets]
            },
            win_rate: total_win_trades
                / aggregate_trades
                    .daily_net_return
                    .iter()
                    .filter(|&&x| x > 0.0)
                    .count() as f32,
            profit_factor: if aggregate_trades.total_gross_loss > 0.0 {
                aggregate_trades.total_gross_gain / aggregate_trades.total_gross_loss
            } else {
                f32::INFINITY
            },
            max_drawdown,
            max_drawdown_duration,
            sharpe_ratio,
            sortino_ratio,
            calmar_ratio,
            position_metrics,
            risk_free_rate,
            cash_utilization_ratio,
        };
        println!(
            "[Timer] Time to run key metrics calculation: {:.3} seconds",
            timer.elapsed().as_secs_f64()
        );
        result
    }

    pub fn aggregate_trades(trades: &[Trade], num_assets: usize) -> TradeMetrics {
        if trades.is_empty() {
            return TradeMetrics {
                daily_net_return: Vec::new(),
                position_gross_loss: vec![0.0; num_assets],
                position_gross_gain: vec![0.0; num_assets],
                position_buy_count: vec![0.0; num_assets],
                position_sell_count: vec![0.0; num_assets],
                position_take_profit_count: vec![0.0; num_assets],
                position_stop_loss_count: vec![0.0; num_assets],
                position_signal_sell_count: vec![0.0; num_assets],
                position_liquidation_count: vec![0.0; num_assets],
                position_total_win_trades: vec![0.0; num_assets],
                position_first_trade: vec![0u64; num_assets],
                position_last_trade: vec![0u64; num_assets],
                total_gross_loss: 0.0,
                total_gross_gain: 0.0,
            };
        }

        let mut total_gross_loss = 0.0;
        let mut total_gross_gain = 0.0;

        let mut position_gross_loss = vec![0.0; num_assets];
        let mut position_gross_gain = vec![0.0; num_assets];
        let mut position_buy_count = vec![0.0; num_assets];
        let mut position_sell_count = vec![0.0; num_assets];
        let mut position_take_profit_count = vec![0.0; num_assets];
        let mut position_stop_loss_count = vec![0.0; num_assets];
        let mut position_signal_sell_count = vec![0.0; num_assets];
        let mut position_liquidation_count = vec![0.0; num_assets];
        let mut position_total_win_trades = vec![0.0; num_assets];

        let mut daily_net_return = Vec::new();

        let mut prev_day = timestamp_to_est_date(trades[0].execution_timestamp as i64);
        let mut daily_pnl_net = 0.0;
        let mut daily_capital_used = 0.0;
        let mut position_daily_pnl_gross = vec![0.0; num_assets];

        let mut position_first_trade = vec![0u64; num_assets];
        let mut position_last_trade = vec![0u64; num_assets];
        let mut position_has_trades = vec![false; num_assets];

        for trade in trades {
            let ticker_id = trade.ticker_id;
            let day = timestamp_to_est_date(trade.execution_timestamp as i64);

            if !position_has_trades[ticker_id] {
                position_first_trade[ticker_id] = trade.execution_timestamp;
                position_has_trades[ticker_id] = true;
            }
            position_last_trade[ticker_id] = trade.execution_timestamp;

            if day != prev_day {
                daily_net_return.push(if daily_capital_used > 0.0 {
                    daily_pnl_net / daily_capital_used
                } else {
                    0.0
                });

                for (i, &pnl) in position_daily_pnl_gross.iter().enumerate() {
                    if pnl > 0.0 {
                        position_total_win_trades[i] += 1.0;
                    }
                }

                prev_day = day;
                daily_pnl_net = 0.0;
                daily_capital_used = 0.0;
                position_daily_pnl_gross.fill(0.0);
            }

            if trade.is_buy() {
                position_buy_count[ticker_id] += 1.0;
            } else {
                let realized_pnl = trade.realized_pnl_gross;
                if realized_pnl > 0.0 {
                    position_gross_gain[ticker_id] += realized_pnl;
                    total_gross_gain += realized_pnl;
                } else {
                    let abs_pnl = realized_pnl.abs();
                    position_gross_loss[ticker_id] += abs_pnl;
                    total_gross_loss += abs_pnl;
                }

                let pnl_net = realized_pnl - trade.pro_rata_buy_cost - trade.cost;
                daily_pnl_net += pnl_net;
                daily_capital_used += trade.avg_entry_price * trade.quantity;
                position_daily_pnl_gross[ticker_id] += realized_pnl;

                match trade.trade_type {
                    TradeType::TakeProfit => position_take_profit_count[ticker_id] += 1.0,
                    TradeType::StopLoss => position_stop_loss_count[ticker_id] += 1.0,
                    TradeType::SignalSell => position_signal_sell_count[ticker_id] += 1.0,
                    TradeType::Liquidation => position_liquidation_count[ticker_id] += 1.0,
                    _ => {}
                }
                position_sell_count[ticker_id] += 1.0;
            }
        }

        daily_net_return.push(if daily_capital_used > 0.0 {
            daily_pnl_net / daily_capital_used
        } else {
            0.0
        });

        for (i, &pnl) in position_daily_pnl_gross.iter().enumerate() {
            if pnl > 0.0 {
                position_total_win_trades[i] += 1.0;
            }
        }

        TradeMetrics {
            daily_net_return,
            position_gross_loss,
            position_gross_gain,
            position_buy_count,
            position_sell_count,
            position_take_profit_count,
            position_stop_loss_count,
            position_signal_sell_count,
            position_liquidation_count,
            position_total_win_trades,
            position_last_trade,
            position_first_trade,
            total_gross_loss,
            total_gross_gain,
        }
    }
}

pub fn calculate_max_drawdown(equity_curve: &[f32]) -> (f32, f32) {
    if equity_curve.len() < 2 {
        return (0.0, 0.0);
    }

    let mut max_equity = equity_curve[0];
    let mut max_drawdown = 0.0;
    let mut max_drawdown_duration = 0.0;
    let mut current_drawdown_duration = 0.0;
    let mut in_drawdown = false;

    for &equity in equity_curve {
        if equity > max_equity {
            max_equity = equity;
            if in_drawdown {
                in_drawdown = false;
                current_drawdown_duration = 0.0;
            }
        } else if equity < max_equity {
            let drawdown = (max_equity - equity) / max_equity;
            if drawdown > max_drawdown {
                max_drawdown = drawdown;
            }

            if !in_drawdown {
                in_drawdown = true;
                current_drawdown_duration = 1.0;
            } else {
                current_drawdown_duration += 1.0;
            }

            if current_drawdown_duration > max_drawdown_duration {
                max_drawdown_duration = current_drawdown_duration;
            }
        }
    }

    (max_drawdown, max_drawdown_duration)
}

pub fn calculate_annualized_return(
    total_return: f32,
    start_timestamp: u64,
    end_timestamp: u64,
) -> f32 {
    if start_timestamp >= end_timestamp {
        return 0.0;
    }

    let time_diff_seconds = (end_timestamp - start_timestamp) as f64;
    let years = time_diff_seconds / (365.25 * 24.0 * 60.0 * 60.0);
    let annualized_return = ((1.0 + total_return as f64).powf(1.0 / years) - 1.0) as f32;
    annualized_return
}

pub fn calculate_risk_metrics(
    daily_returns: &[f32],
    risk_free_rate: f32,
    max_drawdown: f32,
) -> (f32, f32, f32) {
    if daily_returns.is_empty() {
        return (0.0, 0.0, 0.0);
    }

    let avg_daily_return = daily_returns.iter().sum::<f32>() / daily_returns.len() as f32;
    let annualized_return = avg_daily_return * 252.0;

    let daily_rf_rate = risk_free_rate / 252.0;
    let excess_return = avg_daily_return - daily_rf_rate;

    let variance = daily_returns
        .iter()
        .map(|&r| (r - avg_daily_return).powi(2))
        .sum::<f32>()
        / daily_returns.len() as f32;
    let std_dev = variance.sqrt();
    let annualized_volatility = std_dev * (252.0_f32).sqrt();

    let downside_returns: Vec<f32> = daily_returns
        .iter()
        .filter(|&&r| r < avg_daily_return)
        .map(|&r| (r - avg_daily_return).powi(2))
        .collect();

    let downside_variance = if downside_returns.is_empty() {
        0.0
    } else {
        downside_returns.iter().sum::<f32>() / downside_returns.len() as f32
    };
    let downside_deviation = downside_variance.sqrt();
    let annualized_downside_deviation = downside_deviation * (252.0_f32).sqrt();

    let sharpe_ratio = if annualized_volatility > 0.0 {
        (excess_return * 252.0) / annualized_volatility
    } else {
        0.0
    };

    let sortino_ratio = if annualized_downside_deviation > 0.0 {
        (excess_return * 252.0) / annualized_downside_deviation
    } else {
        0.0
    };

    let calmar_ratio = if max_drawdown.abs() > 0.0 {
        annualized_return / max_drawdown.abs()
    } else {
        0.0
    };

    (sharpe_ratio, sortino_ratio, calmar_ratio)
}
