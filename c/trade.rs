use crate::utils::ticker_to_id;

// a record of a single trade, mostly for reporting purposes
#[derive(Debug)]
pub struct Trade {
    pub ticker: String,
    pub ticker_id: usize,
    pub quantity: f64, // + for buy, - for sell

    pub cost: Option<f64>, // transaction cost + slippage?
    pub execution_timestamp: Option<u64>,
    pub price: Option<f64>, // when trade is created, price is not available, filled at execution

    // sell trade, most need to reference to Position during execution
    pub avg_entry_price: Option<f64>,
    pub holding_period: Option<u64>, // only if position is closed
    pub realized_pnl: Option<f64>,

    pub is_stop_loss: Option<bool>,
    pub is_liquidation: Option<bool>,
    pub is_signal_sell: Option<bool>,
    pub is_signal_buy: Option<bool>,

    pub trade_status: Option<String>,
    pub trade_comment: Option<String>,
}

impl Trade {
    pub fn new(ticker: &str, quantity: f64) -> Self {
        Self {
            ticker: ticker.to_string(),
            ticker_id: ticker_to_id(ticker).unwrap_or(10),
            quantity,
            cost: None,
            execution_timestamp: None,
            price: None,
            avg_entry_price: None,
            holding_period: None,
            realized_pnl: None,
            is_stop_loss: Some(false),
            is_liquidation: Some(false),
            is_signal_sell: Some(false),
            is_signal_buy: Some(false),
            trade_status: Some("Pending".to_string()),
            trade_comment: Some("".to_string()),
        }
    }

    pub fn update_buy_trade(&mut self, price: f64, timestamp: u64, cost: f64) {
        self.price = Some(price);
        self.execution_timestamp = Some(timestamp);
        self.cost = Some(cost);
        self.trade_status = Some("Executed".to_string());
        self.trade_comment = Some("".to_string());
        self.is_signal_buy = Some(true);
    }

    pub fn update_sell_trade(
        &mut self,
        price: f64,
        timestamp: u64,
        cost: f64,
        sell_type: String,
        avg_entry_price: f64,
        entry_timestamp: u64,
    ) {
        self.price = Some(price);
        self.execution_timestamp = Some(timestamp);
        self.cost = Some(cost);
        self.holding_period = Some(timestamp - entry_timestamp);
        self.avg_entry_price = Some(avg_entry_price);
        self.realized_pnl = Some((price - avg_entry_price) * -self.quantity);

        self.trade_status = Some("Executed".to_string());
        self.trade_comment = Some("".to_string());
        self.is_signal_sell = Some(sell_type == "signal_sell");
        self.is_liquidation = Some(sell_type == "liquidation");
        self.is_stop_loss = Some(sell_type == "stop_loss");
    }

    pub fn update_trade_status(&mut self, status: String, comment: String) {
        self.trade_status = Some(status);
        self.trade_comment = Some(comment);
    }
}
