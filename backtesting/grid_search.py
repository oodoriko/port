# use signal in reverse! -> filter
from config import Sectors, Strategies

# scearios -> portoflio initial setup, constraints
# gridsearch -> additional setup, run back test on all portoflio
# results -> backtest, report

# final_signal = max(-1, min(1, total_signal))

initial_capital: float = 100_000
initial_holdings: Dict[str, float] = field(default_factory=dict)
new_capital_growth_pct: float = 0.0
new_capital_growth_amt: float = 10_000
capital_growth_freq: str = CapitalGrowthFrequency.DAILY.value

grid_search_params = {
    "strategies": [
        {"triggers": [Strategies.MACD_CROSSOVER], "filter": []},
        {"triggers": [Strategies.RSI_CROSSOVER], "filter": []},
        {"triggers": [Strategies.BOLLINGER_BANDS], "filter": []},
        {"triggers": [Strategies.Z_SCORE_MEAN_REVERSION], "filter": []},
        {
            "triggers": [Strategies.MACD_CROSSOVER],
            "filter": [Strategies.BOLLINGER_BANDS],
        },  # mean reversion confirmed by bollinger bands
        {
            "triggers": [Strategies.RSI_CROSSOVER, Strategies.Z_SCORE_MEAN_REVERSION],
            "filter": [],
        },  # momentum with mean reversion
        {
            "triggers": [
                Strategies.MACD_CROSSOVER,
                Strategies.BOLLINGER_BANDS,
                Strategies.Z_SCORE_MEAN_REVERSION,
                Strategies.RSI_CROSSOVER,
            ],
            "filter": [],
        },  # DON'T KNOW
    ],
    "sector_exposure": [
        [
            Sectors.TECHNOLOGY,
            Sectors.FINANCIAL_SERVICES,
            Sectors.CONSUMER_CYCLICAL,
            Sectors.COMMUNICATION_SERVICES,
            Sectors.HEALTHCARE,
            Sectors.INDUSTRIALS,
            Sectors.CONSUMER_DEFENSIVE,
            Sectors.ENERGY,
            Sectors.BASIC_MATERIALS,
            Sectors.REAL_ESTATE,
            Sectors.UTILITIES,
        ],  # all
        [Sectors.TECHNOLOGY, Sectors.ENERGY, Sectors.INDUSTRIALS],  # Trend following
        [
            Sectors.TECHNOLOGY,
            Sectors.COMMUNICATION_SERVICES,
            Sectors.FINANCIAL_SERVICES,
        ],  # sentiment-based
        [
            Sectors.UTILITIES,
            Sectors.CONSUMER_CYCLICAL,
            Sectors.CONSUMER_DEFENSIVE,
            Sectors.HEALTHCARE,
            Sectors.REAL_ESTATE,
        ],  # mean reversion
    ],
}


def grid_search(params):
    pass
