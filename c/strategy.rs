use crate::constraints::Constraint;
use crate::params::{
    PortfolioConstraintParams, PortfolioParams, PositionConstraintParams, SignalParams,
};
use crate::portfolio::Portfolio;
use crate::signals::*;
use std::collections::HashMap;

pub enum SignalType {
    EmaRsiMacd,
    BbRsiOversold,
    BbRsiOverbought,
    PatternRsiMacd,
    TripleEmaPatternMacdRsi,
    BbSqueezeBreakout,
    RsiOversoldReversal,
    SupportBounce,
    UptrendPattern,
    StochOversold,
}

impl SignalType {
    pub fn from_name(name: &str) -> Option<Self> {
        match name {
            "ema_rsi_macd" => Some(SignalType::EmaRsiMacd),
            "bb_rsi_oversold" => Some(SignalType::BbRsiOversold),
            "bb_rsi_overbought" => Some(SignalType::BbRsiOverbought),
            "pattern_rsi_macd" => Some(SignalType::PatternRsiMacd),
            "triple_ema_pattern_macd_rsi" => Some(SignalType::TripleEmaPatternMacdRsi),
            "bb_squeeze_breakout" => Some(SignalType::BbSqueezeBreakout),
            "rsi_oversold_reversal" => Some(SignalType::RsiOversoldReversal),
            "support_bounce" => Some(SignalType::SupportBounce),
            "uptrend_pattern" => Some(SignalType::UptrendPattern),
            "stoch_oversold" => Some(SignalType::StochOversold),
            _ => None,
        }
    }
}

// basically a backtest recipe
pub struct Strategy {
    pub name: String,
    pub portfolio_name: String,
    pub portfolio_params: PortfolioParams,
    pub portfolio_constraints: PortfolioConstraintParams,
    pub position_constraints: Vec<PositionConstraintParams>,
}

impl Strategy {
    pub fn new(
        name: &str,
        portfolio_name: &str,
        portfolio_params: PortfolioParams,
        portfolio_constraints: PortfolioConstraintParams,
        position_constraints: Vec<PositionConstraintParams>,
    ) -> Self {
        Self {
            name: name.to_string(),
            portfolio_name: portfolio_name.to_string(),
            portfolio_params,
            portfolio_constraints,
            position_constraints: position_constraints.clone(),
        }
    }

    pub fn create_portfolio(&self) -> Portfolio {
        let num_assets = self.signals.len();
        let position_constraint = self
            .position_constraints
            .get(0)
            .cloned()
            .unwrap_or_default();
        Portfolio::new(
            self.portfolio_name.to_string(),
            num_assets,
            self.portfolio_params.clone(),
            self.portfolio_constraints.clone(),
            position_constraint,
        )
    }

    pub fn create_constraints(&self) -> Constraint {
        Constraint::from_position_constraints(&self.position_constraints)
    }

    pub fn create_signals_generator(
        strategies: Vec<HashMap<String, SignalParams>>,
    ) -> Vec<HashMap<String, Signal>> {
        let mut all_tickers_signals = Vec::new();
        for strategy in strategies {
            // indexed by ticker
            let mut singl_ticker_signals = Vec::new();
            for (sig_name, params) in strategy {
                if let Some(signal) = create_signal_from_params(&params) {
                    singl_ticker_signals.push((sig_name, signal));
                }
            }
            all_tickers_signals.extend(singl_ticker_signals);
        }
        all_tickers_signals
    }

    pub fn warm_up_signals(
        &mut self,
        signals: &HashMap<String, Signal>,
        price_data_map: &HashMap<usize, Vec<[f32; 4]>>,
    ) {
        for (&ticker_id, price_data) in price_data_map.iter() {
            if let Some(signals) = signals.get_mut(&ticker_id) {
                for row in price_data {
                    let price = row[0];
                    let high = Some(row[1]);
                    let low = Some(row[2]);
                    let close = Some(row[3]);
                    for sig in signals.iter_mut() {
                        sig.update(price, high, low, close);
                    }
                }
            }
        }
    }
    // generate signals for each ticker
}

pub fn create_signal_from_params(params: &SignalParams) -> Option<Box<dyn Signal>> {
    if let Some(sig) = EmaRsiMacdSignal::from_params(params) {
        return Some(Box::new(sig));
    }
    if let Some(sig) = BbRsiOversoldSignal::<20>::from_params(params) {
        return Some(Box::new(sig));
    }
    if let Some(sig) = BbRsiOverboughtSignal::<20>::from_params(params) {
        return Some(Box::new(sig));
    }
    if let Some(sig) = PatternRsiMacdSignal::<20, 10>::from_params(params) {
        return Some(Box::new(sig));
    }
    if let Some(sig) = TripleEmaPatternMacdRsiSignal::<20, 10>::from_params(params) {
        return Some(Box::new(sig));
    }
    if let Some(sig) = BbSqueezeBreakoutSignal::<20>::from_params(params) {
        return Some(Box::new(sig));
    }
    if let Some(sig) = RsiOversoldReversalSignal::from_params(params) {
        return Some(Box::new(sig));
    }
    if let Some(sig) = SupportBounceSignal::<20, 10>::from_params(params) {
        return Some(Box::new(sig));
    }
    if let Some(sig) = UptrendPatternSignal::<20, 10>::from_params(params) {
        return Some(Box::new(sig));
    }
    if let Some(sig) = StochOversoldSignal::<14, 3, 3>::from_params(params) {
        return Some(Box::new(sig));
    }
    None
}
