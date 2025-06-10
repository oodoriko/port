from config import (
    DEFAULT_BACKTEST_PARAMS,
    INITIAL_SETUP,
    Benchmarks,
    CapitalGrowthFrequency,
    InitialSetup,
    Strategies,
)


class Scenario:
    def __init__(
        self,
        name,
        strategies,
        start_date,
        end_date,
        constraints,
        additional_setup,
        benchmark,
    ):
        self.name = name
        self.strategies = strategies
        self.start_date = start_date
        self.end_date = end_date
        self.constraints = constraints
        self.additional_setup = additional_setup
        self.benchmark = benchmark
        self.trading_style = ""

    def set_trading_style(self, trading_style):
        self.trading_style = trading_style


# scenario 1: sp500 10yrs unconstrained no short macd rsi bollinger mr
scenario_1 = Scenario(
    name="sp500_10yrs_unconstrained_no_short_macd_rsi_bollinger_mr",
    strategies=[
        Strategies.MACD_CROSSOVER,
        Strategies.RSI_CROSSOVER,
        Strategies.BOLLINGER_BANDS,
        Strategies.Z_SCORE_MEAN_REVERSION,
    ],
    start_date="2015-01-01",
    end_date="2025-06-01",
    constraints=DEFAULT_BACKTEST_PARAMS["constraints"],
    additional_setup=INITIAL_SETUP,
    benchmark=Benchmarks.SP500,
)
scenario_1.set_trading_style(
    """Using purely technical indicators with a lookback window less than 2 months.
The portfolio should be traded relatively frequently, with a high turnover rate.
    """
)


# for testing
scenario_2 = Scenario(
    name="testing",
    strategies=[Strategies.MACD_CROSSOVER],
    start_date="2025-02-01",
    end_date="2025-06-01",
    constraints=DEFAULT_BACKTEST_PARAMS["constraints"],
    additional_setup=INITIAL_SETUP,
    benchmark=Benchmarks.SP500,
)


# for testing
scenario_3 = Scenario(
    name="sp500_3yrs_unconstrained_no_short_macd",
    strategies=[
        Strategies.MACD_CROSSOVER,
        Strategies.RSI_CROSSOVER,
        Strategies.BOLLINGER_BANDS,
        Strategies.Z_SCORE_MEAN_REVERSION,
    ],
    start_date="2022-01-01",
    end_date="2025-06-01",
    constraints=DEFAULT_BACKTEST_PARAMS["constraints"],
    additional_setup=INITIAL_SETUP,
    benchmark=Benchmarks.SP500,
)


# Test scenarios to demonstrate capital growth configurations
scenario_no_capital_growth = Scenario(
    name="test_no_capital_growth",
    strategies=[Strategies.MACD_CROSSOVER],
    start_date="2025-02-01",
    end_date="2025-06-01",
    constraints=DEFAULT_BACKTEST_PARAMS["constraints"],
    additional_setup=InitialSetup(
        initial_capital=10,
        new_capital_growth_amt=0,  # No capital growth
        capital_growth_freq=CapitalGrowthFrequency.MONTHLY.value,
    ).to_dict(),
    benchmark=Benchmarks.SP500,
)

scenario_with_capital_growth = Scenario(
    name="test_with_10k_daily_capital_growth",
    strategies=[Strategies.MACD_CROSSOVER],
    start_date="2025-02-01",
    end_date="2025-06-01",
    constraints=DEFAULT_BACKTEST_PARAMS["constraints"],
    additional_setup=InitialSetup(
        initial_capital=100_000,
        new_capital_growth_amt=10_000,  # $10k capital growth
        capital_growth_freq=CapitalGrowthFrequency.DAILY.value,  # Daily
    ).to_dict(),
    benchmark=Benchmarks.SP500,
)
