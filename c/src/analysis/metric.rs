use crate::trading::position::{Position, PositionStatus};
use crate::trading::trade::{Trade, TradeStatus, TradeType};
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct PositionPerformance {
    pub ticker_id: u32,
    pub quantity: f32,
    pub sell_cost_ratio: f32, // cum_sell_cost/(cum_sell_cost + cum_buy_cost)
    pub buy_cost_ratio: f32,  // cum_buy_cost/(cum_sell_cost + cum_buy_cost)
    pub total_cum_cost: f32,  // cum_sell_cost + cum_buy_cost
    pub realized_pnl: f32,
    pub take_profit_gain: f32,
    pub take_profit_loss: f32,
    pub stop_loss_gain: f32,
    pub stop_loss_loss: f32,
    pub signal_sell_gain: f32,
    pub signal_sell_loss: f32,
    pub position_status: PositionStatus,

    // Percentage calculations against realized PnL
    pub take_profit_gain_pct: f32,
    pub take_profit_loss_pct: f32,
    pub stop_loss_gain_pct: f32,
    pub stop_loss_loss_pct: f32,
    pub signal_sell_gain_pct: f32,
    pub signal_sell_loss_pct: f32,

    // Return calculations
    pub realized_ratio: f32,        // total_sold_shares / total_bought_shares
    pub gross_realized_return: f32, // (cum_sell_proceeds - cum_buy_proceeds * realized_ratio) / (cum_buy_proceeds * realized_ratio)
    pub net_realized_return: f32,   // same as gross but net of costs
    pub gross_unrealized_return: f32, // for remaining position
    pub net_unrealized_return: f32, // for remaining position
}

#[derive(Debug, Clone)]
pub struct TradeMetrics {
    // Per ticker metrics
    pub ticker_metrics: HashMap<usize, TickerTradeMetrics>,
    // Overall metrics
    pub total_trades: usize,
    pub total_buy_trades: usize,
    pub total_sell_trades: usize,
    pub overall_win_rate: f32,
    pub overall_avg_gross_return: f32,
    pub overall_avg_net_return: f32,
}

#[derive(Debug, Clone)]
pub struct TickerTradeMetrics {
    pub ticker_id: usize,
    pub total_trades: usize,
    pub buy_trades: usize,
    pub sell_trades: usize,
    pub avg_trades_per_day: f32,
    pub avg_buy_trades_per_day: f32,
    pub avg_sell_trades_per_day: f32,
    pub buy_trade_pct: f32,
    pub sell_trade_pct: f32,

    // Trade status breakdown
    pub executed_trades: usize,
    pub failed_trades: usize,
    pub rejected_trades: usize,
    pub pending_trades: usize,
    pub executed_pct: f32,
    pub failed_pct: f32,
    pub rejected_pct: f32,
    pub pending_pct: f32,

    // Sell trade specific metrics
    pub sell_trades_with_holding_period: usize,
    pub avg_holding_period_minutes: f32,
    pub max_holding_period_minutes: f32,
    pub min_holding_period_minutes: f32,

    // Return metrics
    pub sell_trades_with_returns: usize,
    pub avg_gross_return: f32,
    pub avg_net_return: f32,
    pub win_rate: f32,

    // Daily metrics
    pub trading_days: usize,
    pub avg_win_rate_per_day: f32,
}

