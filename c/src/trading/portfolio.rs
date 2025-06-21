use crate::core::params::{PortfolioConstraintParams, PortfolioParams, PositionConstraintParams};
use crate::trading::position::Position;
use crate::trading::trade::{Trade, TradeStatus};
use crate::utils::utils::is_end_of_period;

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
    pub timestamps: Vec<i64>,
    pub portfolio_params: PortfolioParams,
    pub portfolio_constraints: PortfolioConstraintParams,
    pub position_constraints: Vec<PositionConstraintParams>,
    pub trading_history: Vec<Vec<Trade>>,
    pub peak_notional: f32,
    pub num_assets: usize,
    commission_rate: f32,
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

        let mut trading_history = Vec::with_capacity(1000);
        trading_history.extend(vec![Vec::new(); 3]);

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
            timestamps: Vec::new(),
            trading_history,
            peak_notional: initial_cash,
            num_assets,
            commission_rate: 0.001,
        }
    }

    #[inline(always)]
    pub fn pre_order_update(&mut self, prices: &[Vec<f32>]) {
        for idx in 0..self.num_assets.min(prices.len()) {
            if let Some(pos) = &mut self.positions[idx] {
                let close_price = unsafe {
                    prices.get_unchecked(idx).get_unchecked(3) // Close price is index 3
                };
                pos.pre_order_update(*close_price);
            }
        }
    }

    #[inline(always)]
    pub fn post_order_update(
        &mut self,
        prices: &[f32],
        executed_trades: &[Trade],
        next_trades: &[Trade],
        available_cash: f32,
        total_cost: f32,
        total_realized_pnl: f32,
    ) {
        let len = self.trading_history.len();

        if len >= 2 {
            let second_to_last = &mut self.trading_history[len - 2];
            second_to_last.clear();
            second_to_last.extend_from_slice(executed_trades);
        }

        let mut next_trades_vec = Vec::with_capacity(next_trades.len());
        next_trades_vec.extend_from_slice(next_trades);
        self.trading_history.push(next_trades_vec);

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
        self.peak_notional = self.peak_notional.max(total_notional);
    }

    #[inline(always)]
    pub fn execute_trades(
        &mut self,
        trades: &mut [Trade],
        prices: &[f32],
        timestamp: u64,
    ) -> (f32, f32, f32) {
        let mut available_cash = *self.cash_curve.last().unwrap_or(&0.0);
        let min_cash_pct = self.portfolio_constraints.min_cash_pct;
        available_cash = available_cash * (1.0 - min_cash_pct);
        let mut total_cost = 0.0;
        let mut total_realized_pnl = 0.0;

        for trade in trades.iter_mut() {
            let ticker_id = trade.ticker_id;

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
                        let max_quantity = (available_cash - initial_cost).max(0.0) / price;
                        trade.quantity = max_quantity;
                        let actual_cost = trade.quantity * price * self.commission_rate;

                        if trade.quantity > 0.0 {
                            position.update_buy_position(
                                price,
                                trade.quantity,
                                timestamp,
                                actual_cost,
                            );
                            let total_trade_cost = trade.quantity * price + actual_cost;
                            available_cash -= total_trade_cost;
                            total_cost += actual_cost;
                            trade.update_buy_trade(price, timestamp, actual_cost);
                        }
                    } else {
                        let (realized_pnl, actual_quantity_sold) = position.update_sell_position(
                            price,
                            trade.quantity,
                            timestamp,
                            initial_cost,
                        );

                        trade.quantity = actual_quantity_sold;
                        trade.update_sell_trade(
                            price,
                            timestamp,
                            initial_cost,
                            position.avg_entry_price,
                            position.entry_timestamp,
                        );

                        total_realized_pnl += realized_pnl;
                        available_cash += actual_quantity_sold * price - initial_cost;
                        total_cost += initial_cost;

                        if position.quantity <= 0.0 {
                            self.positions[ticker_id] = None;
                        }
                    }
                }
                None => {
                    if trade.is_buy() {
                        let max_quantity = (available_cash - initial_cost).max(0.0) / price;
                        trade.quantity = max_quantity;
                        let actual_cost = trade.quantity * price * self.commission_rate;

                        if trade.quantity > 0.0 {
                            let position = Position::new(
                                ticker_id as u32,
                                price,
                                Some(trade.quantity),
                                Some(timestamp),
                                self.position_constraints.get(ticker_id).cloned(),
                            );
                            trade.update_buy_trade(price, timestamp, actual_cost);

                            let total_trade_cost = trade.quantity * price + actual_cost;
                            available_cash -= total_trade_cost;
                            total_cost += actual_cost;
                            self.positions[ticker_id] = Some(position);
                        }
                    } else {
                        trade.update_trade_status(TradeStatus::Failed);
                        trade.set_comment("Short sell prohibited".to_string());
                    }
                }
            }
        }

        (available_cash, total_cost, total_realized_pnl)
    }

    #[inline(always)]
    pub fn liquidation(&mut self, prices: &[f32], trades: &mut [Trade], timestamp: u64) {
        let (available_cash, total_cost, total_realized_pnl) =
            self.execute_trades(trades, prices, timestamp);

        self.post_order_update(
            prices,
            trades,
            trades, // Same slice for both executed and next
            available_cash,
            total_cost,
            total_realized_pnl,
        );

        let mut trades_copy = Vec::with_capacity(trades.len());
        trades_copy.extend_from_slice(trades);
        self.trading_history.push(trades_copy);
    }

    #[inline(always)]
    pub fn update_capital(&mut self, current_timestamp: i64) {
        if !is_end_of_period(
            current_timestamp,
            &self.portfolio_params.capital_growth_frequency,
        ) {
            return;
        }

        let current_equity = *self.equity_curve.last().unwrap_or(&0.0);
        let current_cash = *self.cash_curve.last().unwrap_or(&0.0);
        let capital_increase = if self.portfolio_params.capital_growth_amount > 0.0 {
            self.portfolio_params.capital_growth_amount
        } else {
            current_equity * self.portfolio_params.capital_growth_pct
        };

        let new_cash = current_cash + capital_increase;
        let len = self.cash_curve.len();
        self.cash_curve.insert(len - 1, new_cash);
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
