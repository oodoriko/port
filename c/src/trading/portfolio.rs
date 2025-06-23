use crate::core::params::{
    Frequency, PortfolioConstraintParams, PortfolioParams, PositionConstraintParams,
};
use crate::trading::position::Position;
use crate::trading::trade::{Trade, TradeStatus};
use crate::utils::utils::{is_end_of_period, timestamp_to_datetime};
use chrono::Datelike;

#[derive(Debug)]
pub struct Portfolio {
    pub name: String,
    pub positions: Vec<Option<Position>>, // indexed by ticker_id
    pub holdings: Vec<f32>,               // indexed by ticker_id, just the total shares
    pub equity_curve: Vec<f32>,
    pub cash_curve: Vec<f32>,
    pub notional_curve: Vec<f32>,
    pub cost_curve: Vec<f32>,
    pub realized_pnl_curve: Vec<f32>,
    pub unrealized_pnl_curve: Vec<f32>,
    pub portfolio_params: PortfolioParams,
    pub portfolio_constraints: PortfolioConstraintParams,
    pub position_constraints: Vec<PositionConstraintParams>,
    pub pending_trades: Vec<Trade>,
    pub peak_equity: f32,
    pub num_assets: usize,
    commission_rate: f32,
    last_cash_distribution_period: Option<i64>, // Track the period when last cash distribution occurred
}

impl Portfolio {
    pub fn new(
        name: String,
        num_assets: usize,
        portfolio_params: PortfolioParams,
        portfolio_constraints: PortfolioConstraintParams,
        position_constraints: Vec<PositionConstraintParams>,
    ) -> Self {
        let initial_cash = portfolio_params.initial_cash;

        let pending_trades = Vec::new();

        Self {
            name,
            portfolio_params,
            portfolio_constraints,
            position_constraints,
            positions: vec![None; num_assets],
            holdings: vec![0.0; num_assets],
            equity_curve: vec![initial_cash],
            cash_curve: vec![initial_cash],
            notional_curve: vec![0.0],
            cost_curve: vec![0.0],
            realized_pnl_curve: vec![0.0],
            unrealized_pnl_curve: vec![0.0],
            pending_trades,
            peak_equity: initial_cash,
            num_assets,
            commission_rate: 0.001,
            last_cash_distribution_period: None,
        }
    }

    #[inline(always)]
    pub fn pre_order_update(&mut self, close_prices: &[f32]) {
        for idx in 0..self.num_assets.min(close_prices.len()) {
            if let Some(pos) = &mut self.positions[idx] {
                let close_price = unsafe { *close_prices.get_unchecked(idx) };
                pos.pre_order_update(close_price);
            }
        }
    }

    #[inline(always)]
    pub fn post_order_update(
        &mut self,
        prices: &[f32],
        available_cash: f32,
        total_cost: f32,
        total_realized_pnl: f32,
    ) {
        self.cash_curve.push(available_cash);
        self.cost_curve.push(total_cost);
        self.realized_pnl_curve.push(total_realized_pnl);

        let mut total_notional = 0.0;
        let mut total_unrealized_pnl = 0.0;

        for idx in 0..self.num_assets.min(prices.len()) {
            if let Some(pos) = &mut self.positions[idx] {
                let price = unsafe { *prices.get_unchecked(idx) };
                let (notional, unrealized_pnl) = pos.post_order_update(price);
                total_notional += notional;
                total_unrealized_pnl += unrealized_pnl;
                unsafe {
                    *self.holdings.get_unchecked_mut(idx) = pos.quantity;
                }
            } else {
                // Clear holdings for positions that no longer exist
                unsafe {
                    *self.holdings.get_unchecked_mut(idx) = 0.0;
                }
            }
        }

        let last_cash = available_cash;
        let total_equity = total_notional + last_cash;
        self.equity_curve.push(total_equity);
        self.notional_curve.push(total_notional);
        self.unrealized_pnl_curve.push(total_unrealized_pnl);
        self.peak_equity = self.peak_equity.max(total_equity);
    }

