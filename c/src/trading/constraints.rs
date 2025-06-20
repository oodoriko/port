use crate::params::PositionConstraintParams;
use crate::position::Position;
use crate::trade::Trade;

pub struct Constraint {
    pub max_position_size_pct: Vec<f32>,
    pub min_trade_size_pct: Vec<f32>,
    pub min_holding_candle: Vec<u64>,
    pub trailing_stop_loss_pct: Vec<f32>,
    pub trailing_stop_update_threshold_pct: Vec<f32>,
    pub max_drawdown_pct: f32,
    pub rebalance_threshold_pct: f32,
    pub take_profit_pct: Vec<f32>,
    pub risk_per_trade_pct: Vec<f32>,
    pub sell_fraction: Vec<f32>,
    pub candle_time: u64,
}

impl Constraint {
    pub fn from_position_constraints(position_constraints: &[PositionConstraintParams]) -> Self {
        let mut max_position_size_pct = Vec::new();
        let mut min_trade_size_pct = Vec::new();
        let mut min_holding_candle = Vec::new();
        let mut trailing_stop_loss_pct = Vec::new();
        let mut trailing_stop_update_threshold_pct = Vec::new();
        let mut take_profit_pct = Vec::new();
        let mut risk_per_trade_pct = Vec::new();
        let mut sell_fraction = Vec::new();

        for pc in position_constraints {
            max_position_size_pct.push(pc.max_position_size_pct);
            min_trade_size_pct.push(pc.min_trade_size_pct);
            min_holding_candle.push(pc.min_holding_candle);
            trailing_stop_loss_pct.push(pc.trailing_stop_loss_pct);
            trailing_stop_update_threshold_pct.push(pc.trailing_stop_update_threshold_pct);
            take_profit_pct.push(pc.take_profit_pct);
            risk_per_trade_pct.push(pc.risk_per_trade_pct);
            sell_fraction.push(pc.sell_fraction);
        }

        Self {
            max_position_size_pct,
            min_trade_size_pct,
            min_holding_candle,
            trailing_stop_loss_pct,
            trailing_stop_update_threshold_pct,
            take_profit_pct,
            risk_per_trade_pct,
            sell_fraction,
            max_drawdown_pct: 0.0,
            rebalance_threshold_pct: 0.0,
            candle_time: 60,
        }
    }
    pub fn set_cadence(&mut self, candle_time: u64) {
        self.candle_time = candle_time;
    }

    pub fn calculate_max_pos_size_by_risk(
        &self,
        trades: &[i8],
        price: &[f32],
        portfolio_value: f32,
        holdings: &[f32],
    ) -> Vec<f32> {
        trades
            .iter()
            .enumerate()
            .map(|(i, trade)| {
                if *trade == -1 {
                    holdings[i] * self.sell_fraction[i]
                } else {
                    let risk_per_trade = price[i] * self.risk_per_trade_pct[i];
                    (self.max_position_size_pct[i] * portfolio_value) / risk_per_trade
                }
            })
            .collect()
    }

    pub fn pre_order_check(
        &self,
        price: &[f32],
        positions: &[Option<Position>],
        peak_portfolio_value: f32,
    ) -> (bool, Vec<Trade>) {
        let mut max_drawdown_trades = Vec::new();
        let mut stop_loss_trades = Vec::new();
        let mut new_market_value = 0.0;
        for (idx, position) in positions.iter().enumerate() {
            if let Some(position) = position {
                if price[idx] < position.trailing_stop_price {
                    stop_loss_trades.push(Trade::stop_loss(-position.quantity, idx));
                }
                new_market_value += position.quantity * price[idx];
                max_drawdown_trades.push(Trade::liquidation(-position.quantity, idx));
            }
        }
        if new_market_value < self.max_drawdown_pct * peak_portfolio_value {
            return (true, max_drawdown_trades);
        }
        (false, stop_loss_trades)
    }

    pub fn generate_trades(
        &mut self,
        signals: &[i8],
        price: &[f32],
        portfolio_value: f32,
        positions: &[Option<Position>],
    ) -> Vec<Trade> {
        let mut new_trades = Vec::new();
        for (idx, position) in positions.iter().enumerate() {
            if signals[idx] == 0 {
                continue;
            }
            if signals[idx] == 1 {
                let max_position_size_pct = self.max_position_size_pct.get(idx).unwrap_or(&0.0);
                let risk_per_trade_pct = self.risk_per_trade_pct.get(idx).unwrap_or(&0.0);
                let min_trade_size_pct = self.min_trade_size_pct.get(idx).unwrap_or(&0.0);

                let max_pos_size =
                    (max_position_size_pct * portfolio_value) / (risk_per_trade_pct * price[idx]);
                if max_pos_size * price[idx] > min_trade_size_pct * portfolio_value {
                    new_trades.push(Trade::signal_buy(max_pos_size, idx));
                }
            }
            if signals[idx] == -1 {
                if let Some(position) = position {
                    let sell_fraction = self.sell_fraction.get(idx).unwrap_or(&0.0);
                    new_trades.push(Trade::signal_sell(position.quantity * sell_fraction, idx));
                }
            }
        }
        new_trades
    }

    pub fn evaluate_trades(
        &self,
        trades: &[Trade],
        price: &[f32],
        portfolio_value: f32,
        timestamp: u64,
        positions: &[Option<Position>],
    ) -> Vec<Trade> {
        let mut actual_trades = Vec::new();
        let mut total_size = 0.0;
        for trade in trades {
            let notional = trade.quantity * price[trade.ticker_id as usize];

            if trade.is_signal_buy.unwrap_or(false) {
                let mut holding_period = 0;
                if let Some(position) = positions[trade.ticker_id as usize].clone() {
                    holding_period = (timestamp - position.entry_timestamp) / self.candle_time;
                };
                if holding_period == 0
                    || holding_period >= *self.min_holding_candle.get(trade.ticker_id).unwrap_or(&0)
                {
                    if notional
                        > self.min_trade_size_pct.get(trade.ticker_id).unwrap_or(&0.0)
                            * portfolio_value
                    {
                        total_size += notional;
                        actual_trades.push(trade.clone());
                    }
                }
            }
            if trade.is_signal_sell.unwrap_or(false) {
                total_size += notional;
                actual_trades.push(trade.clone());
            }
        }

        if total_size > self.rebalance_threshold_pct * portfolio_value {
            actual_trades
        } else {
            Vec::new()
        }
    }
}
