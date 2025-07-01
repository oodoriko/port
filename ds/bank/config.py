from __future__ import annotations

import itertools
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


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
    k_line: List[int] = field(default_factory=lambda: [9, 14, 21])
    d_line: List[int] = field(default_factory=lambda: [3, 5])

    include_delta: bool = True
    include_k_lag1: bool = True
    include_d_lag1: bool = True

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
    fast_line: List[int] = field(default_factory=lambda: [3, 5, 6, 8, 10, 12])
    slow_line: List[int] = field(default_factory=lambda: [10, 13, 10, 21, 26, 35])
    signal_line: List[int] = field(default_factory=lambda: [3, 5, 9])
    include_lag1: bool = True
    include_hist_delta: bool = True

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
    windows: List[int] = field(default_factory=lambda: [6, 9, 14, 21, 30])
    include_delta: bool = True

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
    windows: List[int] = field(default_factory=lambda: [10, 20, 30])
    std_multipliers: List[float] = field(default_factory=lambda: [1.5, 2.0, 2.5])
    types: Tuple[str, ...] = ("bandwidth", "zscore")

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
    mfi_windows: List[int] = field(default_factory=lambda: [6, 14, 21])
    include_delta: bool = True

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
    vwap_rolling_windows: List[int] = field(default_factory=lambda: [20, 50])

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
    windows: List[int] = field(default_factory=lambda: [10, 20, 30, 50, 100])

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
    windows: List[int] = field(default_factory=lambda: [5, 10, 14, 21, 30])

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
class MomentumConfig:
    stochastic: StochasticConfig
    macd: MACDConfig
    rsi: RSIConfig

    def total_features_summary(self) -> None:
        print("MomentumConfig:")
        print(f"# stochastic: {self.stochastic.total_features}")
        print(f"# macd: {self.macd.total_features}")
        print(f"# rsi: {self.rsi.total_features}")

    def total_features(self) -> int:
        return (
            self.stochastic.total_features
            + self.macd.total_features
            + self.rsi.total_features
        )


@dataclass
class VolatilityConfig:
    bollinger: BollingerConfig

    def total_features_summary(self) -> None:
        print("VolatilityConfig:")
        print(f"# bollinger: {self.bollinger.total_features}")

    def total_features(self) -> int:
        return self.bollinger.total_features


@dataclass
class VolumeConfig:
    mfi: MFIConfig
    vwap: VWAPConfig

    def total_features_summary(self) -> None:
        print("VolumeConfig:")
        print(f"# mfi: {self.mfi.total_features}")
        print(f"# vwap: {self.vwap.total_features}")

    def total_features(self) -> int:
        return self.mfi.total_features + self.vwap.total_features


@dataclass
class PriceStructureConfig:
    donchian: DonchianConfig
    atr: ATRConfig

    def total_features_summary(self) -> None:
        print("PriceStructureConfig:")
        print(f"# donchian: {self.donchian.total_features}")
        print(f"# atr: {self.atr.total_features}")

    def total_features(self) -> int:
        return self.donchian.total_features + self.atr.total_features


@dataclass
class FeatureBankConfig:
    name: str
    momentum: MomentumConfig
    volatility: VolatilityConfig
    volume: VolumeConfig
    price_structure: PriceStructureConfig

    def total_features_summary(self) -> None:
        self.momentum.total_features_summary()
        self.volatility.total_features_summary()
        self.volume.total_features_summary()
        self.price_structure.total_features_summary()

        print("total features: ", self.total_features())

    def total_features(self) -> int:
        return (
            self.momentum.total_features()
            + self.volatility.total_features()
            + self.volume.total_features()
            + self.price_structure.total_features()
        )


CONFIG_v1 = FeatureBankConfig(
    name="config_v1",
    momentum=MomentumConfig(
        stochastic=StochasticConfig(),
        macd=MACDConfig(),
        rsi=RSIConfig(),
    ),
    volatility=VolatilityConfig(
        bollinger=BollingerConfig(),
    ),
    volume=VolumeConfig(
        mfi=MFIConfig(),
        vwap=VWAPConfig(),
    ),
    price_structure=PriceStructureConfig(
        donchian=DonchianConfig(),
        atr=ATRConfig(),
    ),
)


@dataclass
class TargetConfig:
    name: str
    windows: List[int] = field(default_factory=lambda: [1, 3, 5, 10, 15])
    thresholds: Dict[int, float] = field(
        default_factory=lambda: {1: 0.0007, 3: 0.001, 5: 0.0015, 10: 0.002, 15: 0.0035}
    )

    def __post_init__(self):
        self.windows_thresholds = [(w, self.thresholds[w]) for w in self.windows]


CONFIG_y_v1 = TargetConfig(
    name="config_y_v1",
    windows=[1, 3, 5, 10, 15],
    thresholds={1: 0.0007, 3: 0.001, 5: 0.0015, 10: 0.002, 15: 0.0035},
)

# def diff(config1: FeatureBankConfig, config2: FeatureBankConfig) -> Dict[str, Any]:
#     diff = {}
#     for group_name, group_cfg1 in vars(config1).items():
#         for sub_name, sub_cfg1 in vars(group_cfg1).items():
#             for params, feature_names in sub_cfg1.features.items():

#                 if sub_name not in diff:
#                     diff[sub_name] = {}
#                 diff[sub_name][params] = feature_names
#     return diff
