import numpy as np
import pandas as pd


class Constraints:
    """dummy dumb dumb bad"""

    def __init__(self, constraints: dict):
        self.constraints = constraints
        self.product_data = None
        self.price = None
        self.volume = None

    def set_product_data(self, product_data: pd.DataFrame):
        self.product_data = product_data

    def set_price(self, price: pd.DataFrame):
        self.price = price

    def set_volume(self, volume: pd.DataFrame):
        self.volume = volume

    def list_constraints(self) -> dict:
        return self.constraints

    def evaluate_trades(
        self, trades: list[int], positions_size: int, max_holdings: int
    ) -> bool:
        if self.constraints is None or len(self.constraints) == 0:
            return True
        if trades is None or len(trades) == 0:
            return True
        value, count = np.unique(trades, return_counts=True)

        max_short_count = max(
            max_holdings / 2, self.constraints["max_short_count"] * positions_size
        )
        max_long_count = max(
            max_holdings / 2, self.constraints["max_long_count"] * positions_size
        )

        short_count_idx = np.where(value == -1)[0]
        if len(short_count_idx) > 0:
            short_count = count[short_count_idx[0]]
            if short_count > max_short_count:
                print(
                    f"Short trade amount {short_count} too large violates max trade constraint"
                )
                return False
        long_count_idx = np.where(value == 1)[0]
        if len(long_count_idx) > 0:
            long_count = count[long_count_idx[0]]
            if long_count > max_long_count:
                print(
                    f"Long trade amount {long_count} too large violates max trade constraint"
                )
                return False
        return True

    def allocate_capital_to_buy(
        self,
        date,
        capital: float,
        trading_plan: dict[str, int],
        new_holdings: dict[str, int],
        shares_to_be_traded: dict[str, int],
        executed_trading_plan: dict[str, int],
    ) -> float:
        available_capital = self._calculate_available_capital(capital)
        to_buy = self._get_tickers_to_buy(trading_plan)

        if not to_buy:
            return available_capital

        prices = self.price.loc[date, to_buy]
        allocation_method = self.constraints.get("capital_allocation_method", "equal")

        return self._execute_allocation_strategy(
            allocation_method,
            available_capital,
            to_buy,
            prices,
            date,
            new_holdings,
            shares_to_be_traded,
            executed_trading_plan,
        )

    def _calculate_available_capital(self, capital: float) -> float:
        if self.constraints.get("no_cash", False):
            capital *= 1 - self.constraints.get("hold_cash", 0)
        return capital

    def _get_tickers_to_buy(self, trading_plan: dict[str, int]) -> list[str]:
        return [ticker for ticker, signal in trading_plan.items() if signal == 1]

    def _execute_allocation_strategy(
        self,
        method: str,
        capital: float,
        tickers: list[str],
        prices: pd.Series,
        date,
        new_holdings: dict[str, int],
        shares_to_be_traded: dict[str, int],
        executed_trading_plan: dict[str, int],
    ) -> float:
        """Execute the appropriate capital allocation strategy."""
        if method == "equal":
            return self._allocate_equal_weights(
                capital, tickers, prices, new_holdings, shares_to_be_traded
            )
        elif method == "max_market_cap":
            priority_list = self._get_market_cap_priority(tickers)
            return self._allocate_by_priority(
                capital,
                priority_list,
                prices,
                new_holdings,
                shares_to_be_traded,
                executed_trading_plan,
            )
        elif method == "highest_volume":
            priority_list = self._get_volume_priority(date, tickers)
            return self._allocate_by_priority(
                capital,
                priority_list,
                prices,
                new_holdings,
                shares_to_be_traded,
                executed_trading_plan,
            )
        elif method == "optimizer":
            raise NotImplementedError("Optimizer not implemented")
        else:
            raise ValueError(f"Invalid capital allocation method: {method}")

    def _allocate_equal_weights(
        self,
        capital: float,
        tickers: list[str],
        prices: pd.Series,
        new_holdings: dict[str, int],
        shares_to_be_traded: dict[str, int],
    ) -> float:
        """Allocate capital equally across all tickers."""
        total_price = np.sum(prices)
        amount_per_ticker = capital / total_price
        remaining_capital = capital

        for ticker in tickers:
            shares = amount_per_ticker / prices[ticker]
            shares_to_be_traded[ticker] = shares
            new_holdings[ticker] = new_holdings.get(ticker, 0) + shares
            remaining_capital -= shares * prices[ticker]

        return remaining_capital

    def _allocate_by_priority(
        self,
        capital: float,
        priority_list: list[str],
        prices: pd.Series,
        new_holdings: dict[str, int],
        shares_to_be_traded: dict[str, int],
        executed_trading_plan: dict[str, int],
    ) -> float:
        """Allocate capital based on priority order with max buy size constraints."""
        remaining_capital = capital
        max_buy_size = self.constraints.get("max_buy_size", 1) * capital

        for ticker in priority_list:
            if remaining_capital <= 0:
                executed_trading_plan[ticker] = 0
                continue

            max_affordable_shares = (
                min(remaining_capital, max_buy_size) / prices[ticker]
            )
            shares_to_be_traded[ticker] = max_affordable_shares
            new_holdings[ticker] = new_holdings.get(ticker, 0) + max_affordable_shares
            remaining_capital -= max_affordable_shares * prices[ticker]

        # Allocate any remaining capital to the top priority ticker
        if remaining_capital > 0 and priority_list:
            top_ticker = priority_list[0]
            additional_shares = remaining_capital / prices[top_ticker]
            shares_to_be_traded[top_ticker] = (
                shares_to_be_traded.get(top_ticker) + additional_shares
            )
            new_holdings[top_ticker] = new_holdings.get(top_ticker) + additional_shares
            remaining_capital = 0

        return remaining_capital

    def _get_market_cap_priority(self, tickers: list[str]) -> list[str]:
        if self.product_data is None:
            raise ValueError("Product data not set. Call set_product_data() first.")

        return (
            self.product_data[self.product_data.ticker.isin(tickers)]
            .sort_values(by="marketCap", ascending=False)
            .ticker.tolist()
        )

    def _get_volume_priority(self, date, tickers: list[str]) -> list[str]:
        if self.volume is None:
            raise ValueError("Volume data not set. Call set_volume() first.")

        volume = self.volume.loc[date, tickers]
        return volume.sort_values(ascending=False).index.tolist()