impl TradeMetrics {
    pub fn from_trades(trades: &[Trade]) -> Self {
        let mut ticker_metrics: HashMap<usize, TickerTradeMetrics> = HashMap::new();
        let mut total_trades = 0;
        let mut total_buy_trades = 0;
        let mut total_sell_trades = 0;
        let mut total_wins = 0;
        let mut total_gross_return_sum = 0.0;
        let mut total_net_return_sum = 0.0;
        let mut total_sell_trades_with_returns = 0;

        // Group trades by ticker and day
        let mut trades_by_ticker: HashMap<usize, Vec<&Trade>> = HashMap::new();
        let mut trades_by_day: HashMap<u64, Vec<&Trade>> = HashMap::new();

        for trade in trades {
            let ticker_id = trade.ticker_id;
            let day = trade.generated_at / (24 * 60 * 60); // Convert minutes to days

            trades_by_ticker
                .entry(ticker_id)
                .or_insert_with(Vec::new)
                .push(trade);
            trades_by_day
                .entry(day)
                .or_insert_with(Vec::new)
                .push(trade);

            total_trades += 1;
            if trade.is_buy() {
                total_buy_trades += 1;
            } else {
                total_sell_trades += 1;
            }
        }

        // Calculate metrics for each ticker
        for (ticker_id, ticker_trades) in &trades_by_ticker {
            let mut buy_trades = 0;
            let mut sell_trades = 0;
            let mut executed_trades = 0;
            let mut failed_trades = 0;
            let mut rejected_trades = 0;
            let mut pending_trades = 0;

            let mut holding_periods: Vec<u64> = Vec::new();
            let mut gross_returns: Vec<f32> = Vec::new();
            let mut net_returns: Vec<f32> = Vec::new();
            let mut wins = 0;

            let mut trading_days_set = std::collections::HashSet::new();
            let mut executed_trading_days_set = std::collections::HashSet::new();
            let mut sell_trading_days_set = std::collections::HashSet::new();

            for trade in ticker_trades {
                // Count by trade type
                if trade.is_buy() {
                    buy_trades += 1;
                } else {
                    sell_trades += 1;
                }

                // Count by status
                match trade.trade_status {
                    TradeStatus::Executed => executed_trades += 1,
                    TradeStatus::Failed => failed_trades += 1,
                    TradeStatus::Rejected => rejected_trades += 1,
                    TradeStatus::Pending => pending_trades += 1,
                }

                // Track trading days - any trade activity
                let day = trade.generated_at / (24 * 60 * 60);
                trading_days_set.insert(day);

                // Track days with executed trades only
                if trade.trade_status == TradeStatus::Executed {
                    executed_trading_days_set.insert(day);
                }

                // Track days with sell trades only
                if !trade.is_buy() {
                    sell_trading_days_set.insert(day);
                }

                // Calculate sell trade specific metrics
                if !trade.is_buy() && trade.holding_period > 0 {
                    holding_periods.push(trade.holding_period);
                }

                // Calculate return metrics for executed sell trades
                if !trade.is_buy()
                    && trade.trade_status == TradeStatus::Executed
                    && trade.price > 0.0
                {
                    let gross_return = if trade.avg_entry_price > 0.0 {
                        trade.realized_pnl_gross / (trade.avg_entry_price * trade.quantity)
                    } else {
                        0.0
                    };
                    gross_returns.push(gross_return);

                    let net_return = if trade.avg_entry_price > 0.0 {
                        (trade.realized_pnl_gross - trade.pro_rata_buy_cost - trade.cost)
                            / (trade.avg_entry_price * trade.quantity + trade.pro_rata_buy_cost)
                    } else {
                        0.0
                    };
                    net_returns.push(net_return);

                    if gross_return > 0.0 {
                        wins += 1;
                    }
                }
            }

            let total_trading_days = trading_days_set.len();
            let executed_trading_days = executed_trading_days_set.len();
            let sell_trading_days = sell_trading_days_set.len();

            // Use appropriate day counts for different metrics
            let avg_trades_per_day = if total_trading_days > 0 {
                ticker_trades.len() as f32 / total_trading_days as f32
            } else {
                0.0
            };

            let avg_buy_trades_per_day = if total_trading_days > 0 {
                buy_trades as f32 / total_trading_days as f32
            } else {
                0.0
            };

            let avg_sell_trades_per_day = if total_trading_days > 0 {
                sell_trades as f32 / total_trading_days as f32
            } else {
                0.0
            };

            let buy_trade_pct = if ticker_trades.len() > 0 {
                buy_trades as f32 / ticker_trades.len() as f32 * 100.0
            } else {
                0.0
            };

            let sell_trade_pct = if ticker_trades.len() > 0 {
                sell_trades as f32 / ticker_trades.len() as f32 * 100.0
            } else {
                0.0
            };

            let executed_pct = if ticker_trades.len() > 0 {
                executed_trades as f32 / ticker_trades.len() as f32 * 100.0
            } else {
                0.0
            };

            let failed_pct = if ticker_trades.len() > 0 {
                failed_trades as f32 / ticker_trades.len() as f32 * 100.0
            } else {
                0.0
            };

            let rejected_pct = if ticker_trades.len() > 0 {
                rejected_trades as f32 / ticker_trades.len() as f32 * 100.0
            } else {
                0.0
            };

            let pending_pct = if ticker_trades.len() > 0 {
                pending_trades as f32 / ticker_trades.len() as f32 * 100.0
            } else {
                0.0
            };

            let avg_holding_period_minutes = if !holding_periods.is_empty() {
                holding_periods.iter().sum::<u64>() as f32 / holding_periods.len() as f32
            } else {
                0.0
            };

            let max_holding_period_minutes =
                holding_periods.iter().max().copied().unwrap_or(0) as f32;
            let min_holding_period_minutes =
                holding_periods.iter().min().copied().unwrap_or(0) as f32;

            let avg_gross_return = if !gross_returns.is_empty() {
                gross_returns.iter().sum::<f32>() / gross_returns.len() as f32
            } else {
                0.0
            };

            let avg_net_return = if !net_returns.is_empty() {
                net_returns.iter().sum::<f32>() / net_returns.len() as f32
            } else {
                0.0
            };

            let win_rate = if !gross_returns.is_empty() {
                wins as f32 / gross_returns.len() as f32 * 100.0
            } else {
                0.0
            };

            // Calculate daily win rate - use days with executed sell trades
            let mut daily_wins = 0;
            let mut daily_trades = 0;
            for (day, day_trades) in &trades_by_day {
                let day_sell_trades: Vec<&&Trade> = day_trades
                    .iter()
                    .filter(|t| {
                        t.ticker_id == *ticker_id
                            && !t.is_buy()
                            && t.trade_status == TradeStatus::Executed
                            && t.price > 0.0
                    })
                    .collect();

                if !day_sell_trades.is_empty() {
                    daily_trades += 1;
                    // Check if ANY trade on this day was a winner
                    let has_winning_trade = day_sell_trades.iter().any(|t| {
                        let gross_return = if t.avg_entry_price > 0.0 {
                            t.realized_pnl_gross / (t.avg_entry_price * t.quantity)
                        } else {
                            0.0
                        };
                        gross_return > 0.0
                    });
                    if has_winning_trade {
                        daily_wins += 1;
                    }
                }
            }

            let avg_win_rate_per_day = if daily_trades > 0 {
                daily_wins as f32 / daily_trades as f32 * 100.0
            } else {
                0.0
            };

            // Update overall totals
            if !gross_returns.is_empty() {
                total_wins += wins;
                total_gross_return_sum += gross_returns.iter().sum::<f32>();
                total_net_return_sum += net_returns.iter().sum::<f32>();
                total_sell_trades_with_returns += gross_returns.len();
            }

            ticker_metrics.insert(
                *ticker_id,
                TickerTradeMetrics {
                    ticker_id: *ticker_id,
                    total_trades: ticker_trades.len(),
                    buy_trades,
                    sell_trades,
                    avg_trades_per_day,
                    avg_buy_trades_per_day,
                    avg_sell_trades_per_day,
                    buy_trade_pct,
                    sell_trade_pct,
                    executed_trades,
                    failed_trades,
                    rejected_trades,
                    pending_trades,
                    executed_pct,
                    failed_pct,
                    rejected_pct,
                    pending_pct,
                    sell_trades_with_holding_period: holding_periods.len(),
                    avg_holding_period_minutes,
                    max_holding_period_minutes,
                    min_holding_period_minutes,
                    sell_trades_with_returns: gross_returns.len(),
                    avg_gross_return,
                    avg_net_return,
                    win_rate,
                    trading_days: total_trading_days,
                    avg_win_rate_per_day,
                },
            );
        }

        // Calculate overall metrics
        let overall_win_rate = if total_sell_trades_with_returns > 0 {
            total_wins as f32 / total_sell_trades_with_returns as f32 * 100.0
        } else {
            0.0
        };

        let overall_avg_gross_return = if total_sell_trades_with_returns > 0 {
            total_gross_return_sum / total_sell_trades_with_returns as f32
        } else {
            0.0
        };

        let overall_avg_net_return = if total_sell_trades_with_returns > 0 {
            total_net_return_sum / total_sell_trades_with_returns as f32
        } else {
            0.0
        };

        Self {
            ticker_metrics,
            total_trades,
            total_buy_trades,
            total_sell_trades,
            overall_win_rate,
            overall_avg_gross_return,
            overall_avg_net_return,
        }
    }
}