    #[inline(always)]
    pub fn execute_trades(
        &mut self,
        trades: &mut [Trade],
        prices: &[f32],
        timestamp: u64,
        no_trades_asset_ids: &[usize],
    ) -> (f32, f32, f32, Vec<Trade>) {
        let available_cash =
            self.get_current_cash() * (1.0 - self.portfolio_constraints.min_cash_pct);
        let mut total_cost = 0.0;
        let mut total_realized_pnl = 0.0;
        let mut executed_trades = Vec::new();
        let mut net_cash = 0.0;
        for trade in trades.iter_mut() {
            let ticker_id = trade.ticker_id;
            if no_trades_asset_ids.contains(&ticker_id) {
                continue;
            }
            if ticker_id >= self.num_assets || ticker_id >= prices.len() {
                trade.update_trade_status(TradeStatus::Failed);
                trade.set_comment("Invalid ticker ID".to_string());
                continue;
            }

            let price = unsafe { *prices.get_unchecked(ticker_id) };
            let initial_cost = trade.quantity * price * self.commission_rate;

            match &mut self.positions[ticker_id] {
                Some(position) => {
                    if trade.is_buy() {
                        let requested_quantity = trade.quantity;
                        let max_affordable_quantity =
                            (available_cash - initial_cost).max(0.0) / price;

                        trade.quantity =
                            (requested_quantity.min(max_affordable_quantity) * 1e6).round() / 1e6;
                        let actual_cost = trade.quantity * price * self.commission_rate;

                        if trade.quantity > 0.0 {
                            position.update_buy_position(
                                price,
                                trade.quantity,
                                timestamp,
                                actual_cost,
                            );
                            net_cash -= trade.quantity * price + actual_cost;
                            total_cost += actual_cost;
                            trade.update_buy_trade(price, timestamp, actual_cost, trade.quantity);
                            executed_trades.push(trade.clone());
                        } else {
                            trade.update_trade_status(TradeStatus::Failed);
                            trade.set_comment("Insufficient cash".to_string());
                        }
                    } else {
                        let realized_pnl = position.update_sell_position(
                            price,
                            trade.quantity,
                            timestamp,
                            initial_cost,
                            trade.trade_type,
                        );
                        let pro_rata_buy_cost =
                            position.cum_buy_cost * trade.quantity / position.total_shares_bought;
                        trade.update_sell_trade(
                            price,
                            timestamp,
                            initial_cost,
                            pro_rata_buy_cost,
                            position.avg_entry_price,
                            position.last_entry_timestamp,
                        );

                        total_realized_pnl += realized_pnl;
                        net_cash += trade.quantity * price - initial_cost;
                        total_cost += initial_cost;

                        executed_trades.push(trade.clone());
                    }
                }
                None => {
                    if trade.is_buy() {
                        let requested_quantity = trade.quantity;
                        let max_affordable_quantity =
                            (available_cash - initial_cost).max(0.0) / price;

                        trade.quantity =
                            (requested_quantity.min(max_affordable_quantity) * 1e6).round() / 1e6;
                        let actual_cost = trade.quantity * price * self.commission_rate;

                        if trade.quantity > 0.0 {
                            let position = Position::new(
                                ticker_id as u32,
                                price,
                                Some(trade.quantity),
                                Some(timestamp),
                                self.position_constraints.get(ticker_id).cloned(),
                            );
                            trade.update_buy_trade(price, timestamp, actual_cost, trade.quantity);

                            let total_trade_cost = trade.quantity * price + actual_cost;
                            net_cash -= total_trade_cost;
                            total_cost += actual_cost;
                            self.positions[ticker_id] = Some(position);
                            executed_trades.push(trade.clone());
                        } else {
                            trade.update_trade_status(TradeStatus::Failed);
                            trade.set_comment("Insufficient cash".to_string());
                        }
                    } else {
                        trade.update_trade_status(TradeStatus::Failed);
                        trade.set_comment("Short sell prohibited".to_string());
                    }
                }
            }
        }
        (net_cash, total_cost, total_realized_pnl, executed_trades)
    }

    #[inline(always)]
    pub fn liquidation(&mut self, prices: &[f32], trades: &mut [Trade], timestamp: u64) {
        let (available_cash, total_cost, total_realized_pnl, _) =
            self.execute_trades(trades, prices, timestamp, &[]);

        self.post_order_update(
            prices, // Same slice for both executed and next
            available_cash,
            total_cost,
            total_realized_pnl,
        );
        self.pending_trades = Vec::new();
    }

    /// Get the period identifier for a timestamp based on frequency
    #[inline(always)]
    fn get_period_identifier(&self, timestamp: i64) -> i64 {
        match &self.portfolio_params.capital_growth_frequency {
            Frequency::Daily => timestamp / 86400, // Days since epoch
            Frequency::Weekly => {
                let days_since_epoch = timestamp / 86400;
                (days_since_epoch + 4) / 7 // Weeks since epoch (adjusted for Thursday start)
            }
            Frequency::Monthly => {
                let datetime = timestamp_to_datetime(timestamp);
                (datetime.year() as i64) * 12 + (datetime.month() as i64) - 1
            }
            Frequency::Quarterly => {
                let datetime = timestamp_to_datetime(timestamp);
                (datetime.year() as i64) * 4 + ((datetime.month() - 1) / 3) as i64
            }
            Frequency::Yearly => {
                let datetime = timestamp_to_datetime(timestamp);
                datetime.year() as i64
            }
        }
    }

    #[inline(always)]
    pub fn get_new_cash(&mut self, current_timestamp: i64) -> f32 {
        if !is_end_of_period(
            current_timestamp,
            &self.portfolio_params.capital_growth_frequency,
        ) {
            return 0.0;
        }

        let current_period = self.get_period_identifier(current_timestamp);

        // Check if we've already distributed cash for this period
        if let Some(last_period) = self.last_cash_distribution_period {
            if current_period == last_period {
                return 0.0; // Already distributed cash for this period
            }
        }

        // Update the last distribution period
        self.last_cash_distribution_period = Some(current_period);

        let current_equity = self.get_current_equity();
        return if self.portfolio_params.capital_growth_amount > 0.0 {
            self.portfolio_params.capital_growth_amount
        } else {
            current_equity * self.portfolio_params.capital_growth_pct
        };
    }

    #[inline(always)]
    pub fn get_current_cash(&self) -> f32 {
        *self.cash_curve.last().unwrap_or(&0.0)
    }

    #[inline(always)]
    pub fn get_current_equity(&self) -> f32 {
        *self.equity_curve.last().unwrap_or(&0.0)
    }

    #[inline(always)]
    pub fn get_position_count(&self) -> usize {
        self.positions.iter().filter(|p| p.is_some()).count()
    }
}
