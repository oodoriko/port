use std::collections::HashMap;
use std::fmt;

// portfolio::constraint:
// trailing_stop_pct
// rebalance_threshold
// max_position_size_pct
// min_trade_size_pct
// min_holding_candle

// one coin per position
#[derive(Clone)]
pub struct Position {
    // initial attributes
    pub ticker: String,
    pub ticker_id: u32,
    pub quantity: f32,
    pub avg_entry_price: f32,
    pub entry_timestamp: u64, // earliest entry
    pub constraint: HashMap<String, f32>,
    pub peak_price: f32,
    pub trailing_stop_price: f32,
    pub take_profit_price: f32,

    // buy related attributes
    pub cum_buy_proceeds: f32,
    pub cum_buy_cost: f32, // transaction cost + slippage?
    pub unrealized_pnl: Option<f32>,
    pub last_entry_price: f32,
    pub last_entry_timestamp: u64,

    // sell related attributes
    pub cum_sell_proceeds: Option<f32>,
    pub cum_sell_cost: Option<f32>, // transaction cost + slippage?
    pub realized_pnl: Option<f32>,
    pub last_exit_price: Option<f32>,
    pub last_exit_timestamp: Option<u64>,

    // additional attributes
    pub notional: f32,
}

impl Position {
    pub fn new(
        ticker_id: u32,
        price: f32,
        quantity: Option<f32>,
        entry_timestamp: Option<u64>,
        ticker: Option<&str>,
        constraint: Option<HashMap<String, f32>>,
    ) -> Self {
        Self {
            ticker: ticker.unwrap_or("").to_string(),
            ticker_id,
            quantity: quantity.unwrap_or(0.0),
            avg_entry_price: price,
            entry_timestamp: entry_timestamp.unwrap_or(0),
            peak_price: price,
            trailing_stop_price: price,
            take_profit_price: f32::MAX,
            constraint: constraint.unwrap_or_default(),
            cum_buy_proceeds: 0.0,
            cum_buy_cost: 0.0,
            unrealized_pnl: None,
            last_entry_price: price,
            last_entry_timestamp: entry_timestamp.unwrap_or(0),
            cum_sell_proceeds: None,
            cum_sell_cost: None,
            realized_pnl: None,
            last_exit_price: None,
            last_exit_timestamp: None,
            notional: 0.0,
        }
    }

    fn update_trailing_stop_price(&mut self, price: f32) {
        if let Some(&trailing_stop_pct) = self.constraint.get("trailing_stop_pct") {
            self.trailing_stop_price = price * trailing_stop_pct;
        }
    }

    pub fn pre_order_update(&mut self, price: f32) {
        self.update_trailing_stop_price(price);
        self.notional = self.quantity * price;
        self.unrealized_pnl = Some((price - self.avg_entry_price) * self.quantity);
    }

    pub fn post_order_update(&mut self, price: f32) -> (f32, f32) {
        if price > self.last_entry_price {
            let new_stop = price * 0.95; // 5% trailing stop
            if new_stop > self.trailing_stop_price {
                self.trailing_stop_price = new_stop;
            }
        }
        self.notional = self.quantity * price;
        self.unrealized_pnl = Some((price - self.avg_entry_price) * self.quantity);
        return (self.notional, self.unrealized_pnl.unwrap_or(0.0));
    }

    pub fn update_buy_position(&mut self, price: f32, quantity: f32, timestamp: u64, cost: f32) {
        self.quantity += quantity;
        self.avg_entry_price =
            (self.avg_entry_price * self.quantity + price * quantity) / (self.quantity + quantity);
        self.last_entry_timestamp = timestamp;
        self.last_entry_price = price;
        self.cum_buy_proceeds += price * quantity;
        self.cum_buy_cost += cost;
    }

    pub fn update_sell_position(
        &mut self,
        price: f32,
        quantity: f32,
        timestamp: u64,
        cost: f32,
    ) -> f32 {
        self.cum_sell_proceeds = Some(self.cum_sell_proceeds.unwrap_or(0.0) + price * -quantity);
        self.cum_sell_cost = Some(self.cum_sell_cost.unwrap_or(0.0) + cost);
        self.realized_pnl = Some((price - self.avg_entry_price) * -quantity);
        self.last_exit_price = Some(price);
        self.last_exit_timestamp = Some(timestamp);
        self.quantity += quantity; // sell qty is negative
        return self.realized_pnl.unwrap_or(0.0);
    }
}

impl fmt::Debug for Position {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "Position {{ ticker: {}, ticker_id: {}, quantity: {:.4}, avg_entry_price: {:.2}, entry_timestamp: {}, peak_price: {:.2}, trailing_stop_price: {:.2}, cum_buy_proceeds: {:.2}, cum_buy_cost: {:.2}, unrealized_pnl: {:?}, last_entry_price: {:.2}, last_entry_timestamp: {}, cum_sell_proceeds: {:?}, cum_sell_cost: {:?}, realized_pnl: {:?}, last_exit_price: {:?}, last_exit_timestamp: {:?} }}",
            self.ticker,
            self.ticker_id,
            self.quantity,
            self.avg_entry_price,
            self.entry_timestamp,
            self.peak_price,
            self.trailing_stop_price,
            self.cum_buy_proceeds,
            self.cum_buy_cost,
            self.unrealized_pnl,
            self.last_entry_price,
            self.last_entry_timestamp,
            self.cum_sell_proceeds,
            self.cum_sell_cost,
            self.realized_pnl,
            self.last_exit_price,
            self.last_exit_timestamp
        )
    }
}
