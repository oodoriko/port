use crate::core::params::{
    PortfolioConstraintParams, PortfolioParams, PositionConstraintParams, SignalParams,
};
use crate::data::data::InfluxDBHandler;
use crate::trading::portfolio::Portfolio;
use crate::trading::strategy::Strategy;
use chrono::{DateTime, Utc};
use std::collections::HashMap;

pub async fn backtest(
    strategy_name: String,
    portfolio_name: String,
    start: DateTime<Utc>,
    end: DateTime<Utc>,
    strategies: HashMap<String, Vec<SignalParams>>,
    portfolio_params: PortfolioParams,
    portfolio_constraints_params: PortfolioConstraintParams,
    position_constraints_params: Vec<PositionConstraintParams>,
    warm_up_period: usize,
    cadence: u64, // in minutes
) -> Result<Portfolio, Box<dyn std::error::Error>> {
    let handler = InfluxDBHandler::new()?;
    let tickers: Vec<String> = strategies.keys().cloned().collect();
    let strategies_vec: Vec<Vec<SignalParams>> = tickers
        .iter()
        .map(|ticker| strategies[ticker].clone())
        .collect();

    let ticker_refs: Vec<&str> = tickers.iter().map(|s| s.as_str()).collect();
    let (data, timestamps) = handler.load_data(&ticker_refs, start, end).await?;
    let warm_up_price_data: Vec<Vec<Vec<f32>>> =
        data.iter().take(warm_up_period).cloned().collect();

    let mut strategy = Strategy::new(
        &strategy_name,
        &portfolio_name,
        portfolio_params,
        portfolio_constraints_params,
        position_constraints_params,
        &strategies_vec,
    );

    let mut portfolio = strategy.create_portfolio();
    let mut constraint = strategy.create_constraints();
    constraint.set_cadence(cadence * 60);
    strategy.warm_up_signals(&warm_up_price_data);

    let mut exit = false;
    for idx in warm_up_period..timestamps.len() {
        let time = timestamps[idx];

        let close_prices: Vec<f32> = data[idx].iter().map(|asset_ohlcv| asset_ohlcv[3]).collect();

        if exit {
            let mut liquidation_trades =
                portfolio.trading_history[portfolio.trading_history.len() - 1].clone();
            portfolio.liquidation(&close_prices, &mut liquidation_trades, time as u64);
            break;
        }

        portfolio.pre_order_update(&data[idx]);
        let (is_exit, mut priority_sell_trades) = constraint.pre_order_check(
            &close_prices,
            &portfolio.positions,
            portfolio.equity_curve[portfolio.equity_curve.len() - 1],
        );

        if is_exit {
            exit = true;
            // overwrite any existing pending trades from last period
            portfolio.post_order_update(&close_prices, &Vec::new(), &priority_sell_trades);
            continue;
        }
        // execute priority sell trades
        portfolio.execute_trades(&mut priority_sell_trades, &close_prices, time as u64);

        // generate signals
        strategy.update_signals(data[idx].clone());
        let signals = strategy.generate_signals();
        let mut signals_adjusted = signals.clone();
        for trade in priority_sell_trades.iter() {
            signals_adjusted[trade.ticker_id] = 0;
        }

        // generate trading plan, positions level constraint is checked during generate_trades, portfolio level constraint is checked during evaluate_trades
        let mut trades = constraint.generate_trades(
            &signals_adjusted,
            &close_prices,
            portfolio.equity_curve[portfolio.equity_curve.len() - 1],
            &portfolio.positions,
        );
        trades = constraint.evaluate_trades(
            &trades,
            &close_prices,
            portfolio.equity_curve[portfolio.equity_curve.len() - 1],
            time as u64,
            &portfolio.positions,
        );

        // execute trades from previous period
        let mut prev_trades =
            portfolio.trading_history[portfolio.trading_history.len() - 1].clone();
        if prev_trades.len() > 0 {
            portfolio.execute_trades(&mut prev_trades, &close_prices, time as u64);
            prev_trades.extend(priority_sell_trades);
        }

        portfolio.post_order_update(&close_prices, &prev_trades, &trades);
    }
    Ok(portfolio)
}

pub fn backtest_result(portfolio: Portfolio) {
    println!("=== BACKTEST RESULTS ===\n");

    println!("📊 Portfolio: {}", portfolio.name);
    println!("📈 Total Records: {}", portfolio.equity_curve.len());

    if portfolio.equity_curve.is_empty() {
        println!("❌ No data to display");
        return;
    }

    // Summary statistics
    let initial_value = portfolio.equity_curve[0];
    let final_value = *portfolio.equity_curve.last().unwrap();
    let total_return = (final_value - initial_value) / initial_value * 100.0;
    let max_equity = portfolio
        .equity_curve
        .iter()
        .fold(f32::NEG_INFINITY, |a, &b| a.max(b));
    let min_equity = portfolio
        .equity_curve
        .iter()
        .fold(f32::INFINITY, |a, &b| a.min(b));

    println!("\n💰 PERFORMANCE SUMMARY:");
    println!("  Initial Value: ${:.2}", initial_value);
    println!("  Final Value:   ${:.2}", final_value);
    println!("  Total Return:  {:.2}%", total_return);
    println!("  Max Value:     ${:.2}", max_equity);
    println!("  Min Value:     ${:.2}", min_equity);
    println!("  Peak Notional: ${:.2}", portfolio.peak_notional);

    println!("\n=== END BACKTEST RESULTS ===");
}

mod tests {
    use super::backtest;
    use crate::core::params::{
        PortfolioConstraintParams, PortfolioParams, PositionConstraintParams,
    };
    use crate::utils::utils::create_sample_strategies;
    use chrono::TimeZone;
    use chrono::Utc;
    #[tokio::test]
    async fn test_backtest() {
        let start = Utc.with_ymd_and_hms(2025, 6, 17, 16, 0, 0).unwrap();
        let end = Utc.with_ymd_and_hms(2025, 6, 19, 17, 0, 0).unwrap();

        let strategies = create_sample_strategies();

        let portfolio = backtest(
            String::from("test_strategy"),
            String::from("test_portfolio"),
            start,
            end,
            strategies,
            PortfolioParams::default(),
            PortfolioConstraintParams::default(),
            vec![
                PositionConstraintParams::default(),
                PositionConstraintParams::default(),
            ],
            10,
            1,
        )
        .await
        .unwrap();

        // Print the backtest results
        super::backtest_result(portfolio);
    }
}
