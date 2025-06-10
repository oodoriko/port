from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

START_DATE = "2014-01-01"
END_DATE = "2025-06-01"

# market cap constants (in USD)
MIN_MARKET_CAP_DEFAULT = 0
MAX_MARKET_CAP_DEFAULT = np.inf
MARKET_CAP_10M = 10_000_000
MARKET_CAP_1B = 1_000_000_000
MARKET_CAP_10B = 10_000_000_000
MARKET_CAP_100B = 100_000_000_000
MARKET_CAP_1T = 1_000_000_000_000

# trading constants
DEFAULT_MAX_POSITION_SIZE = 0.3
DEFAULT_MAX_TRADES_PER_DAY = 100
DEFAULT_REBALANCE_THRESHOLD = 0.05


class Sectors(Enum):
    """for yahoo finance"""

    TECHNOLOGY = "Technology"
    FINANCIAL_SERVICES = "Financial Services"
    CONSUMER_CYCLICAL = "Consumer Cyclical"
    COMMUNICATION_SERVICES = "Communication Services"
    HEALTHCARE = "Healthcare"
    INDUSTRIALS = "Industrials"
    CONSUMER_DEFENSIVE = "Consumer Defensive"
    ENERGY = "Energy"
    BASIC_MATERIALS = "Basic Materials"
    REAL_ESTATE = "Real Estate"
    UTILITIES = "Utilities"


class Countries(Enum):
    """for yahoo finance"""

    UNITED_STATES = "United States"
    CANADA = "Canada"
    UNITED_KINGDOM = "United Kingdom"
    JAPAN = "Japan"
    GERMANY = "Germany"
    FRANCE = "France"


class Benchmarks(Enum):
    """Supported benchmark indices."""

    SP500 = "sp500"
    NASDAQ = "nasdaq"
    DOW_JONES = "dowjones"


class StrategyTypes(Enum):
    """strategy classification types"""

    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    MEAN_REVERSION = "mean_reversion"


class Strategies(Enum):
    """available trading strategies, note a strategy belongs to a strategy type"""

    MACD_CROSSOVER = "macd_crossover"
    RSI_CROSSOVER = "rsi_crossover"
    BOLLINGER_BANDS = "bollinger_bands"
    Z_SCORE_MEAN_REVERSION = "z_score_mean_reversion"


class CapitalGrowthFrequency(Enum):
    DAILY = "D"
    WEEKLY = "W"
    MONTHLY = "M"
    QUARTERLY = "Q"
    YEARLY = "Y"


class AllocationMethod(Enum):
    EQUAL = "equal"
    MAX_MARKET_CAP = "max_market_cap"
    HIGHEST_VOLUME = "highest_volume"
    OPTIMIZER = "optimizer"


@dataclass
class InitialSetup:
    initial_capital: float = 100_000
    initial_holdings: Dict[str, float] = field(default_factory=dict)
    new_capital_growth_pct: float = 0.0
    new_capital_growth_amt: float = 10_000
    capital_growth_freq: str = CapitalGrowthFrequency.DAILY.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial_capital": self.initial_capital,
            "initial_holdings": self.initial_holdings,
            "new_capital_growth_pct": self.new_capital_growth_pct,
            "new_capital_growth_amt": self.new_capital_growth_amt,
            "capital_growth_freq": self.capital_growth_freq,
        }


@dataclass
class TradingConstraints:
    long_only: bool = True
    no_cash: bool = True
    max_long_count: float = DEFAULT_MAX_POSITION_SIZE
    max_short_count: float = DEFAULT_MAX_POSITION_SIZE
    max_buy_size: float = DEFAULT_MAX_POSITION_SIZE
    capital_allocation_method: str = AllocationMethod.EQUAL.value
    exclude_sectors: List[Sectors] = field(default_factory=list)
    min_market_cap: float = MIN_MARKET_CAP_DEFAULT
    max_market_cap: float = MAX_MARKET_CAP_DEFAULT
    include_countries: List[Countries] = field(default_factory=lambda: [Countries.UNITED_STATES])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return {
            "long_only": self.long_only,
            "no_cash": self.no_cash,
            "max_long_count": self.max_long_count,
            "max_short_count": self.max_short_count,
            "max_buy_size": self.max_buy_size,
            "capital_allocation_method": self.capital_allocation_method,
            "exclude_sectors": self.exclude_sectors,
            "min_market_cap": self.min_market_cap,
            "max_market_cap": self.max_market_cap,
            "include_countries": self.include_countries,
        }


@dataclass
class AdvancedConstraints:
    long_only: bool = False
    no_cash: bool = False
    max_cash: float = 0.1
    hold_cash: float = 0.0
    sector_exposure: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: {"TECH": {"min": 0.2, "max": 0.5}}
    )
    max_position_size: float = 1.0
    max_drawdown_limit: float = 0.20
    rebalance_threshold: float = DEFAULT_REBALANCE_THRESHOLD
    max_daily_trades: int = DEFAULT_MAX_TRADES_PER_DAY
    blackout_dates: List[str] = field(default_factory=list)
    default_position_size: float = 0.1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return {
            "long_only": self.long_only,
            "no_cash": self.no_cash,
            "max_cash": self.max_cash,
            "hold_cash": self.hold_cash,
            "sector_exposure": self.sector_exposure,
            "max_position_size": self.max_position_size,
            "max_drawdown_limit": self.max_drawdown_limit,
            "rebalance_threshold": self.rebalance_threshold,
            "max_daily_trades": self.max_daily_trades,
            "blackout_dates": self.blackout_dates,
            "default_position_size": self.default_position_size,
        }


@dataclass
class BacktestParams:
    initial_capital: float = 10_000
    start_date: str = "2022-01-01"
    end_date: str = END_DATE
    interval: str = "B"  # Business days
    strategies: List[Strategies] = field(
        default_factory=lambda: [
            Strategies.MACD_CROSSOVER,
            Strategies.RSI_CROSSOVER,
            Strategies.BOLLINGER_BANDS,
            Strategies.Z_SCORE_MEAN_REVERSION,
        ]
    )
    constraints: Optional[TradingConstraints] = None

    def __post_init__(self):
        if self.constraints is None:
            self.constraints = TradingConstraints()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return {
            "initial_capital": self.initial_capital,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "interval": self.interval,
            "strategies": self.strategies,
            "constraints": self.constraints.to_dict() if self.constraints else {},
        }


# default configurations
DEFAULT_PORTFOLIO_SETUP = InitialSetup().to_dict()
SIMPLE_CONSTRAINTS = TradingConstraints().to_dict()
CONSTRAINTS_OPTIONS = AdvancedConstraints().to_dict()
DEFAULT_BACKTEST_PARAMS = BacktestParams().to_dict()

# product attributes
DEFAULT_PRODUCT_ATTRIBUTES = ["sector", "industry", "marketCap", "country"]
