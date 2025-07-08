from typing import List

import polars as pl
from config import IndicatorConfig, TargetConfig
from ds_utils import get_historical_data_dict
from indicators import build_indicators
from target import build_targets


class IndicatorsFactory:
    def __init__(
        self,
        name: str,
        trading_pair: str,
        config: List[IndicatorConfig],
        start_date: str,
        end_date: str,
        data_dir: str,
    ):
        self.indicators = build_indicators(config)
        data = get_historical_data_dict(trading_pair, start_date, end_date)
        self.close = data["close"]
        self.high = data["high"]
        self.low = data["low"]
        self.volume = data["volume"]
        self.timestamp = data["timestamp"]
        self.table_name = f"coinbase_{trading_pair.replace('-', '_')}_{name}"
        self.data_dir = f"{data_dir}/indicators/{self.table_name}.parquet"
        del data

    def build_and_save_indicators(self):
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
        df.write_parquet(self.data_dir)


class TargetsFactory:
    def __init__(
        self,
        name: str,
        trading_pair: str,
        config: TargetConfig,
        start_date: str,
        end_date: str,
        data_dir: str,
    ):
        self.trading_pair = trading_pair
        self.config = config
        data = get_historical_data_dict(trading_pair, start_date, end_date)
        self.close = data["close"]
        self.high = data["high"]
        self.low = data["low"]
        self.volume = data["volume"]
        self.timestamp = data["timestamp"]
        self.table_name = f"coinbase_{trading_pair.replace('-', '_')}_{name}"
        self.data_dir = f"{data_dir}/targets"
        del data

    def build_and_save_targets(self):
        targets = build_targets(
            self.low, self.high, self.close, self.volume, self.timestamp, self.config
        )
        for w, t in targets.keys():
            df = pl.DataFrame(targets[(w, t)])
            df = df.sort("timestamp")
            df.write_parquet(f"{self.data_dir}/{self.table_name}_{w}_{t}.parquet")
