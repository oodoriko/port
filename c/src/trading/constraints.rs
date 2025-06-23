use crate::core::params::{PortfolioConstraintParams, PositionConstraintParams};
use crate::trading::position::Position;
use crate::trading::trade::Trade;

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
    pub cool_down_period: Vec<u64>,
    // Cache for hot path calculations
    n_assets: usize,
}

impl Constraint {
    pub fn from_position_constraints(
        position_constraints: &[PositionConstraintParams],
        portfolio_constraints: PortfolioConstraintParams,
    ) -> Self {
        let n_assets = position_constraints.len();

        let mut max_position_size_pct = Vec::with_capacity(n_assets);
        let mut min_trade_size_pct = Vec::with_capacity(n_assets);
        let mut min_holding_candle = Vec::with_capacity(n_assets);
        let mut trailing_stop_loss_pct = Vec::with_capacity(n_assets);
        let mut trailing_stop_update_threshold_pct = Vec::with_capacity(n_assets);
        let mut take_profit_pct = Vec::with_capacity(n_assets);
        let mut risk_per_trade_pct = Vec::with_capacity(n_assets);
        let mut sell_fraction = Vec::with_capacity(n_assets);
        let mut cool_down_period = Vec::with_capacity(n_assets);

        for pc in position_constraints {
            max_position_size_pct.push(pc.max_position_size_pct);
            min_trade_size_pct.push(pc.min_trade_size_pct);
            min_holding_candle.push(pc.min_holding_candle);
            trailing_stop_loss_pct.push(pc.trailing_stop_loss_pct);
            trailing_stop_update_threshold_pct.push(pc.trailing_stop_update_threshold_pct);
            take_profit_pct.push(pc.take_profit_pct);
            risk_per_trade_pct.push(pc.risk_per_trade_pct);
            sell_fraction.push(pc.sell_fraction);
            cool_down_period.push(pc.cool_down_period);
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
            max_drawdown_pct: portfolio_constraints.max_drawdown_pct,
            rebalance_threshold_pct: portfolio_constraints.rebalance_threshold_pct,
            candle_time: 0,
            n_assets,
            cool_down_period,
        }
    }

    #[inline(always)]
    pub fn set_cadence(&mut self, candle_time: u64) {
        self.candle_time = candle_time;
    }

    #[inline(always)]
    pub fn calculate_max_pos_size_by_risk(
        &self,
        trades: &[i8],
        price: &[f32],
        portfolio_value: f32,
        holdings: &[f32],
    ) -> Vec<f32> {
        let len = trades.len().min(self.n_assets);
        let mut result = Vec::with_capacity(len);

        for i in 0..len {
            let trade_signal = unsafe { *trades.get_unchecked(i) };
            let result_value = if trade_signal == -1 {
                unsafe { *holdings.get_unchecked(i) * *self.sell_fraction.get_unchecked(i) }
            } else {
                unsafe {
                    let price_val = *price.get_unchecked(i);
                    let risk_per_trade = price_val * *self.risk_per_trade_pct.get_unchecked(i);
                    (*self.max_position_size_pct.get_unchecked(i) * portfolio_value)
                        / risk_per_trade
                }
            };
            result.push(result_value);
        }
        result
    }

    #[inline(always)]
    pub fn pre_order_check(
        &self,
        price: &[f32],
        positions: &[Option<Position>],
        peak_portfolio_value: f32,
        current_cash: f32,
        timestamp: u64,
    ) -> (bool, Vec<Trade>, Vec<Trade>) {
        let mut stop_loss_trades = Vec::with_capacity(self.n_assets);
        let mut take_profit_trades = Vec::with_capacity(self.n_assets);
        let mut new_market_value = 0.0;

        for (idx, position) in positions.iter().enumerate().take(self.n_assets) {
            if let Some(position) = position {
                if position.quantity <= 0.0 {
                    continue;
                }

                let current_price = unsafe { *price.get_unchecked(idx) };
                if current_price < position.trailing_stop_price {
                    stop_loss_trades.push(Trade::stop_loss(position.quantity, idx, timestamp));
                }

                if current_price > position.avg_entry_price * (1.0 + self.take_profit_pct[idx]) {
                    take_profit_trades.push(Trade::take_profit(position.quantity, idx, timestamp));
                }

                let position_value = position.quantity * current_price;
                new_market_value += position_value;
            }
        }

        if new_market_value != 0.0
            && (peak_portfolio_value - new_market_value - current_cash) / peak_portfolio_value
                > self.max_drawdown_pct
        {
            let mut max_drawdown_trades = Vec::with_capacity(self.n_assets);
            for (idx, position) in positions.iter().enumerate().take(self.n_assets) {
                if let Some(position) = position {
                    if position.quantity <= 0.0 {
                        continue;
                    }
                    max_drawdown_trades.push(Trade::liquidation(position.quantity, idx, timestamp));
                }
            }
            (true, max_drawdown_trades, take_profit_trades)
        } else {
            (false, stop_loss_trades, take_profit_trades)
        }
    }

