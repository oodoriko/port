import type { BacktestParams, BacktestResult } from "../types/backtest";

// API configuration
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8080";

export async function runBacktest(
  params: BacktestParams
): Promise<BacktestResult> {
  const response = await fetch(`${API_BASE_URL}/api/backtest`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.message || `HTTP error! status: ${response.status}`
    );
  }

  return response.json();
}

// For testing - sends empty params to backend
export async function testBacktest(): Promise<BacktestResult> {
  const emptyParams: BacktestParams = {
    strategy_name: "",
    portfolio_name: "",
    start: "",
    end: "",
    strategies: {},
    portfolio_params: {
      initial_cash: 0,
    },
    portfolio_constraints_params: {
      max_position_size: 0,
      max_portfolio_size: 0,
    },
    position_constraints_params: [],
    warm_up_period: 0,
    cadence: 0,
  };

  return runBacktest(emptyParams);
}
