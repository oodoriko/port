use crate::params::{PortfolioConstraintParams, PortfolioParams, PositionConstraintParams};
use crate::position::Position;
use crate::trade::Trade;
use crate::utils::ticker_to_constraint;
use std::collections::HashMap;

// portfolio::constraint:
// max_drawdown_pct

#[derive(Debug)]
pub struct Portfolio {
    pub name: String,
    pub positions: Vec<Option<Position>>, // indexed by ticker_id
    pub holdings: Vec<f64>,               // indexed by ticker_id, just the total shares
    pub equity_curve: Vec<f64>,
    pub cash_curve: Vec<f64>,
    pub notional_curve: Vec<f64>,
    pub cost_curve: Vec<f64>,
    pub realized_pnl_curve: Vec<f64>,
    pub unrealized_pnl_curve: Vec<f64>,
    pub portfolio_params: PortfolioParams,
    pub portfolio_constraints: PortfolioConstraintParams,
    pub position_constraints: PositionConstraintParams,
    pub trading_history: HashMap<u64, Vec<Trade>>,
}

impl Portfolio {
    pub fn new(
        name: String,
        num_assets: usize,
        portfolio_params: PortfolioParams,
        portfolio_constraints: PortfolioConstraintParams,
        position_constraints: PositionConstraintParams,
    ) -> Self {
        let initial_cash = portfolio_params.initial_cash;
        Self {
            name,
            portfolio_params,
            portfolio_constraints,
            position_constraints,
            positions: vec![None; num_assets],
            holdings: vec![0.0; num_assets],
            equity_curve: vec![initial_cash],
            cash_curve: vec![initial_cash],
            notional_curve: vec![initial_cash],
            cost_curve: vec![0.0],
            realized_pnl_curve: vec![0.0],
            unrealized_pnl_curve: vec![0.0],
            trading_history: HashMap::new(),
        }
    }
    // preorder update and check
    fn execute_buy(
        &mut self,
        prices: &[f64],
        trading_plan: &mut [Trade],
        timestamp: u64,
    ) -> (f64, f64) {
        let mut total_cost = 0.0;
        let mut total_cash_spent = 0.0;
        for trade in trading_plan.iter_mut() {
            if trade.quantity <= 0.0 {
                continue;
            }
            if let Some(&price) = prices.get(trade.ticker_id) {
                let cost = trade.quantity * price;
                let idx = trade.ticker_id;
                match &mut self.positions[idx] {
                    Some(position) => {
                        position.update_buy_position(price, trade.quantity, timestamp, 0.0);
                    }
                    None => {
                        let position = Position::new(
                            &trade.ticker,
                            trade.quantity,
                            price,
                            0.0,
                            timestamp,
                            ticker_to_constraint()
                                .get(&trade.ticker)
                                .cloned()
                                .unwrap_or_default(),
                        );
                        self.positions[idx] = Some(position);
                    }
                }
                total_cost += 0.0; // missing model
                total_cash_spent += cost;
                trade.update_buy_trade(price, timestamp, cost);
                self.holdings[idx] += trade.quantity;
            } else {
                println!("Price not found for ticker: {}", trade.ticker);
                trade.update_trade_status(
                    "Failed".to_string(),
                    "Ticker or price not found".to_string(),
                );
                continue;
            }
        }
        (total_cost, total_cash_spent)
    }

    fn execute_sell(
        &mut self,
        prices: &[f64],
        trading_plan: &mut [Trade],
        timestamp: u64,
    ) -> (f64, f64, f64) {
        let mut total_realized_pnl = 0.0;
        let mut total_cost = 0.0;
        let mut total_cash_received = 0.0;
        for trade in trading_plan.iter_mut() {
            if trade.quantity >= 0.0 {
                continue;
            }
            if let Some(&price) = prices.get(trade.ticker_id) {
                let idx = trade.ticker_id;
                if let Some(position) = self.positions[idx].as_mut() {
                    let realized_pnl =
                        position.update_sell_position(price, trade.quantity, timestamp, 0.0);
                    total_realized_pnl += realized_pnl;
                    total_cost += 0.0;
                    total_cash_received += -trade.quantity * price; // trade qty is negative
                    trade.update_sell_trade(
                        price,
                        timestamp,
                        0.0,
                        "signal_sell".to_string(),
                        position.avg_entry_price,
                        position.entry_timestamp,
                    );
                    self.holdings[idx] -= trade.quantity; // bc trade qty is negative
                } else {
                    println!("Position not found for ticker: {}", trade.ticker);
                    trade.update_trade_status(
                        "Failed".to_string(),
                        "Position not found".to_string(),
                    );
                    continue;
                }
            } else {
                println!("Price not found for ticker: {}", trade.ticker);
                trade.update_trade_status(
                    "Failed".to_string(),
                    "Ticker or price not found".to_string(),
                );
                continue;
            }
        }
        (total_realized_pnl, total_cost, total_cash_received)
    }

    // postorder update
}