    #[inline(always)]
    pub fn generate_trades(
        &mut self,
        signals: &[i8],
        price: &[f32],
        portfolio_value: f32,
        available_cash: f32,
        timestamp: u64,
        positions: &[Option<Position>],
    ) -> Vec<Trade> {
        let mut valid_trades = Vec::with_capacity(self.n_assets / 2);
        let mut total_size = 0.0;

        let rebalance_threshold = self.rebalance_threshold_pct * portfolio_value;
        let min_available = available_cash.min(portfolio_value);
        let signal_len = signals.len().min(positions.len()).min(self.n_assets);

        for idx in 0..signal_len {
            let signal = unsafe { *signals.get_unchecked(idx) };
            let position = unsafe { positions.get_unchecked(idx) };

            match signal {
                0 => continue,
                1 => {
                    if let Some(pos) = position {
                        let holding_period = (timestamp - pos.entry_timestamp) / self.candle_time;
                        let min_holding = unsafe { *self.min_holding_candle.get_unchecked(idx) };
                        if holding_period < min_holding {
                            continue;
                        }
                        let cool_down_period = unsafe { *self.cool_down_period.get_unchecked(idx) };
                        if cool_down_period > 0 {
                            let holding_period =
                                (timestamp - pos.last_exit_timestamp) / self.candle_time;
                            if holding_period < cool_down_period && pos.last_exit_pnl < 0.0 {
                                continue;
                            }
                        }
                    }
                    let current_price = unsafe { *price.get_unchecked(idx) };
                    let risk_per_trade_pct = unsafe { *self.risk_per_trade_pct.get_unchecked(idx) };
                    let trailing_stop_pct =
                        unsafe { *self.trailing_stop_loss_pct.get_unchecked(idx) };
                    let max_pos_pct = unsafe { *self.max_position_size_pct.get_unchecked(idx) };
                    let min_trade_pct = unsafe { *self.min_trade_size_pct.get_unchecked(idx) };

                    let risk_denominator = trailing_stop_pct * current_price;

                    let risk_based_size = (risk_per_trade_pct * min_available) / risk_denominator;
                    let max_allowed_size = (max_pos_pct * portfolio_value) / current_price;
                    let max_pos_size = (risk_based_size.min(max_allowed_size) * 1e6).round() / 1e6; // prevent overflow

                    let min_trade_threshold = min_trade_pct * portfolio_value;
                    let trade_value = max_pos_size * current_price;
                    if trade_value > min_trade_threshold {
                        total_size += trade_value;
                        valid_trades.push(Trade::signal_buy(max_pos_size, idx, timestamp));
                    }
                }
                -1 => {
                    if let Some(pos) = position {
                        if pos.quantity <= 0.0 {
                            continue;
                        }
                        let sell_fraction = unsafe { *self.sell_fraction.get_unchecked(idx) };
                        let current_price = unsafe { *price.get_unchecked(idx) };

                        let quantity = (pos.quantity * sell_fraction * 1e6).round() / 1e6; // prevent overflow
                        let trade_value = quantity * current_price;

                        total_size -= trade_value;
                        valid_trades.push(Trade::signal_sell(quantity, idx, timestamp));
                    }
                }
                _ => {}
            }
        }

        if total_size > rebalance_threshold {
            valid_trades
        } else {
            Vec::new()
        }
    }
}
