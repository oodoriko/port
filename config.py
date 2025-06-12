from data.data import Benchmarks
from portfolio.constraints import ConstraintsConfig
from portfolio.portfolio import CapitalGrowthFrequency, PortfolioConfig
from strategies.strategy import StrategyTypes

####SET UP SOME DEFAULT CONFIGS####

##DEFAULT PORTFOLIO SETUP
DEFAULT_PORTFOLIO_SETUP = PortfolioConfig(
    initial_capital=100_000,
    initial_holdings={},
    new_capital_growth_amt=10000,
    capital_growth_freq=CapitalGrowthFrequency.MONTHLY.value,
)

##DEFAULT CONSTRAINTS
DEFAULT_CONSTRAINTS = ConstraintsConfig(
    long_only=True,
    cash_pct=0.0,
    max_long_count=0.3,
    max_short_count=0.3,
    max_buy_size=0.3,
)

DEFAULT_BENCHMARK = Benchmarks.SP500

##DEFAULT STRATEGY CONFIG
DEFAULT_STRATEGY_CONFIG = {
    StrategyTypes.MACD_CROSSOVER: True,
    StrategyTypes.RSI_CROSSOVER: True,
    StrategyTypes.BOLLINGER_BANDS: True,
    StrategyTypes.Z_SCORE_MEAN_REVERSION: True,
}

DEFAULT_GRID_SEARCH_PARAMS = [
    # going to be just strategy selection for now, maybe later can gs on strategy params like slow/fast period
    {StrategyTypes.MACD_CROSSOVER: True},
    {StrategyTypes.RSI_CROSSOVER: True},
    {StrategyTypes.BOLLINGER_BANDS: True},
    {StrategyTypes.Z_SCORE_MEAN_REVERSION: True},
    {StrategyTypes.MACD_CROSSOVER: True, StrategyTypes.BOLLINGER_BANDS: False},
    {StrategyTypes.RSI_CROSSOVER: True, StrategyTypes.Z_SCORE_MEAN_REVERSION: True},
    {
        StrategyTypes.MACD_CROSSOVER: True,
        StrategyTypes.RSI_CROSSOVER: True,
        StrategyTypes.BOLLINGER_BANDS: True,
        StrategyTypes.Z_SCORE_MEAN_REVERSION: True,
    },
]
