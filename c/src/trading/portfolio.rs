use crate::params::{PortfolioConstraintParams, PortfolioParams, PositionConstraintParams};
use crate::position::Position;
use crate::trade::Trade;

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
    pub trading_history: Vec<Vec<Trade>>,
    pub peak_notional: f32,
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
            trading_history: vec![vec![]; 2],
            peak_notional: initial_cash,
        }
    }

    pub fn pre_order_update(&mut self, prices: &Vec<Vec<f32>>) {
        for (idx, position) in self.positions.iter_mut().enumerate() {
            if let Some(pos) = position {
                pos.pre_order_update(prices[idx][3]); // update with close price
            }
        }
    }

    pub fn post_order_update(
        &mut self,
        prices: &[f32],
        executed_trades: &[Trade],
        next_trades: &[Trade],
    ) {
        // position, trades, cash, cost and realized pnl are updated in execute_trades
        let current_idx = self.trading_history.len() - 1;
        self.trading_history[current_idx - 1] = executed_trades.to_vec();
        self.trading_history[current_idx] = next_trades.to_vec();

        let mut total_notional = 0.0;
        let mut total_unrealized_pnl = 0.0;

        for (idx, position) in self.positions.iter_mut().enumerate() {
            if let Some(pos) = position {
                let (notional, unrealized_pnl) = pos.post_order_update(prices[idx]);
                total_notional += notional;
                total_unrealized_pnl += unrealized_pnl;
                self.holdings[idx] = pos.quantity;
            }
        }

        let total_equity = total_notional + self.cash_curve.last().unwrap_or(&0.0);
        self.equity_curve.push(total_equity);
        self.notional_curve.push(total_notional);
        self.unrealized_pnl_curve.push(total_unrealized_pnl);
        self.peak_notional = self.peak_notional.max(total_notional);
    }

    pub fn execute_trades(&mut self, trades: &mut Vec<Trade>, prices: &[f32], timestamp: u64) {
        let mut cash = *self.cash_curve.last().unwrap_or(&0.0);
        let mut total_cost = 0.0;
        let mut total_realized_pnl = 0.0;

        for trade in trades.iter_mut() {
            let ticker_id = trade.ticker_id as usize;
            let price = prices[ticker_id];
            let cost = trade.quantity * price * 0.001; // 10bps commission

            match &mut self.positions[ticker_id] {
                Some(position) => {
                    if trade.quantity < 0.0 {
                        let realized_pnl =
                            position.update_sell_position(price, trade.quantity, timestamp, cost);

                        trade.update_sell_trade(
                            price,
                            timestamp,
                            cost,
                            position.avg_entry_price,
                            position.entry_timestamp,
                        );
                        total_realized_pnl += realized_pnl;
                        cash -= trade.quantity * price - cost;
                        total_cost += cost;
                    } else if trade.quantity > 0.0 {
                        position.update_buy_position(price, trade.quantity, timestamp, cost);
                        cash -= trade.quantity * price - cost;
                        total_cost += cost;
                    }
                }
                None => {
                    if trade.quantity > 0.0 {
                        // new position
                        let position = Position::new(
                            trade.ticker_id as u32,
                            price,
                            Some(trade.quantity),
                            Some(timestamp),
                            None, // ticker string not available
                            None, // constraint not available
                        );
                        trade.update_buy_trade(price, timestamp, cost);
                        cash -= trade.quantity * price + cost;
                        self.positions[ticker_id] = Some(position);
                    } else {
                        trade.update_trade_status(
                            "Failed".to_string(),
                            "Short sell prohibited".to_string(),
                        );
                    }
                }
            }

            total_cost += cost;
        }

        self.cash_curve.push(cash);
        self.cost_curve.push(total_cost);
        self.realized_pnl_curve.push(total_realized_pnl);
    }

    pub fn liquidation(&mut self, prices: &[f32], trades: &mut Vec<Trade>, timestamp: u64) {
        self.execute_trades(trades, prices, timestamp);
        self.post_order_update(prices, &trades, &trades);
        self.trading_history.push(trades.clone());
    }
}
