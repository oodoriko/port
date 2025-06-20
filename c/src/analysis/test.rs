mod tests {
    use crate::analysis::backtest::{backtest, backtest_result};
    use crate::core::params::{
        PortfolioConstraintParams, PortfolioParams, PositionConstraintParams,
    };
    use crate::trading::strategy::Strategy;
    use crate::utils::utils::create_sample_strategies;
    use chrono::TimeZone;
    use chrono::Utc;

    #[tokio::test]
    async fn test_backtest() {
        let tickers = vec!["BTC-USD".to_string(), "ETH-USD".to_string()];
        let start = Utc.with_ymd_and_hms(2025, 6, 17, 16, 0, 0).unwrap();
        let end = Utc.with_ymd_and_hms(2025, 6, 19, 17, 0, 0).unwrap();

        let strategies = create_sample_strategies();

        let portfolio = backtest(
            String::from("test_strategy"),
            String::from("test_portfolio"),
            start,
            end,
            tickers,
            strategies,
            PortfolioParams::default(),
            PortfolioConstraintParams::default(),
            vec![
                PositionConstraintParams::default(),
                PositionConstraintParams::default(),
            ],
            2,
            1,
        )
        .await
        .unwrap();

        // Print the backtest results
        backtest_result(portfolio);
    }

    #[tokio::test]
    async fn test_backtest2() {
        println!("=== MOCK DATA BACKTEST TEST ===");

        // Create mock price data for 10 days
        // Format: [day][ticker][ohlcv] where ohlcv = [open, high, low, close, volume]
        let mock_data = create_mock_price_data();
        let mock_timestamps: Vec<i64> = (0..12).map(|i| 1624464000 + i * 60 * 60 * 24).collect(); // Daily timestamps

        let strategies = create_sample_strategies();

        // Create strategy and portfolio manually
        let mut strategy = Strategy::new(
            "mock_test_strategy",
            "mock_test_portfolio",
            PortfolioParams::default(),
            PortfolioConstraintParams::default(),
            vec![
                PositionConstraintParams::default(),
                PositionConstraintParams::default(),
            ],
            &strategies,
        );

        let mut portfolio = strategy.create_portfolio();
        let mut constraint = strategy.create_constraints();
        constraint.set_cadence(60 * 60 * 24); // Daily cadence

        // Warm up with first 2 days
        let warm_up_price_data: Vec<Vec<Vec<f32>>> = mock_data.iter().take(2).cloned().collect();
        strategy.warm_up_signals(&warm_up_price_data);

        // Run backtest loop with mock data
        let mut exit = false;
        for (idx, &time) in mock_timestamps.iter().enumerate().skip(2) {
            if idx > 10 {
                break;
            }

            println!("\n\n========== MOCK idx: {} ==========", idx);
            println!("portfolio cash: {:?}", portfolio.cash_curve);
            println!("positions: {:?}", portfolio.positions);

            let mut available_cash = portfolio.cash_curve[portfolio.cash_curve.len() - 1];
            let mut total_cost = 0.0;
            let mut total_realized_pnl = 0.0;

            let close_prices: Vec<f32> = mock_data[idx - 1]
                .iter()
                .map(|asset_ohlcv| asset_ohlcv[3])
                .collect();
            let open_prices: Vec<f32> = mock_data[idx - 1]
                .iter()
                .map(|asset_ohlcv| asset_ohlcv[1])
                .collect();

            if exit {
                let mut liquidation_trades =
                    portfolio.trading_history[portfolio.trading_history.len() - 1].clone();
                portfolio.liquidation(&close_prices, &mut liquidation_trades, time as u64);
                break;
            }

            portfolio.pre_order_update(&mock_data[idx]);
            let (is_exit, risk_trades) = constraint.pre_order_check(
                &close_prices,
                &portfolio.positions,
                portfolio.equity_curve[portfolio.equity_curve.len() - 1],
                time as u64,
            );

            if is_exit {
                println!("bankruptcy!!!!!!!");
                exit = true;
                portfolio.post_order_update(
                    &close_prices,
                    &Vec::new(),
                    &risk_trades,
                    available_cash,
                    total_cost,
                    total_realized_pnl,
                );
                continue;
            }

            // Generate signals using previous day's data
            strategy.update_signals(mock_data[idx - 1].clone());
            let signals = strategy.generate_signals();
            let mut signals_adjusted = signals.clone();
            for trade in risk_trades.iter() {
                signals_adjusted[trade.ticker_id] = 0;
            }

            // Execute previous trades
            let mut prev_trades =
                portfolio.trading_history[portfolio.trading_history.len() - 2].clone();
            if prev_trades.len() > 0 {
                (available_cash, total_cost, total_realized_pnl) =
                    portfolio.execute_trades(&mut prev_trades, &open_prices, time as u64);
            }

            portfolio.update_capital(time);
            let mut trades = constraint.generate_trades(
                &signals_adjusted,
                &close_prices,
                portfolio.equity_curve[portfolio.equity_curve.len() - 1],
                available_cash,
                time as u64,
                &portfolio.positions,
            );
            trades.extend(risk_trades);

            portfolio.post_order_update(
                &close_prices,
                &prev_trades,
                &trades,
                available_cash,
                total_cost,
                total_realized_pnl,
            );

            // Comprehensive sanity check
            println!("=== MOCK SANITY CHECK idx {} ===", idx);
            println!("Cash curve: {:?}", portfolio.cash_curve);
            println!("Equity curve: {:?}", portfolio.equity_curve);
            println!("Notional curve: {:?}", portfolio.notional_curve);
            println!("Cost curve: {:?}", portfolio.cost_curve);
            println!("Realized PnL curve: {:?}", portfolio.realized_pnl_curve);
            println!("Unrealized PnL curve: {:?}", portfolio.unrealized_pnl_curve);
            println!("Holdings: {:?}", portfolio.holdings);
            println!("Executed trades (prev_trades): {:?}", prev_trades);
            println!("Next trades: {:?}", trades);
            println!("Available cash after execution: {}", available_cash);
            println!("Total cost this period: {}", total_cost);
            println!("Total realized PnL this period: {}", total_realized_pnl);

            // Critical assertions for backtest integrity
            let latest_cash = *portfolio.cash_curve.last().unwrap();
            let latest_notional = *portfolio.notional_curve.last().unwrap();
            let latest_equity = *portfolio.equity_curve.last().unwrap();

            println!(
                "VERIFICATION: cash + notional = {} + {} = {}, equity = {}",
                latest_cash,
                latest_notional,
                latest_cash + latest_notional,
                latest_equity
            );

            // ASSERTION 1: Cash + Notional must equal Equity (fundamental accounting balance)
            assert!(
                (latest_cash + latest_notional - latest_equity).abs() < 0.01,
                "ACCOUNTING MISMATCH at idx {}: cash({}) + notional({}) = {} != equity({})",
                idx,
                latest_cash,
                latest_notional,
                latest_cash + latest_notional,
                latest_equity
            );

            // ASSERTION 2: Cash must never be negative
            assert!(
                latest_cash >= 0.0,
                "NEGATIVE CASH at idx {}: cash = {}",
                idx,
                latest_cash
            );

            // ASSERTION 3: Position quantities must never be negative
            for (pos_idx, position) in portfolio.positions.iter().enumerate() {
                if let Some(pos) = position {
                    assert!(
                        pos.quantity >= 0.0,
                        "NEGATIVE POSITION QUANTITY at idx {} for ticker {}: quantity = {}",
                        idx,
                        pos_idx,
                        pos.quantity
                    );
                }
            }

            // ASSERTION 4: Holdings must match position quantities
            for (pos_idx, position) in portfolio.positions.iter().enumerate() {
                let holding = portfolio.holdings.get(pos_idx).unwrap_or(&0.0);
                if let Some(pos) = position {
                    assert!(
                        (pos.quantity - holding).abs() < 0.0001,
                        "POSITION-HOLDING MISMATCH at idx {} for ticker {}: position.quantity({}) != holding({})",
                        idx, pos_idx, pos.quantity, holding
                    );
                } else {
                    assert!(
                        *holding == 0.0,
                        "NON-ZERO HOLDING WITHOUT POSITION at idx {} for ticker {}: holding = {}",
                        idx,
                        pos_idx,
                        holding
                    );
                }
            }

            // ASSERTION 5: Available cash should match latest cash (after trade execution)
            assert!(
                (available_cash - latest_cash).abs() < 0.01,
                "AVAILABLE CASH MISMATCH at idx {}: available_cash({}) != latest_cash({})",
                idx,
                available_cash,
                latest_cash
            );

            println!("✅ All assertions passed for idx {}", idx);
            println!("=========================");
        }

        // FINAL PERFORMANCE ASSERTIONS - Extract values before moving portfolio
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
        let peak_notional = portfolio.peak_notional;

        // Print final results
        backtest_result(portfolio);

        println!("\n=== FINAL PERFORMANCE ASSERTIONS ===");

        // Assert initial value
        assert!(
            (initial_value - 100000.0).abs() < 0.01,
            "Initial value mismatch: expected 100000.00, got {:.2}",
            initial_value
        );

        // Assert final value
        assert!(
            (final_value - 91372.45).abs() < 0.01,
            "Final value mismatch: expected 91372.45, got {:.2}",
            final_value
        );

        // Assert total return
        assert!(
            (total_return - (-8.63)).abs() < 0.01,
            "Total return mismatch: expected -8.63%, got {:.2}%",
            total_return
        );

        // Assert max value
        assert!(
            (max_equity - 100000.0).abs() < 0.01,
            "Max value mismatch: expected 100000.00, got {:.2}",
            max_equity
        );

        // Assert min value
        assert!(
            (min_equity - 88902.59).abs() < 0.01,
            "Min value mismatch: expected 88902.59, got {:.2}",
            min_equity
        );

        // Assert peak notional
        assert!(
            (peak_notional - 100000.0).abs() < 0.01,
            "Peak notional mismatch: expected 100000.00, got {:.2}",
            peak_notional
        );

        println!("✅ All final performance assertions passed!");
        println!("  Initial Value: ${:.2} ✓", initial_value);
        println!("  Final Value:   ${:.2} ✓", final_value);
        println!("  Total Return:  {:.2}% ✓", total_return);
        println!("  Max Value:     ${:.2} ✓", max_equity);
        println!("  Min Value:     ${:.2} ✓", min_equity);
        println!("  Peak Notional: ${:.2} ✓", peak_notional);

        println!("=== END MOCK DATA BACKTEST TEST ===");
    }

    fn create_mock_price_data() -> Vec<Vec<Vec<f32>>> {
        // Create 12 days of mock OHLCV data for 2 tickers (BTC-USD, ETH-USD)
        // Each day contains [ticker][ohlcv] where ohlcv = [open, high, low, close, volume]

        vec![
            // Day 0
            vec![
                vec![50000.0, 51000.0, 49500.0, 50500.0, 1000.0], // BTC-USD
                vec![3000.0, 3100.0, 2950.0, 3050.0, 2000.0],     // ETH-USD
            ],
            // Day 1
            vec![
                vec![50500.0, 52000.0, 50000.0, 51500.0, 1100.0], // BTC-USD
                vec![3050.0, 3200.0, 3000.0, 3150.0, 2100.0],     // ETH-USD
            ],
            // Day 2 - Market starts trending up
            vec![
                vec![51500.0, 53000.0, 51000.0, 52800.0, 1200.0], // BTC-USD
                vec![3150.0, 3300.0, 3100.0, 3250.0, 2200.0],     // ETH-USD
            ],
            // Day 3 - Continued uptrend
            vec![
                vec![52800.0, 54500.0, 52500.0, 54200.0, 1300.0], // BTC-USD
                vec![3250.0, 3400.0, 3200.0, 3380.0, 2300.0],     // ETH-USD
            ],
            // Day 4 - Peak and reversal starts
            vec![
                vec![54200.0, 55000.0, 53000.0, 53500.0, 1400.0], // BTC-USD
                vec![3380.0, 3450.0, 3200.0, 3300.0, 2400.0],     // ETH-USD
            ],
            // Day 5 - Sharp decline (trigger stop loss)
            vec![
                vec![53500.0, 53500.0, 48000.0, 48500.0, 1500.0], // BTC-USD - Big drop
                vec![3300.0, 3300.0, 2800.0, 2850.0, 2500.0],     // ETH-USD - Big drop
            ],
            // Day 6 - Bounce back slightly
            vec![
                vec![48500.0, 50000.0, 47500.0, 49200.0, 1600.0], // BTC-USD
                vec![2850.0, 2950.0, 2750.0, 2900.0, 2600.0],     // ETH-USD
            ],
            // Day 7 - Continued recovery
            vec![
                vec![49200.0, 51000.0, 48800.0, 50800.0, 1700.0], // BTC-USD
                vec![2900.0, 3050.0, 2850.0, 3000.0, 2700.0],     // ETH-USD
            ],
            // Day 8 - Sideways movement
            vec![
                vec![50800.0, 51500.0, 50200.0, 50900.0, 1800.0], // BTC-USD
                vec![3000.0, 3100.0, 2950.0, 3020.0, 2800.0],     // ETH-USD
            ],
            // Day 9 - Another small dip
            vec![
                vec![50900.0, 51000.0, 49500.0, 49800.0, 1900.0], // BTC-USD
                vec![3020.0, 3050.0, 2900.0, 2950.0, 2900.0],     // ETH-USD
            ],
            // Day 10 - Recovery
            vec![
                vec![49800.0, 52000.0, 49500.0, 51200.0, 2000.0], // BTC-USD
                vec![2950.0, 3150.0, 2900.0, 3080.0, 3000.0],     // ETH-USD
            ],
            // Day 11 - Final day
            vec![
                vec![51200.0, 52500.0, 50800.0, 51800.0, 2100.0], // BTC-USD
                vec![3080.0, 3200.0, 3000.0, 3120.0, 3100.0],     // ETH-USD
            ],
        ]
    }
}
