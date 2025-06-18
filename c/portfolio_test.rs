//! Portfolio integration test

use crate::portfolio::Portfolio;
use crate::trade::Trade;
use crate::utils::ticker_to_id;
use env_logger;
use log;

#[cfg(test)]
fn test_simple_trading_flow() {
    let _ = env_logger::builder()
        .is_test(true)
        .filter_level(log::LevelFilter::Info)
        .try_init();

    let prices = vec![
        vec![50000.0, 4000.0],
        vec![51000.0, 4200.0],
        vec![49500.0, 4100.0],
    ];

    let mut portfolio = Portfolio::new("TestPortfolio".to_string(), 200_000.0);
    let mut cash = *portfolio.cash_curve.last().unwrap();
    let mut realized_pnl = 0.0;
    let mut cost = 0.0;

    for (day, price_row) in prices.iter().enumerate() {
        let timestamp = day as u64;
        let mut trading_plan = vec![];
        for (_k, v) in portfolio.positions.iter_mut() {
            if let Some(&price) = price_row.get(v.id) {
                if let Some(sl_trades) = v.pre_order_update(price) {
                    trading_plan.push(sl_trades);
                }
            }
        }
        match day {
            0 => {
                trading_plan.push(Trade::new("BTC", 1.0));
                trading_plan.push(Trade::new("ETH", 2.0));
            }
            1 => {
                trading_plan.push(Trade::new("BTC", -0.5));
                trading_plan.push(Trade::new("ETH", -1.0));
            }
            _ => {}
        }

        if trading_plan.iter().any(|t| t.quantity > 0.0) {
            let (buy_cost, cash_spent) =
                portfolio.execute_buy(price_row, &mut trading_plan, timestamp);
            cost += buy_cost;
            cash -= cash_spent;
        }

        if trading_plan.iter().any(|t| t.quantity < 0.0) {
            let (realized, sell_cost, cash_received) =
                portfolio.execute_sell(price_row, &mut trading_plan, timestamp);
            realized_pnl += realized;
            cost += sell_cost;
            cash += cash_received;
        }

        let mut notional = 0.0;
        let mut unrealized_pnl = 0.0;
        for (_k, v) in portfolio.positions.iter_mut() {
            if let Some(&price) = price_row.get(v.id) {
                let (market_value, pos_unrealized_pnl) = v.post_order_update(price);
                notional += market_value;
                unrealized_pnl += pos_unrealized_pnl;
            }
        }

        portfolio.equity_curve.push(cash + notional + realized_pnl);
        portfolio.cash_curve.push(cash);
        portfolio.notional_curve.push(notional);
        portfolio.cost_curve.push(cost);
        portfolio.realized_pnl_curve.push(realized_pnl);
        portfolio.unrealized_pnl_curve.push(unrealized_pnl);

        log::info!(
            "day: {}, cash: {}, notional: {}, realized_pnl: {}, unrealized_pnl: {}, positions: {:?}",
            day,
            cash,
            notional,
            realized_pnl,
            unrealized_pnl,
            portfolio.positions
        );
        portfolio.trading_history.insert(timestamp, trading_plan);

        let tol = 1e-6;
        match day {
            0 => {
                // day one notional is: 50000*1 + 4000*2 = 58000
                // day one cash is: 200000 - 58000 = 142000
                // day one equity is: 58000 + 142000 = 200000
                assert!((notional - 58000.0).abs() < tol, "Day 0 notional");
                assert!((cash - 142000.0).abs() < tol, "Day 0 cash");
                assert!(
                    (portfolio.equity_curve.last().unwrap() - 200000.0).abs() < tol,
                    "Day 0 equity"
                );
                // peak price after day 0 is just entry price
                let btc = portfolio.positions.get("BTC").unwrap();
                let eth = portfolio.positions.get("ETH").unwrap();
                assert!((btc.peak_price - 50000.0).abs() < tol, "Day 0 BTC peak");
                assert!((eth.peak_price - 4000.0).abs() < tol, "Day 0 ETH peak");
            }
            1 => {
                // day two notional is: 51000*0.5 + 4200*1 = 29700
                // day two cash is: 142000 + 29700 = 171700
                // day two equity is: 29700 + 171700 = 201400
                // day two realized pnl is: (51000-50000)*0.5 + (4200-4000)*1 = 500 + 200 = 700
                // day two unrealized on eth is: (4200-4000)*1 = 200
                // day two unrealized on btc is: (51000-50000)*0.5 = 500
                // day two peak price for etc is 4200
                // day two peak price for btc is 51000
                assert!((notional - 29700.0).abs() < tol, "Day 1 notional");
                assert!((cash - 171700.0).abs() < tol, "Day 1 cash");
                assert!(
                    (portfolio.equity_curve.last().unwrap() - 201400.0).abs() < tol,
                    "Day 1 equity"
                );
                assert!((realized_pnl - 700.0).abs() < tol, "Day 1 realized");
                let btc = portfolio.positions.get("BTC").unwrap();
                let eth = portfolio.positions.get("ETH").unwrap();
                assert!((btc.peak_price - 51000.0).abs() < tol, "Day 1 BTC peak");
                assert!((eth.peak_price - 4200.0).abs() < tol, "Day 1 ETH peak");

                let btc_unrealized = (51000.0 - 50000.0) * 0.5;
                let eth_unrealized = (4200.0 - 4000.0) * 1.0;
                println!("Day 1 BTC unrealized: {:?}", btc.unrealized_pnl);
                println!("Day 1 ETH unrealized: {:?}", eth.unrealized_pnl);
                println!("Day 1 total unrealized: {}", unrealized_pnl);
                assert!(
                    (btc.unrealized_pnl.unwrap_or(0.0) - btc_unrealized).abs() < tol,
                    "Day 1 BTC unrealized"
                );
                assert!(
                    (eth.unrealized_pnl.unwrap_or(0.0) - eth_unrealized).abs() < tol,
                    "Day 1 ETH unrealized"
                );
            }
            2 => {
                // day three notional is: 49500*0.5 + 4100*1 = 28850
                // day three cash is: 171700
                // day three equity is: 28850 + 171700 + 700 - 350 = 200900
                // day three realized pnl curve is: 700
                // day three unrealized pnl curve is: (4100-4000)*1 + (49500-50000)*0.5 = -100 - 250 = -350
                assert!((notional - 28850.0).abs() < tol, "Day 2 notional");
                assert!((cash - 171700.0).abs() < tol, "Day 2 cash");
                assert!(
                    (portfolio.equity_curve.last().unwrap() - 200900.0).abs() < tol,
                    "Day 2 equity"
                );
                assert!((realized_pnl - 700.0).abs() < tol, "Day 2 realized");
                assert!((unrealized_pnl - (-350.0)).abs() < tol, "Day 2 unrealized");
                let btc = portfolio.positions.get("BTC").unwrap();
                let eth = portfolio.positions.get("ETH").unwrap();
                assert!((btc.peak_price - 51000.0).abs() < tol, "Day 2 BTC peak");
                assert!((eth.peak_price - 4200.0).abs() < tol, "Day 2 ETH peak");
                // Optionally, check unrealized PnL for each asset
                let btc_unrealized = (49500.0 - 50000.0) * 0.5;
                let eth_unrealized = (4100.0 - 4000.0) * 1.0;
                assert!(
                    (btc.unrealized_pnl.unwrap_or(0.0) - btc_unrealized).abs() < tol,
                    "Day 2 BTC unrealized"
                );
                assert!(
                    (eth.unrealized_pnl.unwrap_or(0.0) - eth_unrealized).abs() < tol,
                    "Day 2 ETH unrealized"
                );
            }
            _ => {}
        }
    }
    log::info!("final portfolio: {:?}", portfolio);
}
