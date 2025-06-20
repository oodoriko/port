use crate::constraints::Constraint;
use crate::params::{
    PortfolioConstraintParams, PortfolioParams, PositionConstraintParams, SignalParams,
};
use crate::portfolio::Portfolio;
use crate::r#const::{MAX_ASSETS, MAX_SIGNALS_PER_ASSET};
use crate::signals::*;

pub struct Strategy {
    pub name: String,
    pub portfolio_name: String,
    pub portfolio_params: PortfolioParams,
    pub portfolio_constraints: PortfolioConstraintParams,
    pub position_constraints: Vec<PositionConstraintParams>,
    pub strategies: Vec<Vec<SignalParams>>,
    signal_generator: SignalGenerator,
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
        let signal_generator = Self::create_signal_generator(strategies);
        Self {
            name: name.to_string(),
            portfolio_name: portfolio_name.to_string(),
            portfolio_params,
            portfolio_constraints,
            position_constraints,
            strategies: strategies.to_vec(),
            signal_generator,
        }
    }

    pub fn create_portfolio(&self) -> Portfolio {
        let num_assets = self.strategies.len();

        Portfolio::new(
            self.portfolio_name.to_string(),
            num_assets,
            self.portfolio_params.clone(),
            self.portfolio_constraints.clone(),
            self.position_constraints.clone(),
        )
    }

    pub fn create_constraints(&self) -> Constraint {
        Constraint::from_position_constraints(&self.position_constraints)
    }

    pub fn update_signals(&mut self, data: Vec<Vec<f32>>) {
        assert!(data.len() <= MAX_ASSETS, "Too many assets in OHLC data");
        self.signal_generator.update(data);
    }
    pub fn generate_signals(&self) -> Vec<i8> {
        self.signal_generator.generate_signals()
    }

    fn create_signal_generator(strategies: &[Vec<SignalParams>]) -> SignalGenerator {
        let mut signal_generator = SignalGenerator::new(strategies.len());

        for (asset_idx, asset_strategies) in strategies.iter().enumerate() {
            assert!(
                asset_strategies.len() <= MAX_SIGNALS_PER_ASSET,
                "Too many signals for asset {}",
                asset_idx
            );
            for strategy_params in asset_strategies {
                if let Some(signal) = create_signal_from_params(strategy_params) {
                    signal_generator.add_signal(asset_idx, signal);
                }
            }
        }
        signal_generator
    }

    pub fn warm_up_signals(&mut self, data: &Vec<Vec<Vec<f32>>>) {
        for time_data in data.iter() {
            for (asset_idx, asset_ohlcv) in time_data.iter().enumerate() {
                if let Some(signals) = self.signal_generator.signals.get_mut(asset_idx) {
                    for signal in signals.iter_mut() {
                        signal.update(
                            asset_ohlcv[0],
                            asset_ohlcv[1],
                            asset_ohlcv[2],
                            asset_ohlcv[3],
                        );
                    }
                }
            }
        }
    }
}
