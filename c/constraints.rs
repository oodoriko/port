use crate::params::PositionConstraintParams;

pub struct Constraint {
    pub max_position_size_pct: Vec<f32>,
    pub min_trade_size_pct: Vec<f32>,
    pub min_holding_candle: Vec<u32>,
    pub trailing_stop_loss_pct: Vec<f32>,
    pub trailing_stop_update_threshold_pct: Vec<f32>,
    pub take_profit_pct: Vec<f32>,
    pub risk_per_trade_pct: Vec<f32>,
    pub sell_fraction: Vec<f32>,
}

impl Constraint {
    pub fn from_position_constraints(position_constraints: &[PositionConstraintParams]) -> Self {
        let mut max_position_size_pct = Vec::new();
        let mut min_trade_size_pct = Vec::new();
        let mut min_holding_candle = Vec::new();
        let mut trailing_stop_loss_pct = Vec::new();
        let mut trailing_stop_update_threshold_pct = Vec::new();
        let mut take_profit_pct = Vec::new();
        let mut risk_per_trade_pct = Vec::new();
        let mut sell_fraction = Vec::new();

        for pc in position_constraints {
            max_position_size_pct.push(pc.max_position_size_pct as f32);
            min_trade_size_pct.push(pc.min_trade_size_pct as f32);
            min_holding_candle.push(pc.min_holding_candle as u32);
            trailing_stop_loss_pct.push(pc.trailing_stop_loss_pct as f32);
            trailing_stop_update_threshold_pct.push(pc.trailing_stop_update_threshold_pct as f32);
            take_profit_pct.push(pc.take_profit_pct as f32);
            risk_per_trade_pct.push(pc.risk_per_trade_pct as f32);
            sell_fraction.push(pc.sell_fraction as f32);
        }

        Self {
            max_position_size_pct,
            min_trade_size_pct,
            min_holding_candle,
            trailing_stop_loss_pct,
            trailing_stop_update_threshold_pct,
            take_profit_pct,
            risk_per_trade_pct,
            sell_fraction,
        }
    }
    #[inline(always)]
    pub fn calculate_max_pos_size_by_risk(
        &self,
        trades: &[i8],
        price: &[f32],
        portfolio_value: f32,
        holdings: &[f64],
    ) -> Vec<f32> {
        trades
            .iter()
            .enumerate()
            .map(|(i, trade)| {
                if *trade == -1 {
                    (holdings[i] * self.sell_fraction[i] as f64) as f32
                } else {
                    let risk_per_trade = price[i] * self.risk_per_trade_pct[i];
                    (self.max_position_size_pct[i] * portfolio_value) / risk_per_trade
                }
            })
            .collect()
    }

    // pub fn evaluate_trades(
    //     &self,
    //     trades: &[i8],
    //     price: &[f32],
    //     portfolio_value: f32,
    //     holdings: &[f64],
    // ) -> Vec<f32> {
    // }
}
