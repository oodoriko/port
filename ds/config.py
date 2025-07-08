from __future__ import annotations

import itertools
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import yaml


def cartesian_product(lists: List[List[Any]]) -> List[Tuple[Any, ...]]:
    return [product for product in itertools.product(*lists)]


class IndicatorConfig(ABC):
    def __post_init__(self):
        self.features_meta = self._generate_features_meta()
        self.total_features = sum(len(v) for v in self.features_meta.values())

    @abstractmethod
    def _generate_features(self) -> Dict[Tuple[Any, ...], List[str]]:
        pass

    @abstractmethod
    def feature_summary(self) -> None:
        pass

    @abstractmethod
    def print_config(self) -> None:
        pass


@dataclass
class StochasticConfig(IndicatorConfig):
    k_line: List[int]
    d_line: List[int]

    include_delta: bool
    include_k_lag1: bool
    include_d_lag1: bool
    name: str = "stochastic"

    def __post_init__(self):
        self.k_d_pairs = cartesian_product([self.k_line, self.d_line])
        self.features = self._generate_features()
        self.total_features = sum(len(v) for v in self.features.values())

    def _generate_features(self) -> Dict[Tuple[int, int], List[str]]:
        features = {}
        for k, d in self.k_d_pairs:
            names = []
            prefix = f"stoch_k{k}_d{d}"
            names.append(f"{prefix}_k")
            names.append(f"{prefix}_d")
            names.append(f"{prefix}_k_minus_d")
            if self.include_delta:
                names.append(f"{prefix}_k_delta")
            if self.include_k_lag1:
                names.append(f"{prefix}_k_lag1")
            if self.include_d_lag1:
                names.append(f"{prefix}_d_lag1")
            features[
                (k, d, self.include_delta, self.include_k_lag1, self.include_d_lag1)
            ] = names
        return features

    def feature_summary(self) -> None:
        print("StochasticConfig:")
        print(f"# value pairs: {len(self.features.keys())}")
        print(f"# features: {self.total_features}")

    def print_config(self) -> None:
        self.feature_summary()
        print(f"k_line: {self.k_line}")
        print(f"d_line: {self.d_line}")
        print(f"include_delta: {self.include_delta}")
        print(f"include_k_lag1: {self.include_k_lag1}")
        print(f"include_d_lag1: {self.include_d_lag1}")


@dataclass
class MACDConfig(IndicatorConfig):
    fast_line: List[int]
    slow_line: List[int]
    signal_line: List[int]
    include_lag1: bool
    include_hist_delta: bool
    name: str = "macd"

    def __post_init__(self):
        triplets = cartesian_product([self.fast_line, self.slow_line, self.signal_line])
        self.triplets = [
            (fast, slow, signal) for fast, slow, signal in triplets if slow - fast >= 2
        ]
        self.features = self._generate_features()
        self.total_features = sum(len(v) for v in self.features.values())

    def _generate_features(self) -> Dict[Tuple[int, int, int], List[str]]:
        features = {}
        for fast, slow, signal in self.triplets:
            names = []
            prefix = f"macd_fast{fast}_slow{slow}_signal{signal}_hist"
            if self.include_lag1:
                names.append(f"{prefix}_lag1")
            if self.include_hist_delta:
                names.append(f"{prefix}_delta")
            features[
                (fast, slow, signal, self.include_lag1, self.include_hist_delta)
            ] = names
        return features

    def feature_summary(self) -> None:
        print("MACDConfig:")
        print(f"# triplets: {len(self.triplets)}")
        print(f"# features: {sum(len(v) for v in self.features.values())}")

    def print_config(self) -> None:
        self.feature_summary()
        print(f"fast_line: {self.fast_line}")
        print(f"slow_line: {self.slow_line}")
        print(f"signal_line: {self.signal_line}")
        print(f"include_lag1: {self.include_lag1}")


