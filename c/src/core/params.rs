use serde::{Deserialize, Serialize};

// Shared SignalParams enum for all signals
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SignalParams {
    EmaRsiMacd {
        ema_fast: usize,
        ema_medium: usize,
        ema_slow: usize,
        rsi_period: usize,
        initial_close: Option<f32>,
        rsi_ob: f32,
        rsi_os: f32,
        rsi_bull_div: f32,
        macd_fast: usize,
        macd_slow: usize,
        macd_signal: usize,
    },
    BbRsiOversold {
        name: String,
        std_dev: f32,
        initial_close: Option<f32>,
        rsi_period: usize,
        rsi_ob: f32,
        rsi_os: f32,
        rsi_bull_div: f32,
    },
    BbRsiOverbought {
        name: String,
        std_dev: f32,
        initial_close: Option<f32>,
        rsi_period: usize,
        rsi_ob: f32,
        rsi_os: f32,
        rsi_bull_div: f32,
    },
    PatternRsiMacd {
        name: String,
        resistance_threshold: f32,
        support_threshold: f32,
        initial_high: Option<f32>,
        initial_low: Option<f32>,
        initial_close: Option<f32>,
        rsi_period: usize,
        rsi_ob: f32,
        rsi_os: f32,
        rsi_bull_div: f32,
        macd_fast: usize,
        macd_slow: usize,
        macd_signal: usize,
    },
    TripleEmaPatternMacdRsi {
        name: String,
        ema_fast: usize,
        ema_medium: usize,
        ema_slow: usize,
        resistance_threshold: f32,
        support_threshold: f32,
        initial_high: Option<f32>,
        initial_low: Option<f32>,
        initial_close: Option<f32>,
        macd_fast: usize,
        macd_slow: usize,
        macd_signal: usize,
        rsi_period: usize,
        rsi_ob: f32,
        rsi_os: f32,
        rsi_bull_div: f32,
    },
    BbSqueezeBreakout {
        name: String,
        std_dev: f32,
        initial_close: Option<f32>,
        macd_fast: usize,
        macd_slow: usize,
        macd_signal: usize,
    },
    RsiOversoldReversal {
        name: String,
        rsi_period: usize,
        initial_close: Option<f32>,
        rsi_ob: f32,
        rsi_os: f32,
        rsi_bull_div: f32,
        ema_fast: usize,
        ema_medium: usize,
        ema_slow: usize,
    },
    SupportBounce {
        name: String,
        resistance_threshold: f32,
        support_threshold: f32,
        initial_high: Option<f32>,
        initial_low: Option<f32>,
        initial_close: Option<f32>,
        macd_fast: usize,
        macd_slow: usize,
        macd_signal: usize,
    },
    UptrendPattern {
        name: String,
        ema_fast: usize,
        ema_medium: usize,
        ema_slow: usize,
        resistance_threshold: f32,
        support_threshold: f32,
        initial_high: Option<f32>,
        initial_low: Option<f32>,
        initial_close: Option<f32>,
        rsi_period: usize,
        rsi_ob: f32,
        rsi_os: f32,
        rsi_bull_div: f32,
    },
    StochOversold {
        name: String,
        initial_high: Option<f32>,
        initial_low: Option<f32>,
        initial_close: Option<f32>,
        ema_fast_period: usize,
        ema_slow_period: usize,
        oversold: f32,
    },
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PositionConstraintParams {
    pub max_position_size_pct: f32,
    pub min_trade_size_pct: f32,
    pub min_holding_candle: u64,
    pub trailing_stop_loss_pct: f32,
    pub trailing_stop_update_threshold_pct: f32,
    pub take_profit_pct: f32,
    pub risk_per_trade_pct: f32,
    pub sell_fraction: f32,
    pub cool_down_period: u64,
}

impl Default for PositionConstraintParams {
    fn default() -> Self {
        Self {
            max_position_size_pct: 1.0,
            min_trade_size_pct: 0.05,
            min_holding_candle: 15,
            trailing_stop_loss_pct: 0.05,
            trailing_stop_update_threshold_pct: 0.02,
            take_profit_pct: 0.2,
            risk_per_trade_pct: 0.05,
            sell_fraction: 0.5,
            cool_down_period: 0,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PortfolioConstraintParams {
    pub rebalance_threshold_pct: f32,
    pub min_cash_pct: f32,
    pub max_drawdown_pct: f32,
}

impl Default for PortfolioConstraintParams {
    fn default() -> Self {
        Self {
            rebalance_threshold_pct: 0.05,
            min_cash_pct: 0.1,
            max_drawdown_pct: 0.2,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PortfolioParams {
    pub initial_cash: f32,
    pub capital_growth_pct: f32,
    pub capital_growth_amount: f32,
    pub capital_growth_frequency: Frequency,
}

impl Default for PortfolioParams {
    fn default() -> Self {
        Self {
            initial_cash: 100000.0,
            capital_growth_pct: 0.05,
            capital_growth_amount: 10000.0,
            capital_growth_frequency: Frequency::Monthly,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Frequency {
    Daily,
    Weekly,
    Monthly,
    Quarterly,
    Yearly,
}
