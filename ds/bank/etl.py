import os
from pathlib import Path

import polars as pl
from bank.config import FeatureBankConfig, TargetConfig
from bank.indicators import build_indicators
from bank.target import build_targets
from database_utils import get_historical_data_dict


class IndicatorsETL:
    def __init__(
        self,
        trading_pair: str,
        config: FeatureBankConfig,
        limit: int = None,
    ):
        """
        Initialize ETL for indicators data.

        Args:
            trading_pair: Trading pair like "btc-usdc"
            config: FeatureBankConfig object
            limit: Optional limit on number of rows
            storage_type: "parquet" or "database"
            output_dir: Directory for parquet files (if storage_type="parquet")
        """
        self.indicators = build_indicators(config)
        data = get_historical_data_dict(trading_pair, limit)
        self.close = data["close"]
        self.high = data["high"]
        self.low = data["low"]
        self.volume = data["volume"]
        self.timestamp = data["timestamp"]
        self.table_name = f"coinbase_{trading_pair.replace('-', '_')}_{config.name}"
        del data

    def run(self):
        indicators_data = {}
        for indicator in self.indicators:
            feature_names = indicator.feature_names
            feature_values = indicator.compute(
                self.high, self.low, self.close, self.volume
            )
            features = dict(zip(feature_names, feature_values))
            indicators_data.update(features)

        indicators_data["timestamp"] = self.timestamp

        df = pl.DataFrame(indicators_data)
        df = df.sort("timestamp")
        df.write_parquet(f"data/indicators/{self.table_name}.parquet")


class TargetsETL:
    def __init__(self, trading_pair: str, config: TargetConfig):
        self.trading_pair = trading_pair
        self.config = config
        data = get_historical_data_dict(trading_pair, None)
        self.close = data["close"]
        self.high = data["high"]
        self.low = data["low"]
        self.volume = data["volume"]
        self.timestamp = data["timestamp"]
        self.table_name = f"coinbase_{trading_pair.replace('-', '_')}_{config.name}"
        del data

    def run(self):
        targets = build_targets(
            self.low, self.high, self.close, self.volume, self.timestamp
        )
        for w, t in targets.keys():
            df = pl.DataFrame(targets[(w, t)])
            df = df.sort("timestamp")
            df.write_parquet(f"data/targets/{self.table_name}_{w}_{t}.parquet")