impl PositionPerformance {
    pub fn from_position(position: &Position) -> Self {
        let total_cum_cost = position.cum_sell_cost + position.cum_buy_cost;
        let sell_cost_ratio = if total_cum_cost > 0.0 {
            position.cum_sell_cost / total_cum_cost
        } else {
            0.0
        };
        let buy_cost_ratio = if total_cum_cost > 0.0 {
            position.cum_buy_cost / total_cum_cost
        } else {
            0.0
        };

        // Calculate percentages against realized PnL
        let realized_pnl_abs = position.realized_pnl_gross.abs();
        let take_profit_gain_pct = if realized_pnl_abs > 0.0 {
            position.take_profit_gain / realized_pnl_abs * 100.0
        } else {
            0.0
        };
        let take_profit_loss_pct = if realized_pnl_abs > 0.0 {
            position.take_profit_loss.abs() / realized_pnl_abs * 100.0
        } else {
            0.0
        };
        let stop_loss_gain_pct = if realized_pnl_abs > 0.0 {
            position.stop_loss_gain / realized_pnl_abs * 100.0
        } else {
            0.0
        };
        let stop_loss_loss_pct = if realized_pnl_abs > 0.0 {
            position.stop_loss_loss.abs() / realized_pnl_abs * 100.0
        } else {
            0.0
        };
        let signal_sell_gain_pct = if realized_pnl_abs > 0.0 {
            position.signal_sell_gain / realized_pnl_abs * 100.0
        } else {
            0.0
        };
        let signal_sell_loss_pct = if realized_pnl_abs > 0.0 {
            position.signal_sell_loss.abs() / realized_pnl_abs * 100.0
        } else {
            0.0
        };

        // Calculate realized ratio
        let realized_ratio = if position.total_shares_bought > 0.0 {
            position.total_shares_sold / position.total_shares_bought
        } else {
            0.0
        };

        // Calculate gross realized return
        let gross_realized_return = if position.cum_buy_proceeds * realized_ratio > 0.0 {
            (position.cum_sell_proceeds - position.cum_buy_proceeds * realized_ratio)
                / (position.cum_buy_proceeds * realized_ratio)
        } else {
            0.0
        };

        // Calculate net realized return
        let net_realized_return =
            if (position.cum_buy_proceeds + position.cum_buy_cost) * realized_ratio > 0.0 {
                (position.cum_sell_proceeds
                    - position.cum_sell_cost
                    - (position.cum_buy_proceeds + position.cum_buy_cost) * realized_ratio)
                    / ((position.cum_buy_proceeds + position.cum_buy_cost) * realized_ratio)
            } else {
                0.0
            };

        // Calculate unrealized returns for remaining position
        // let remaining_ratio = 1.0 - realized_ratio;
        // let gross_unrealized_return = if position.cum_buy_proceeds * remaining_ratio > 0.0 {
        //     (position.quantity * position.avg_entry_price
        //         - position.cum_buy_proceeds * remaining_ratio)
        //         / (position.cum_buy_proceeds * remaining_ratio)
        // } else {
        //     0.0
        // };

        // let net_unrealized_return =
        //     if (position.cum_buy_proceeds + position.cum_buy_cost) * remaining_ratio > 0.0 {
        //         (position.quantity * position.avg_entry_price
        //             - (position.cum_buy_proceeds + position.cum_buy_cost) * remaining_ratio)
        //             / ((position.cum_buy_proceeds + position.cum_buy_cost) * remaining_ratio)
        //     } else {
        //         0.0
        //     };
        let gross_unrealized_return = 0.0;
        let net_unrealized_return = 0.0;

        Self {
            ticker_id: position.ticker_id,
            quantity: position.quantity,
            sell_cost_ratio,
            buy_cost_ratio,
            total_cum_cost,
            realized_pnl: position.realized_pnl_gross,
            take_profit_gain: position.take_profit_gain,
            take_profit_loss: position.take_profit_loss,
            stop_loss_gain: position.stop_loss_gain,
            stop_loss_loss: position.stop_loss_loss,
            signal_sell_gain: position.signal_sell_gain,
            signal_sell_loss: position.signal_sell_loss,
            position_status: position.position_status,
            take_profit_gain_pct,
            take_profit_loss_pct,
            stop_loss_gain_pct,
            stop_loss_loss_pct,
            signal_sell_gain_pct,
            signal_sell_loss_pct,
            realized_ratio,
            gross_realized_return,
            net_realized_return,
            gross_unrealized_return,
            net_unrealized_return,
        }
    }
}
