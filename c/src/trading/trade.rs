// a record of a single trade, mostly for reporting purposes
#[derive(Debug, Clone)]
pub struct Trade {
    pub ticker_id: usize,
    pub quantity: f32, // + for buy, - for sell

    pub cost: Option<f32>, // transaction cost + slippage?
    pub execution_timestamp: Option<u64>,
    pub price: Option<f32>, // when trade is created, price is not available, filled at execution

    // sell trade, most need to reference to Position during execution
    pub avg_entry_price: Option<f32>,
    pub holding_period: Option<u64>, // only if position is closed
    pub realized_pnl: Option<f32>,

    pub is_stop_loss: Option<bool>,
    pub is_liquidation: Option<bool>,
    pub is_signal_sell: Option<bool>,
    pub is_signal_buy: Option<bool>,

    pub trade_status: Option<String>,
    pub trade_comment: Option<String>,
}

impl Trade {
    pub fn new(quantity: f32, ticker_id: usize) -> Self {
        Self {
            ticker_id,
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

    pub fn signal_buy(quantity: f32, ticker_id: usize) -> Self {
        let mut trade = Self::new(quantity, ticker_id);
        trade.is_signal_buy = Some(true);
        trade
    }

    pub fn signal_sell(quantity: f32, ticker_id: usize) -> Self {
        let mut trade = Self::new(quantity, ticker_id);
        trade.is_signal_sell = Some(true);
        trade
    }

    pub fn stop_loss(quantity: f32, ticker_id: usize) -> Self {
        let mut trade = Self::new(quantity, ticker_id);
        trade.is_stop_loss = Some(true);
        trade
    }

    pub fn liquidation(quantity: f32, ticker_id: usize) -> Self {
        let mut trade = Self::new(quantity, ticker_id);
        trade.is_liquidation = Some(true);
        trade
    }

    pub fn update_buy_trade(&mut self, price: f32, timestamp: u64, cost: f32) {
        self.price = Some(price);
        self.execution_timestamp = Some(timestamp);
        self.cost = Some(cost);
        self.trade_status = Some("Executed".to_string());
        self.trade_comment = Some("".to_string());
    }

    pub fn update_sell_trade(
        &mut self,
        price: f32,
        timestamp: u64,
        cost: f32,
        avg_entry_price: f32,
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
    }
    pub fn update_trade_status(&mut self, status: String, comment: String) {
        self.trade_status = Some(status);
        self.trade_comment = Some(comment);
    }
}
