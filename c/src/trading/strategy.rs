use crate::constraints::Constraint;
use crate::params::{
    PortfolioConstraintParams, PortfolioParams, PositionConstraintParams, SignalParams,
};
use crate::portfolio::Portfolio;
use crate::r#const::MAX_ASSETS;
use crate::signals::*;

pub struct Strategy {
    pub name: String,
    pub portfolio_name: String,
    pub portfolio_params: PortfolioParams,
    pub portfolio_constraints: PortfolioConstraintParams,
    pub position_constraints: Vec<PositionConstraintParams>,
    pub signal_generator: SignalGenerator,
    pub n_assets: usize,
}

impl Strategy {
    pub fn new(
        name: &str,
        portfolio_name: &str,
        portfolio_params: PortfolioParams,
        portfolio_constraints: PortfolioConstraintParams,
        position_constraints: Vec<PositionConstraintParams>,
        strategies: &[Vec<SignalParams>],
    ) -> Self {
        assert!(strategies.len() <= MAX_ASSETS, "Too many assets");
        let n_assets = strategies.len();
        let signal_generator = Self::create_signal_generator(strategies);
        Self {
            name: name.to_string(),
            portfolio_name: portfolio_name.to_string(),
            portfolio_params,
            portfolio_constraints,
            position_constraints,
            signal_generator,
            n_assets,
        }
    }

    pub fn create_portfolio(&self) -> Portfolio {
        Portfolio::new(
            self.portfolio_name.clone(),
            self.n_assets,
            self.portfolio_params.clone(),
            self.portfolio_constraints.clone(),
            self.position_constraints.clone(),
        )
    }

    pub fn create_constraints(&self) -> Constraint {
        Constraint::from_position_constraints(
            &self.position_constraints,
            self.portfolio_constraints.clone(),
        )
    }

    #[inline(always)]
    pub fn update_signals(&mut self, data: Vec<Vec<f32>>) {
        self.signal_generator.update(data);
    }

    #[inline(always)]
    pub fn generate_signals(&self) -> Vec<i8> {
        self.signal_generator.generate_signals()
    }

    fn create_signal_generator(strategies: &[Vec<SignalParams>]) -> SignalGenerator {
        let mut signal_generator = SignalGenerator::new(strategies.len());

        for (asset_idx, asset_strategies) in strategies.iter().enumerate() {
            for strategy_params in asset_strategies {
                if let Some(signal) = create_signal_from_params(strategy_params) {
                    signal_generator.add_signal(asset_idx, signal);
                }
            }
        }
        signal_generator
    }

    #[inline(always)]
    pub fn warm_up_signals(&mut self, data: &[Vec<Vec<f32>>]) {
        let n_assets = self.n_assets;

        for time_data in data.iter() {
            let signals = &mut self.signal_generator.signals;

            for asset_idx in 0..n_assets.min(time_data.len()) {
                let asset_ohlcv = &time_data[asset_idx];
                let (open, high, low, close) = unsafe {
                    (
                        *asset_ohlcv.get_unchecked(0),
                        *asset_ohlcv.get_unchecked(1),
                        *asset_ohlcv.get_unchecked(2),
                        *asset_ohlcv.get_unchecked(3),
                    )
                };

                if let Some(asset_signals) = signals.get_mut(asset_idx) {
                    for signal in asset_signals.iter_mut() {
                        signal.update(open, high, low, close);
                    }
                }
            }
        }
    }
}
