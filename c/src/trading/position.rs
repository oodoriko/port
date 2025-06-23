use crate::{core::params::PositionConstraintParams, trading::trade::TradeType};
use std::fmt;

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum PositionStatus {
    Open,
    Closed,
}

// one coin per position
#[derive(Clone)]
pub struct Position {
    pub ticker_id: u32,
    pub quantity: f32,
    pub avg_entry_price: f32,
    pub entry_timestamp: u64,
    pub notional: f32,

    pub peak_price: f32,
    pub trailing_stop_price: f32,
    pub take_profit_price: f32,
    pub unrealized_pnl: f32,

    pub cum_buy_proceeds: f32,
    pub cum_buy_cost: f32,
    pub last_entry_price: f32,
    pub last_entry_timestamp: u64,

    pub cum_sell_proceeds: f32,
    pub cum_sell_cost: f32,
    pub realized_pnl_gross: f32,
    pub last_exit_price: f32,
    pub last_exit_timestamp: u64,
    pub last_exit_pnl: f32,

    // more for backtesting
    pub total_shares_bought: f32,
    pub total_shares_sold: f32,
    pub net_position: Vec<f32>,

    pub take_profit_gain: f32,
    pub take_profit_loss: f32,
    pub stop_loss_gain: f32,
    pub stop_loss_loss: f32,
    pub signal_sell_gain: f32,
    pub signal_sell_loss: f32,

    pub constraint: Option<PositionConstraintParams>,
    pub position_status: PositionStatus,
}

impl Position {
    #[inline(always)]
    pub fn new(
        ticker_id: u32,
        price: f32,
        quantity: Option<f32>,
        entry_timestamp: Option<u64>,
        constraint: Option<PositionConstraintParams>,
    ) -> Self {
        let qty = quantity.unwrap_or(0.0);
        let timestamp = entry_timestamp.unwrap_or(0);

        let trailing_stop_price = if let Some(ref constraint) = constraint {
            price * (1.0 - constraint.trailing_stop_loss_pct)
        } else {
            price * 0.95
        };

        Self {
            ticker_id,
            quantity: qty,
            avg_entry_price: price,
            entry_timestamp: timestamp,
            notional: qty * price,
            peak_price: price,
            trailing_stop_price,
            take_profit_price: f32::MAX,
            unrealized_pnl: 0.0,
            cum_buy_proceeds: 0.0,
            cum_buy_cost: 0.0,
            last_entry_price: price,
            last_entry_timestamp: timestamp,
            cum_sell_proceeds: 0.0,
            cum_sell_cost: 0.0,
            realized_pnl_gross: 0.0,
            last_exit_price: 0.0,
            last_exit_timestamp: 0,
            last_exit_pnl: 0.0,
            take_profit_gain: 0.0,
            take_profit_loss: 0.0,
            stop_loss_gain: 0.0,
            stop_loss_loss: 0.0,
            signal_sell_gain: 0.0,
            signal_sell_loss: 0.0,
            constraint,
            position_status: PositionStatus::Open,
            total_shares_bought: 0.0,
            total_shares_sold: 0.0,
            net_position: vec![0.0],
        }
    }

    #[inline(always)]
    fn update_trailing_stop_price(&mut self, price: f32) {
        if let Some(constraint) = &self.constraint {
            let trailing_stop_pct = constraint.trailing_stop_loss_pct;
            let trailing_stop_update_threshold_pct = constraint.trailing_stop_update_threshold_pct;

            let threshold_price = self.peak_price * (1.0 + trailing_stop_update_threshold_pct);
            if price > threshold_price {
                self.trailing_stop_price = price * (1.0 - trailing_stop_pct);
            }
        }
    }

    #[inline(always)]
    pub fn pre_order_update(&mut self, price: f32) {
        if price > self.peak_price {
            self.peak_price = price;
            self.update_trailing_stop_price(price);
        }
    }

    #[inline(always)]
    pub fn post_order_update(&mut self, price: f32) -> (f32, f32) {
        self.notional = self.quantity * price;
        self.unrealized_pnl += (price - self.avg_entry_price) * self.quantity;
        (self.notional, self.unrealized_pnl)
    }

    #[inline(always)]
    pub fn update_buy_position(&mut self, price: f32, quantity: f32, timestamp: u64, cost: f32) {
        let old_quantity = self.quantity;
        let new_quantity = old_quantity + quantity;

        self.quantity = new_quantity;

        self.avg_entry_price =
            (self.avg_entry_price * old_quantity + price * quantity) / new_quantity;
        self.last_entry_timestamp = timestamp;
        self.last_entry_price = price;
        self.cum_buy_proceeds += price * quantity;
        self.cum_buy_cost += cost;
        self.total_shares_bought += quantity;
        self.net_position.push(self.quantity);

        self.notional = new_quantity * price;
    }

    #[inline(always)]
    pub fn update_sell_position(
        &mut self,
        price: f32,
        quantity: f32,
        timestamp: u64,
        cost: f32,
        trade_type: TradeType,
    ) -> f32 {
        let pnl = (price - self.avg_entry_price) * quantity - cost;
        let sell_proceeds = price * quantity;

        self.cum_sell_proceeds += sell_proceeds;
        self.cum_sell_cost += cost;
        self.realized_pnl_gross += pnl + cost;
        self.last_exit_price = price;
        self.last_exit_timestamp = timestamp;
        self.quantity = (self.quantity - quantity).max(0.0);
        self.last_exit_pnl = pnl;
        self.notional = self.quantity * price;
        self.total_shares_sold += quantity;
        self.net_position.push(self.quantity);
        if self.quantity < 0.000001 {
            self.position_status = PositionStatus::Closed;
        }

        if pnl > 0.0 {
            if trade_type == TradeType::TakeProfit {
                self.take_profit_gain += pnl;
            } else if trade_type == TradeType::StopLoss {
                self.stop_loss_gain += pnl;
            } else if trade_type == TradeType::SignalSell {
                self.signal_sell_gain += pnl;
            }
        } else {
            if trade_type == TradeType::TakeProfit {
                self.take_profit_loss += pnl;
            } else if trade_type == TradeType::StopLoss {
                self.stop_loss_loss += pnl;
            } else if trade_type == TradeType::SignalSell {
                self.signal_sell_loss += pnl;
            }
        }

        pnl
    }

    #[inline(always)]
    pub fn has_position(&self) -> bool {
        self.quantity > 0.0
    }

    #[inline(always)]
    pub fn has_sold(&self) -> bool {
        self.last_exit_timestamp > 0
    }

    #[inline(always)]
    pub fn is_profitable(&self, current_price: f32) -> bool {
        current_price > self.avg_entry_price
    }

    #[inline(always)]
    pub fn get_current_value(&self, current_price: f32) -> f32 {
        self.quantity * current_price
    }

    #[inline(always)]
    pub fn get_unrealized_pnl(&self, current_price: f32) -> f32 {
        (current_price - self.avg_entry_price) * self.quantity
    }

    #[inline(always)]
    pub fn should_stop_loss(&self, current_price: f32) -> bool {
        self.quantity > 0.0 && current_price < self.trailing_stop_price
    }

    #[inline(always)]
    pub fn should_take_profit(&self, current_price: f32) -> bool {
        self.quantity > 0.0 && current_price >= self.take_profit_price
    }
}

impl fmt::Debug for Position {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "Position {{ id: {}, qty: {:.4}, entry: {:.2}@{}, pnl: {:.2}, notional: {:.2} }}",
            self.ticker_id,
            self.quantity,
            self.avg_entry_price,
            self.entry_timestamp,
            self.unrealized_pnl,
            self.notional
        )
    }
}
