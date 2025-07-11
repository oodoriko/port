// SignalParams must match the Rust enum structure exactly
export type SignalParams =
  | {
      EmaRsiMacd: {
        ema_fast: number;
        ema_medium: number;
        ema_slow: number;
        rsi_period: number;
        initial_close?: number | null;
        rsi_ob: number;
        rsi_os: number;
        rsi_bull_div: number;
        macd_fast: number;
        macd_slow: number;
        macd_signal: number;
      };
    }
  | {
      BbRsiOversold: {
        name: string;
        std_dev: number;
        initial_close?: number | null;
        rsi_period: number;
        rsi_ob: number;
        rsi_os: number;
        rsi_bull_div: number;
      };
    }
  | {
      BbRsiOverbought: {
        name: string;
        std_dev: number;
        initial_close?: number | null;
        rsi_period: number;
        rsi_ob: number;
        rsi_os: number;
        rsi_bull_div: number;
      };
    }
  | {
      PatternRsiMacd: {
        name: string;
        resistance_threshold: number;
        support_threshold: number;
        initial_high?: number | null;
        initial_low?: number | null;
        initial_close?: number | null;
        rsi_period: number;
        rsi_ob: number;
        rsi_os: number;
        rsi_bull_div: number;
        macd_fast: number;
        macd_slow: number;
        macd_signal: number;
      };
    }
  | {
      TripleEmaPatternMacdRsi: {
        name: string;
        ema_fast: number;
        ema_medium: number;
        ema_slow: number;
        resistance_threshold: number;
        support_threshold: number;
        initial_high?: number | null;
        initial_low?: number | null;
        initial_close?: number | null;
        macd_fast: number;
        macd_slow: number;
        macd_signal: number;
        rsi_period: number;
        rsi_ob: number;
        rsi_os: number;
        rsi_bull_div: number;
      };
    }
  | {
      BbSqueezeBreakout: {
        name: string;
        std_dev: number;
        initial_close?: number | null;
        macd_fast: number;
        macd_slow: number;
        macd_signal: number;
      };
    }
  | {
      RsiOversoldReversal: {
        name: string;
        rsi_period: number;
        initial_close?: number | null;
        rsi_ob: number;
        rsi_os: number;
        rsi_bull_div: number;
        ema_fast: number;
        ema_medium: number;
        ema_slow: number;
      };
    }
  | {
      SupportBounce: {
        name: string;
        resistance_threshold: number;
        support_threshold: number;
        initial_high?: number | null;
        initial_low?: number | null;
        initial_close?: number | null;
        macd_fast: number;
        macd_slow: number;
        macd_signal: number;
      };
    }
  | {
      UptrendPattern: {
        name: string;
        ema_fast: number;
        ema_medium: number;
        ema_slow: number;
        resistance_threshold: number;
        support_threshold: number;
        initial_high?: number | null;
        initial_low?: number | null;
        initial_close?: number | null;
        rsi_period: number;
        rsi_ob: number;
        rsi_os: number;
        rsi_bull_div: number;
      };
    }
  | {
      StochOversold: {
        name: string;
        initial_high?: number | null;
        initial_low?: number | null;
        initial_close?: number | null;
        ema_fast_period: number;
        ema_slow_period: number;
        oversold: number;
      };
    };
// Add other variants as needed

export interface PortfolioParams {
  initial_cash: number;
  capital_growth_pct: number;
  capital_growth_amount: number;
  capital_growth_frequency:
    | "Daily"
    | "Weekly"
    | "Monthly"
    | "Quarterly"
    | "Yearly";
}

export interface PortfolioConstraintParams {
  rebalance_threshold_pct: number;
  min_cash_pct: number;
  max_drawdown_pct: number;
}

export interface PositionConstraintParams {
  max_position_size_pct: number;
  min_trade_size_pct: number;
  min_holding_candle: number;
  trailing_stop_loss_pct: number;
  trailing_stop_update_threshold_pct: number;
  take_profit_pct: number;
  risk_per_trade_pct: number;
  sell_fraction: number;
  cool_down_period: number;
}

