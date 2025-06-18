use crate::trade::Trade;
use crate::utils::ticker_to_id;
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
    pub id: usize,
    pub quantity: f64,
    pub avg_entry_price: f64,
    pub entry_timestamp: u64, // earliest entry
    pub constraint: HashMap<String, f64>,
    pub peak_price: f64,
    pub trailing_stop_price: f64,

    // buy related attributes
    pub cum_buy_proceeds: f64,
    pub cum_buy_cost: f64, // transaction cost + slippage?
    pub unrealized_pnl: Option<f64>,
    pub last_entry_price: f64,
    pub last_entry_timestamp: u64,

    // sell related attributes
    pub cum_sell_proceeds: Option<f64>,
    pub cum_sell_cost: Option<f64>, // transaction cost + slippage?
    pub realized_pnl: Option<f64>,
    pub last_exit_price: Option<f64>,
    pub last_exit_timestamp: Option<u64>,
}

impl Position {
    pub fn new(
        ticker: &str,
        quantity: f64,
        avg_entry_price: f64,
        cost: f64,
        entry_timestamp: u64,
        constraint: HashMap<String, f64>,
    ) -> Self {
        Self {
            ticker: ticker.to_string(),
            quantity: quantity,
            avg_entry_price: avg_entry_price,
            entry_timestamp: entry_timestamp,
            peak_price: avg_entry_price,
            trailing_stop_price: avg_entry_price
                * (1.0 - constraint.get("trailing_stop_pct").unwrap_or(&0.0).clone()),
            constraint: constraint,
            cum_buy_proceeds: avg_entry_price * quantity,
            cum_buy_cost: cost,
            unrealized_pnl: None,
            last_entry_price: avg_entry_price,
            last_entry_timestamp: entry_timestamp,
            cum_sell_proceeds: None,
            cum_sell_cost: None,
            realized_pnl: None,
            last_exit_price: None,
            last_exit_timestamp: None,
            id: ticker_to_id(ticker).unwrap_or(10),
        }
    }

    fn update_trailing_stop_price(&mut self, price: f64) {
        if let Some(&trailing_stop_pct) = self.constraint.get("trailing_stop_pct") {
            self.trailing_stop_price = price * trailing_stop_pct;
        }
    }

    fn check_stop_loss(&mut self, price: f64) -> Option<Trade> {
        if price < self.trailing_stop_price {
            let trade = Trade::new(&self.ticker, -self.quantity);
            return Some(trade);
        } else {
            return None;
        }
    }

    pub fn pre_order_update(&mut self, price: f64) -> Option<Trade> {
        self.peak_price = price.max(self.peak_price);
        self.update_trailing_stop_price(price);
        let sl_trades = self.check_stop_loss(price);
        sl_trades
    }

    pub fn post_order_update(&mut self, price: f64) -> (f64, f64) {
        self.unrealized_pnl = Some((price - self.avg_entry_price) * self.quantity);
        return (price * self.quantity, self.unrealized_pnl.unwrap_or(0.0));
    }

    pub fn update_buy_position(&mut self, price: f64, quantity: f64, timestamp: u64, cost: f64) {
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
        price: f64,
        quantity: f64,
        timestamp: u64,
        cost: f64,
    ) -> f64 {
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
            "Position {{ ticker: {}, id: {}, quantity: {:.4}, avg_entry_price: {:.2}, entry_timestamp: {}, peak_price: {:.2}, trailing_stop_price: {:.2}, cum_buy_proceeds: {:.2}, cum_buy_cost: {:.2}, unrealized_pnl: {:?}, last_entry_price: {:.2}, last_entry_timestamp: {}, cum_sell_proceeds: {:?}, cum_sell_cost: {:?}, realized_pnl: {:?}, last_exit_price: {:?}, last_exit_timestamp: {:?} }}",
            self.ticker,
            self.id,
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
