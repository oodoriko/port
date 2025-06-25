use crate::analysis::backtest::{backtest, backtest_result};
use crate::core::params::{PortfolioConstraintParams, PortfolioParams, PositionConstraintParams};
use crate::utils::utils::create_sample_strategies;
use chrono::TimeZone;
use chrono::Utc;

#[tokio::test]
async fn test_backtest() {
    let tickers = vec!["BTC-USD".to_string()];
    let start = Utc.with_ymd_and_hms(2025, 2, 1, 16, 0, 0).unwrap();
    let end = Utc.with_ymd_and_hms(2025, 4, 1, 17, 0, 0).unwrap();

    let strategies = create_sample_strategies();

    let result = backtest(
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
            // PositionConstraintParams::default(),
        ],
        50,
        1,
        false,
    )
    .await
    .unwrap();

    // Print the backtest results
    backtest_result(
        &result.portfolio,
        &result.executed_trades_by_date,
        result.exited_early,
        &result.trades_type_count,
    );
}