export interface BacktestParams {
  backtest_id: string;
  strategy_name: string;
  portfolio_name: string;
  start: string; // ISO string date
  end: string; // ISO string date
  tickers: string[];
  strategies: SignalParams[][];
  portfolio_params: PortfolioParams;
  portfolio_constraints_params: PortfolioConstraintParams;
  position_constraints_params: PositionConstraintParams[];
  warm_up_period: number;
  cadence: number; // in minutes
}

export interface BacktestResult {
  backtest_id: string;
  portfolio_name: string;
  initial_value: number;
  final_value: number;
  total_return: number;
  max_value: number;
  min_value: number;
  peak_equity: number;
  equity_curve: number[];
  cash_curve: number[];
  notional_curve: number[];
  cost_curve: number[];
  realized_pnl_curve: number[];
  unrealized_pnl_curve: number[];
  timestamps: number[];
  trade_timestamps: number[];
  total_records: number;
  tickers: string[];
  key_metrics: KeyMetrics;
  risk_free_rate: number;
  trade_type_count?: {
    executed: number;
    failed_insufficient_cash: number;
    failed_short_sell_prohibited: number;
    failed_cool_down_period: number;
    rejected_holding_period_too_short: number;
    rejected_cool_down_after_loss: number;
    rejected_trade_size_too_small: number;
    rejected_short_sell_prohibited: number;
  };
}

export interface KeyMetrics {
  // Portfolio level metrics
  status: string;
  portfolio_name: string;
  num_trades: number;
  duration: number; // Duration in years

  // Overview
  market_value: number;
  peak_equity: number;
  cash_injection: number;
  net_realized_pnl: number;
  composition: number[];

  // Return metrics
  gross_return: number;
  net_return: number;
  annualized_return: number;
  win_rate: number;
  profit_factor: number;

  // Contribution metrics
  cash_utilization_ratio: number;

  // Risk metrics
  max_drawdown: number;
  max_drawdown_duration: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number;

  // Position metrics
  position_metrics: PositionMetrics[];
  risk_free_rate: number;
}

export interface PositionMetrics {
  status: string;
  asset_name: number;
  num_trades: number;

  // Overview
  realized_pnl_net: number;
  unrealized_pnl_net: number;
  alpha: number;
  beta: number;

  // Return metrics
  gross_return: number;
  net_return: number;
  annualized_return: number;
  win_rate: number;
  profit_factor: number;

  // Contribution metrics
  take_profit_gain_pct: number;
  take_profit_loss_pct: number;
  stop_loss_gain_pct: number;
  stop_loss_loss_pct: number;
  signal_sell_gain_pct: number;
  signal_sell_loss_pct: number;
  liquidation_gain_pct: number;
  liquidation_loss_pct: number;

  // Trade metrics
  take_profit_trades_pct: number;
  stop_loss_trades_pct: number;
  signal_sell_trades_pct: number;
  liquidation_trades_pct: number;
  sell_pct: number;
  buy_pct: number;

  net_position: number[];
}

import { DateTime } from "luxon";
import { v4 as uuidv4 } from "uuid";

// Default values for form initialization
export const defaultBacktestParams: BacktestParams = {
  backtest_id: uuidv4(),
  strategy_name: "A Strategy",
  portfolio_name: "A Portfolio",
  start: DateTime.now().minus({ days: 60 }).toFormat("yyyy-MM-dd"),
  end: DateTime.now().minus({ days: 1 }).toFormat("yyyy-MM-dd"),
  tickers: [], // Keep empty - user should select their own assets
  strategies: [], // Keep empty - strategies come from asset configuration
  portfolio_params: {
    initial_cash: 100000, // Reasonable default
    capital_growth_pct: 0,
    capital_growth_amount: 1000,
    capital_growth_frequency: "Weekly",
  },
  portfolio_constraints_params: {
    rebalance_threshold_pct: 5, // 5% default
    min_cash_pct: 10, // 10% default (was 0.1)
    max_drawdown_pct: 20, // 20% default (was 0.2)
  },
  position_constraints_params: [], // Keep empty - comes from asset configuration
  warm_up_period: 50, // Reasonable default for indicator warm-up
  cadence: 1, // 15 minutes default
};