@dataclass
class RSIConfig(IndicatorConfig):
    windows: List[int]
    include_delta: bool
    name: str = "rsi"

    def __post_init__(self):
        self.features = self._generate_features()
        self.total_features = sum(len(v) for v in self.features.values())

    def _generate_features(self) -> Dict[int, List[str]]:
        features = {}
        for window in self.windows:
            names = []
            prefix = f"rsi_{window}"
            names.append(prefix)
            if self.include_delta:
                names.append(f"{prefix}_delta")
            features[(window, self.include_delta)] = names
        return features

    def feature_summary(self) -> None:
        print("RSIConfig:")
        print(f"# windows: {len(self.windows)}")
        print(f"# features: {self.total_features}")

    def print_config(self) -> None:
        self.feature_summary()
        print(f"windows: {self.windows}")
        print(f"include_delta: {self.include_delta}")


@dataclass
class BollingerConfig(IndicatorConfig):
    windows: List[int]
    std_multipliers: List[float]
    types: List[str]
    name: str = "bollinger"

    def __post_init__(self):
        self.triplets = cartesian_product(
            [self.windows, self.std_multipliers, self.types]
        )
        self.features = self._generate_features()
        self.total_features = sum(len(v) for v in self.features.values())

    def _generate_features(self) -> Dict[int, List[str]]:
        features = {}
        for window, std_multiplier, type in self.triplets:
            prefix = f"bb_{window}_{std_multiplier}_{type}"
            features[(window, std_multiplier, type)] = [prefix]
        return features

    def feature_summary(self) -> None:
        print("BollingerConfig:")
        print(f"# windows: {len(self.windows)}")
        print(f"# std_multipliers: {len(self.std_multipliers)}")
        print(f"# types: {len(self.types)}")
        print(f"# features: {self.total_features}")

    def print_config(self) -> None:
        self.feature_summary()
        print(f"windows: {self.windows}")
        print(f"std_multipliers: {self.std_multipliers}")
        print(f"types: {self.types}")


@dataclass
class MFIConfig(IndicatorConfig):
    mfi_windows: List[int]
    include_delta: bool
    name: str = "mfi"

    def __post_init__(self):
        self.features = self._generate_features()
        self.total_features = sum(len(v) for v in self.features.values())

    def _generate_features(self) -> Dict[int, List[str]]:
        features = {}
        for window in self.mfi_windows:
            names = []
            prefix = f"mfi_{window}"
            names.append(prefix)
            if self.include_delta:
                names.append(f"{prefix}_delta")
            features[(window, self.include_delta)] = names
        return features

    def feature_summary(self) -> None:
        print("MFIConfig:")
        print(f"# windows: {len(self.mfi_windows)}")
        print(f"# features: {self.total_features}")

    def print_config(self) -> None:
        self.feature_summary()
        print(f"mfi_windows: {self.mfi_windows}")
        print(f"include_delta: {self.include_delta}")


@dataclass
class VWAPConfig(IndicatorConfig):
    vwap_rolling_windows: List[int]
    name: str = "vwap"

    def __post_init__(self):
        self.features = self._generate_features()
        self.total_features = sum(len(v) for v in self.features.values())

    def _generate_features(self) -> Dict[int, List[str]]:
        features = {}
        for window in self.vwap_rolling_windows:
            names = []
            prefix = f"vwap_dist_rolling_{window}"
            names.append(prefix)
            features[window] = names
        return features

    def feature_summary(self) -> None:
        print("VWAPConfig:")
        print(f"# rolling windows: {len(self.vwap_rolling_windows)}")
        print(f"# features: {self.total_features}")

    def print_config(self) -> None:
        self.feature_summary()
        print(f"vwap_rolling_windows: {self.vwap_rolling_windows}")


