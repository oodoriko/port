#[derive(Debug, Clone, Copy, PartialEq)]
pub enum TradeType {
    SignalBuy,
    SignalSell,
    StopLoss,
    Liquidation,
    TakeProfit,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum TradeStatus {
    Pending,
    Executed,
    Failed,
    Rejected,
}

#[derive(Debug, Clone)]
pub struct Trade {
    pub ticker_id: usize,
    pub quantity: f32,
    pub trade_type: TradeType,
    pub trade_status: TradeStatus,

    pub generated_at: u64,
    pub execution_timestamp: u64, // 0 if not executed
    pub price: f32,               // 0.0 if not executed
    pub cost: f32,                // 0.0 if not calculated
    pub pro_rata_buy_cost: f32,   // 0.0 if not applicable

    pub avg_entry_price: f32,    // 0.0 if not applicable
    pub holding_period: u64,     // 0 if not applicable
    pub realized_pnl_gross: f32, // 0.0 if not applicable
    pub realized_return: f32,    // 0.0 if not applicable

    pub trade_comment: Option<String>,
}
impl Trade {
    #[inline(always)]
    pub fn signal_buy(quantity: f32, ticker_id: usize, generated_at: u64) -> Self {
        Self {
            ticker_id,
            quantity,
            trade_type: TradeType::SignalBuy,
            trade_status: TradeStatus::Pending,
            generated_at,
            execution_timestamp: 0,
            price: 0.0,
            cost: 0.0,
            pro_rata_buy_cost: 0.0,
            avg_entry_price: 0.0,
            holding_period: 0,
            realized_pnl_gross: 0.0,
            realized_return: 0.0,
            trade_comment: None,
        }
    }

    #[inline(always)]
    pub fn take_profit(quantity: f32, ticker_id: usize, generated_at: u64) -> Self {
        Self {
            ticker_id,
            quantity,
            trade_type: TradeType::TakeProfit,
            trade_status: TradeStatus::Pending,
            generated_at,
            execution_timestamp: 0,
            price: 0.0,
            cost: 0.0,
            pro_rata_buy_cost: 0.0,
            avg_entry_price: 0.0,
            holding_period: 0,
            realized_pnl_gross: 0.0,
            realized_return: 0.0,
            trade_comment: None,
        }
    }

    #[inline(always)]
    pub fn signal_sell(quantity: f32, ticker_id: usize, generated_at: u64) -> Self {
        Self {
            ticker_id,
            quantity,
            trade_type: TradeType::SignalSell,
            trade_status: TradeStatus::Pending,
            generated_at,
            execution_timestamp: 0,
            price: 0.0,
            cost: 0.0,
            pro_rata_buy_cost: 0.0,
            avg_entry_price: 0.0,
            holding_period: 0,
            realized_pnl_gross: 0.0,
            realized_return: 0.0,
            trade_comment: None,
        }
    }

    #[inline(always)]
    pub fn stop_loss(quantity: f32, ticker_id: usize, generated_at: u64) -> Self {
        Self {
            ticker_id,
            quantity,
            trade_type: TradeType::StopLoss,
            trade_status: TradeStatus::Pending,
            generated_at,
            execution_timestamp: 0,
            price: 0.0,
            cost: 0.0,
            pro_rata_buy_cost: 0.0,
            avg_entry_price: 0.0,
            holding_period: 0,
            realized_pnl_gross: 0.0,
            realized_return: 0.0,
            trade_comment: None,
        }
    }

    #[inline(always)]
    pub fn liquidation(quantity: f32, ticker_id: usize, generated_at: u64) -> Self {
        Self {
            ticker_id,
            quantity,
            trade_type: TradeType::Liquidation,
            trade_status: TradeStatus::Pending,
            generated_at,
            execution_timestamp: 0,
            price: 0.0,
            cost: 0.0,
            pro_rata_buy_cost: 0.0,
            avg_entry_price: 0.0,
            holding_period: 0,
            realized_pnl_gross: 0.0,
            realized_return: 0.0,
            trade_comment: None,
        }
    }

    #[inline(always)]
    pub fn update_buy_trade(&mut self, price: f32, timestamp: u64, cost: f32, quantity: f32) {
        self.quantity = quantity;
        self.price = price;
        self.execution_timestamp = timestamp;
        self.cost = cost;
        self.trade_status = TradeStatus::Executed;
    }

    #[inline(always)]
    pub fn update_sell_trade(
        &mut self,
        price: f32,
        timestamp: u64,
        cost: f32,
        pro_rata_buy_cost: f32,
        avg_entry_price: f32,
        entry_timestamp: u64,
    ) {
        self.price = price;
        self.execution_timestamp = timestamp;
        self.cost = cost;
        self.pro_rata_buy_cost = pro_rata_buy_cost;
        self.holding_period = timestamp - entry_timestamp;
        self.avg_entry_price = avg_entry_price;
        self.realized_pnl_gross = (price - avg_entry_price) * self.quantity;
        self.trade_status = TradeStatus::Executed;
        self.realized_return =
            ((price - cost) * self.quantity - pro_rata_buy_cost) / avg_entry_price * self.quantity
                - 1.0;
    }

    #[inline(always)]
    pub fn update_trade_status(&mut self, status: TradeStatus) {
        self.trade_status = status;
    }

    #[inline(always)]
    pub fn set_comment(&mut self, comment: String) {
        self.trade_comment = Some(comment);
    }

    #[inline(always)]
    pub fn clear_comment(&mut self) {
        self.trade_comment = None;
    }

    #[inline(always)]
    pub fn is_buy(&self) -> bool {
        matches!(self.trade_type, TradeType::SignalBuy)
    }

    #[inline(always)]
    pub fn is_sell(&self) -> bool {
        matches!(self.trade_type, TradeType::SignalSell)
    }

    #[inline(always)]
    pub fn is_stop_loss(&self) -> bool {
        matches!(self.trade_type, TradeType::StopLoss)
    }

    #[inline(always)]
    pub fn is_liquidation(&self) -> bool {
        matches!(self.trade_type, TradeType::Liquidation)
    }

    #[inline(always)]
    pub fn is_executed(&self) -> bool {
        matches!(self.trade_status, TradeStatus::Executed)
    }

    #[inline(always)]
    pub fn is_pending(&self) -> bool {
        matches!(self.trade_status, TradeStatus::Pending)
    }

    #[inline(always)]
    pub fn is_take_profit(&self) -> bool {
        matches!(self.trade_type, TradeType::TakeProfit)
    }
}
