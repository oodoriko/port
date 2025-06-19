//! Portfolio integration test

use crate::constraints::Constraint;
use crate::params::{
    PortfolioConstraintParams, PortfolioParams, PositionConstraintParams, SignalParams,
};
use crate::portfolio::Portfolio;
use crate::strategy::Strategy;
use crate::trade::Trade;
use crate::utils::ticker_to_id;
use env_logger;
use log;

#[cfg(test)]
fn backtest(
    strategy_name: String,
    portfolio_name: String,
    strategies: Vec<Vec<SignalParams>>,
    portfolio_params: PortfolioParams,
    portfolio_constraints: PortfolioConstraintParams,
    position_constraints: Vec<PositionConstraintParams>,
    constraint: Constraint,
    warm_up_period: usize,
) {
    // step one pull data - (n x T x 4)
    // step two initiation
    let strategy = Strategy::new(
        &strategy_name,
        &portfolio_name,
        strategies,
        portfolio_params,
        portfolio_constraints,
        position_constraints,
    );

    let strategy = strategy.create_portfolio();
    let portfolio = Portfolio::new(portfolio_name, 200_000.0);
    let constraint = strategy.create_constraints();
    let signals_generator = strategy.create_signals_generator(strategies);
    let warm_up_price_data = price_data_map.iter().take(warm_up_period).collect();
    strategy.warm_up_signals(&signals_generator, &warm_up_price_data);

    for (day, price_row) in price_data_map.iter().skip(warm_up_period).enumerate() {
        // portoflio preorder update - > get max drawn, stop loss
        // execute preorder updates if any

        // strategy.update_indicators()
        // strategy.generate_signals()
        
        // constraint.generate_trading_plan()
        // constraint.evaluate_trading_plan()

        // portfolio.execute_trading_plan()
        // portoflio.postorder_update()



}
