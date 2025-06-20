import { DateTime } from "luxon";

// SignalParams must match the Rust enum structure exactly
export type SignalParams =
  | {
      EmaRsiMacd: {
        ema_fast: number;
        ema_medium: number;
        ema_slow: number;
        rsi_period: number;
        initial_close: number;
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
        initial_close: number;
        rsi_period: number;
        rsi_ob: number;
        rsi_os: number;
        rsi_bull_div: number;
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
}

export interface BacktestParams {
  strategy_name: string;
  portfolio_name: string;
  start: string; // ISO string date
  end: string; // ISO string date
  strategies: Record<string, SignalParams[]>;
  portfolio_params: PortfolioParams;
  portfolio_constraints_params: PortfolioConstraintParams;
  position_constraints_params: PositionConstraintParams[];
  warm_up_period: number;
  cadence: number; // in minutes
}

export interface BacktestResult {
  portfolio_name: string;
  initial_value: number;
  final_value: number;
  total_return: number;
  max_value: number;
  min_value: number;
  peak_notional: number;
  equity_curve: number[];
  cash_curve: number[];
  notional_curve: number[];
  cost_curve: number[];
  realized_pnl_curve: number[];
  unrealized_pnl_curve: number[];
  total_records: number;
}

// Mock strategies configuration - ready to use without manual input
const mockStrategies = {
  "BTC-USD": [
    {
      EmaRsiMacd: {
        ema_fast: 12,
        ema_medium: 26,
        ema_slow: 50,
        rsi_period: 14,
        initial_close: 50000.0,
        rsi_ob: 70.0,
        rsi_os: 30.0,
        rsi_bull_div: 40.0,
        macd_fast: 12,
        macd_slow: 26,
        macd_signal: 9,
      },
    },
  ],
  "ETH-USD": [
    {
      EmaRsiMacd: {
        ema_fast: 12,
        ema_medium: 26,
        ema_slow: 50,
        rsi_period: 14,
        initial_close: 3000.0,
        rsi_ob: 70.0,
        rsi_os: 30.0,
        rsi_bull_div: 40.0,
        macd_fast: 12,
        macd_slow: 26,
        macd_signal: 9,
      },
    },
  ],
};

// Default values for form initialization
export const defaultBacktestParams: BacktestParams = {
  strategy_name: "Sample Momentum Strategy",
  portfolio_name: "Crypto Momentum Portfolio",
  start: DateTime.now().minus({ days: 60 }).toFormat("yyyy-MM-dd"),
  end: DateTime.now().minus({ days: 1 }).toFormat("yyyy-MM-dd"),
  strategies: mockStrategies,
  portfolio_params: {
    initial_cash: 100000,
    capital_growth_pct: 0.05,
    capital_growth_amount: 10000,
    capital_growth_frequency: "Monthly",
  },
  portfolio_constraints_params: {
    rebalance_threshold_pct: 0.05,
    min_cash_pct: 0.1,
    max_drawdown_pct: 0.2,
  },
  position_constraints_params: [
    {
      max_position_size_pct: 1.0,
      min_trade_size_pct: 0.05,
      min_holding_candle: 15,
      trailing_stop_loss_pct: 0.05,
      trailing_stop_update_threshold_pct: 0.02,
      take_profit_pct: 0.2,
      risk_per_trade_pct: 0.05,
      sell_fraction: 0.5,
    },
  ],
  warm_up_period: 10,
  cadence: 1,
};
