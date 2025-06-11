from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from constants import (
    DEFAULT_MAX_POSITION_SIZE,
    DEFAULT_MAX_TRADES_PER_DAY,
    DEFAULT_REBALANCE_THRESHOLD,
    MAX_MARKET_CAP_DEFAULT,
    MIN_MARKET_CAP_DEFAULT,
)
from data.data import Benchmarks, Countries, Sectors
from strategies.strategy import Strategies, Strategy


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
class PortfolioSetup:
    initial_capital: float = 100_000
    initial_holdings: Dict[str, float] = field(default_factory=dict)
    new_capital_growth_pct: float = 0.0
    new_capital_growth_amt: float = 10000
    capital_growth_freq: str = CapitalGrowthFrequency.MONTHLY.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial_capital": self.initial_capital,
            "initial_holdings": self.initial_holdings,
            "new_capital_growth_pct": self.new_capital_growth_pct,
            "new_capital_growth_amt": self.new_capital_growth_amt,
            "capital_growth_freq": self.capital_growth_freq,
        }


@dataclass
class StrategyConfig:
    triggers: List[Strategies] = field(default_factory=list)
    filter: List[Strategies] = field(default_factory=list)

    def to_strategies(self) -> List[Strategy]:
        return [
            Strategy.create(v, is_filter=k == "filter")
            for k, values in self.to_dict().items()
            for v in values
        ]

    def to_dict(self) -> Dict[str, list[Strategies]]:
        return {
            "triggers": self.triggers,
            "filter": self.filter,
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
    include_countries: List[Countries] = field(
        default_factory=lambda: [Countries.UNITED_STATES]
    )

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


########BACKTESTING CONFIGS########

# default configurations
DEFAULT_PORTFOLIO_SETUP = PortfolioSetup().to_dict()
SIMPLE_CONSTRAINTS = TradingConstraints().to_dict()
CONSTRAINTS_OPTIONS = AdvancedConstraints().to_dict()


@dataclass
class BacktestParams:
    scenario_name: str = "default_scenario_sp500_10yrs_no_short"
    initial_capital: float = 100_000
    start_date: str = "2022-01-01"
    end_date: str = "2025-06-01"
    interval: str = "B"  # Business days
    benchmark: str = Benchmarks.SP500.value

    setup: Dict[str, Any] = field(default_factory=lambda: DEFAULT_PORTFOLIO_SETUP)
    constraints: Optional[Dict[str, Any]] = field(
        default_factory=lambda: SIMPLE_CONSTRAINTS
    )
    strategies: List[Strategies] = field(
        default_factory=lambda: [Strategies.MACD_CROSSOVER]
    )

    def __post_init__(self):
        if self.constraints is None:
            self.constraints = SIMPLE_CONSTRAINTS

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return {
            "initial_capital": self.initial_capital,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "interval": self.interval,
            "strategies": self.strategies,
            "constraints": self.constraints if self.constraints else {},
            "benchmark": self.benchmark,
            "setup": self.setup,
            "scenario_name": self.scenario_name,
        }


DEFAULT_BACKTEST_PARAMS = BacktestParams().to_dict()
DEFAULT_STRATEGY_CONFIG = StrategyConfig(
    triggers=[
        Strategies.MACD_CROSSOVER,
        Strategies.BOLLINGER_BANDS,
        Strategies.Z_SCORE_MEAN_REVERSION,
        Strategies.RSI_CROSSOVER,
    ],
    filter=[],
)

DEFAULT_GRID_SEARCH_PARAMS = [
    StrategyConfig(triggers=[Strategies.MACD_CROSSOVER], filter=[]),
    StrategyConfig(triggers=[Strategies.RSI_CROSSOVER], filter=[]),
    StrategyConfig(triggers=[Strategies.BOLLINGER_BANDS], filter=[]),
    StrategyConfig(triggers=[Strategies.Z_SCORE_MEAN_REVERSION], filter=[]),
    StrategyConfig(
        triggers=[Strategies.MACD_CROSSOVER], filter=[Strategies.BOLLINGER_BANDS]
    ),
    StrategyConfig(
        triggers=[Strategies.RSI_CROSSOVER, Strategies.Z_SCORE_MEAN_REVERSION],
        filter=[],
    ),
    StrategyConfig(
        triggers=[
            Strategies.MACD_CROSSOVER,
            Strategies.BOLLINGER_BANDS,
            Strategies.Z_SCORE_MEAN_REVERSION,
            Strategies.RSI_CROSSOVER,
        ],
        filter=[],
    ),
]
