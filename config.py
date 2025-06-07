from enum import Enum

import numpy as np

START_DATE = "2014-01-01"
END_DATE = "2025-06-01"


class YF_SECTORS(Enum):
    Technology = "Technology"
    FinancialServices = "Financial Services"
    ConsumerCyclical = "Consumer Cyclical"
    CommunicationServices = "Communication Services"
    Healthcare = "Healthcare"
    Industrials = "Industrials"
    ConsumerDefensive = "Consumer Defensive"
    Energy = "Energy"
    BasicMaterials = "Basic Materials"
    RealEstate = "Real Estate"
    Utilities = "Utilities"


class YF_COUNTRIES(Enum):
    UnitedStates = "United States"
    Canada = "Canada"
    UnitedKingdom = "United Kingdom"
    Japan = "Japan"
    Germany = "Germany"
    France = "France"


class Benchmarks(Enum):
    SP500 = "sp500"
    NASDAQ = "nasdaq"
    DOWJONES = "dowjones"


class Strategies(Enum):
    MACD_CROSSOVER = "macd_crossover"
    RSI_CROSSOVER = "rsi_crossover"
    BOLLINGER_BANDS = "bollinger_bands"
    Z_SCORE_MEAN_REVERSION = "z_score_mean_reversion"


class StrategyTypes(Enum):
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    MEAN_REVERSION = "mean_reversion"


INITIAL_SETUP = {  # no holdings scenario for now!
    "initial_capital": 100000,
    "initial_holdings": [],
    "transaction_cost": 0.001,
    ## to filter benchmark tickers to get the watch list for trading
    "exclude_sectors": [],
    "min_market_cap": 0,  # $10M
    "max_market_cap": np.inf,  # $10T, incredible we have companies > 1T now
    "include_countries": [YF_COUNTRIES.UnitedStates],
    "allow_short": False,
}
# may be i need target as well... for weights and exposure -> nvm
DEFAULT_CONSTRAINTS = {
    "long_only": False,
    "no_cash": False,
    "max_cash": 0.1,
    "sector_exposure": {"TECH": {"min": 0.2, "max": 0.5}},
    "max_position_size": 1.0,
    "max_drawdown_limit": 0.20,
    "rebalance_threshold": 0.05,
    "transaction_cost": 0.001,
    "max_daily_trades": 100,
    "blackout_dates": [],  # do not allow trading on these dates e.g. covids, liberation day etc.
    "default_position_size": 0.1,
}

DEFAULT_PRODUCT_ATTRIBUTES = ["sector", "industry", "marketCap", "country"]


DEFAULT_BACKTEST_PARAMS = {
    "initial_capital": 100000,
    "start_date": "2022-01-01",
    "end_date": END_DATE,
    "interval": "B",
    "strategies": [
        Strategies.MACD_CROSSOVER,
        Strategies.RSI_CROSSOVER,
        Strategies.BOLLINGER_BANDS,
        Strategies.Z_SCORE_MEAN_REVERSION,
    ],
    "constraints": {
        "max_short_count": 0.3,
        "max_long_count": 0.3,
    },
}