@dataclass
class DonchianConfig(IndicatorConfig):
    windows: List[int]
    name: str = "donchian"

    def __post_init__(self):
        self.features = self._generate_features()
        self.total_features = sum(len(v) for v in self.features.values())

    def _generate_features(self) -> Dict[int, List[str]]:
        features = {}
        for window in self.windows:
            names = []
            prefix = f"donchian_{window}"
            names.append(prefix)
            names.append(f"{prefix}_price")
            features[window] = names

        return features

    def feature_summary(self) -> None:
        print("DonchianConfig:")
        print(f"# windows: {len(self.windows)}")
        print(f"# features: {self.total_features}")

    def print_config(self) -> None:
        self.feature_summary()
        print(f"windows: {self.windows}")


@dataclass
class ATRConfig(IndicatorConfig):
    windows: List[int]
    name: str = "atr"

    def __post_init__(self):
        self.features = self._generate_features()
        self.total_features = sum(len(v) for v in self.features.values())

    def _generate_features(self) -> Dict[int, List[str]]:
        features = {}
        for window in self.windows:
            names = []
            prefix = f"atr_{window}"
            names.append(prefix)
            names.append(f"{prefix}_price")
            features[window] = names

        return features

    def feature_summary(self) -> None:
        print("ATRnConfig:")
        print(f"# windows: {len(self.windows)}")
        print(f"# features: {self.total_features}")

    def print_config(self) -> None:
        self.feature_summary()


@dataclass
class TargetConfig:
    windows: List[int]
    thresholds: Dict[int, float]
    name: str = "target"

    def __post_init__(self):
        self.windows_thresholds = [(w, self.thresholds[w]) for w in self.windows]


# remove default factory for all configs use list instead of tuple remove wrapper configs remove name from targetconfig renamne as TargetConfig check and refactor target
fns_mapping = {
    "StochasticConfig": StochasticConfig,
    "BollingerConfig": BollingerConfig,
    "MACDConfig": MACDConfig,
    "RSIConfig": RSIConfig,
    "MFIConfig": MFIConfig,
    "VWAPConfig": VWAPConfig,
    "DonchianConfig": DonchianConfig,
    "ATRConfig": ATRConfig,
    "TargetConfig": TargetConfig,
}


@dataclass
class FeaturesSelectionConfig:
    name: str
    trading_pair: str
    features_config: List[IndicatorConfig]
    targets_config: TargetConfig


def validate_yaml(data) -> bool:
    """Validate YAML configuration data against expected schema."""
    meta_keys = ["name", "trading_pair"]
    for key in meta_keys:
        if key not in data or len(data[key]) == 0 or not isinstance(data[key], str):
            raise KeyError(f"Missing/empty/non-str for required key: {key}")

    for cfg in ["features_config", "targets_config"]:
        if cfg not in data:
            raise KeyError(f"Missing config: {cfg}")
        config_inputs = data[cfg]
        for config_name, inputs in config_inputs.items():
            if config_name not in fns_mapping:
                raise KeyError(f"Config name not found: {config_name}")
            else:
                # Get the class from fns_mapping
                config_class = fns_mapping[config_name]
                # Get field names from the dataclass
                from dataclasses import fields

                expected_fields = {field.name for field in fields(config_class)}
                for k, v in inputs.items():
                    if k not in expected_fields:
                        raise KeyError(f"Config attribute missing: {config_name}:{k}")
    return True


def load_configs_from_yaml(yaml_path: str) -> FeaturesSelectionConfig:
    with open(yaml_path, encoding="utf-8") as f:
        file = yaml.safe_load(f)
        validate_yaml(file)
        name = file["name"]
        trading_pair = file["trading_pair"]
        features_inputs = file["features_config"]
        targets_inputs = file["targets_config"]
    features_cfg = [
        fns_mapping[feature](**inputs) for feature, inputs in features_inputs.items()
    ]
    targets_cfg = [
        fns_mapping[target](**inputs) for target, inputs in targets_inputs.items()
    ]
    return FeaturesSelectionConfig(
        name=name,
        trading_pair=trading_pair,
        features_config=features_cfg,
        targets_config=targets_cfg[0],
    )
