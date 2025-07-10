from typing import Dict, List, Tuple

import numpy as np
import polars as pl
from ds_utils import DSLogger
from model import CustomXGB


class RegimeBasedFeatureSelector:
    """bucket the timestamps into different regimes, the idea here is we want to find
    signals that is stable across idiosyncrasies. In other word, we are forfeiting regime
    driven alpha. This is basically a beta strategy optimizer. In the event we want to focus
    on regime detection and switch strategy based off that, we can reverse the filtering rules in this class.

    Regimes are heavily influenced by market microstructure.
    This selector use XGBoost
    """

    def __init__(
        self,
        indicators: pl.DataFrame,
        targets: pl.DataFrame,
        price: np.array,
        volume: np.array,
        timestamp: np.array,
        temporal_stability_threshold: float = 0.8,
        regime_stability_threshold: float = 0.8,
        performance_threshold: float = 0.1,
        gap_days=1,
        target_col: str = "label_vwap",
    ):
        self.indicators = indicators
        self.targets = targets
        self.price = price
        self.volume = volume
        self.timestamp = timestamp

        self.temporal_stability_threshold = temporal_stability_threshold
        self.regime_stability_threshold = regime_stability_threshold
        self.performance_threshold = performance_threshold
        self.gap_days = gap_days

        self.feature_cols = [
            col for col in self.indicators.columns if col not in ["timestamp", "regime"]
        ]
        self.target_col = target_col

        self.features_scores = {}
        self.selected_features = []
        self.feature_performance_matrix = {}
        self.regime_performance_matrix = {}
        self.feature_importance_matrix = {}

        self.logger = DSLogger(__name__)

    def fit(self):
        self.logger.info("Step 1: Creating regimes")
        regimes_df = _create_regimes(self.price, self.volume, self.timestamp)
        regimes = regimes_df.select(pl.col("regime").unique()).to_series().to_list()
        regimes = [r for r in regimes if r is not None]
        print(regimes)

        if self.indicators["timestamp"].dtype not in [pl.Datetime]:
            self.indicators = self.indicators.with_columns(
                pl.from_epoch(pl.col("timestamp")).alias("timestamp")
            )
        if self.targets["timestamp"].dtype not in [pl.Datetime]:
            self.targets = self.targets.with_columns(
                pl.from_epoch(pl.col("timestamp")).alias("timestamp")
            )

        data_with_regimes = self.indicators.join(
            regimes_df, on="timestamp", how="inner"
        ).join(self.targets, on="timestamp", how="inner")

        self.logger.info(f"Found {len(regimes)} regimes")

        self.logger.info("Step 2: Creating splits")
        splits = _create_forward_splits(data_with_regimes)

        self.feature_performance_matrix = {feature: [] for feature in self.feature_cols}
        self.feature_importance_matrix = {feature: [] for feature in self.feature_cols}
        self.regime_performance_matrix = {
            regime: {feature: [] for feature in self.feature_cols} for regime in regimes
        }
        self.logger.info(f"Created {len(splits)} splits")

        self.logger.info("Step 3: Start walk forward validation")
        for idx, (train_expr, test_expr) in enumerate(splits):
            train_data = data_with_regimes.filter(train_expr)
            test_data = data_with_regimes.filter(test_expr)

            if train_data.height < 100 or test_data.height < 100:
                self.logger.info(
                    f"Skipping split {idx} due to insufficient data. Train: {train_data.height}, Test: {test_data.height}"
                )
                continue

            self.logger.info(f"Evaluating feature performance for split {idx}")
            model = CustomXGB(
                train_data=train_data,
                test_data=test_data,
                feature_cols=self.feature_cols,
                target_col=self.target_col,
            )
            overall_feature_performance = model.fit()
            if self.feature_cols:
                self.task_type = overall_feature_performance[self.feature_cols[0]][
                    "task_type"
                ]
            for feature in self.feature_cols:
                self.feature_performance_matrix[feature].append(
                    overall_feature_performance[feature]["primary_score"]
                )
                self.feature_importance_matrix[feature].append(
                    overall_feature_performance[feature]["importance"]
                )
            self.logger.info(f"Evaluating regime performance for split {idx}")
            for regime in regimes:
                test_data_regime = test_data.filter(pl.col("regime") == regime)
                if test_data_regime.height > 10:
                    model = CustomXGB(
                        train_data,
                        test_data_regime,
                        self.feature_cols,
                        self.target_col,
                    )
                    regime_performance = model.fit()
                    for feature in self.feature_cols:
                        self.regime_performance_matrix[regime][feature].append(
                            regime_performance[feature]["primary_score"]
                        )
        self.logger.info("Step 4: feature stability scores")
        for feature in self.feature_cols:
            temporal_scores = self.feature_performance_matrix[feature]
            if len(temporal_scores) > 0:
                temporal_stability = np.mean(
                    np.array(temporal_scores) > self.performance_threshold
                )
            else:
                temporal_stability = 0.0

            regime_stabilities = []
            for regime in regimes:
                regime_scores = self.regime_performance_matrix[regime][feature]
                if len(regime_scores) > 0:
                    regime_stability = np.mean(
                        np.array(regime_scores) > self.performance_threshold
                    )
                    regime_stabilities.append(regime_stability)
            average_regime_stability = (
                np.mean(regime_stabilities) if regime_stabilities else 0.0
            )
            self.features_scores[feature] = {
                "temporal_stability": temporal_stability,
                "regime_stability": average_regime_stability,
                "combined_stability": (temporal_stability * average_regime_stability)
                / 2,
                "mean_performance": (
                    np.mean(temporal_scores) if temporal_scores else 0.0
                ),
                "std_performance": np.std(temporal_scores) if temporal_scores else 0.0,
                "task_type": getattr(self, "task_type", "unknown"),
            }

        self.logger.info(f"Step 5: select stable features")
        for feature, score in self.features_scores.items():
            if (
                score["temporal_stability"] >= self.temporal_stability_threshold
                and score["regime_stability"] >= self.regime_stability_threshold
            ):
                self.selected_features.append(feature)

        self.logger.info(
            f"Selected {len(self.selected_features)} out of {len(self.feature_cols)} features "
            f"({len(self.selected_features)/len(self.feature_cols)*100:.1f}% selection rate)"
        )

    def get_metrics(self) -> pl.DataFrame:
        report_data = []
        for feature in sorted(
            self.features_scores.keys(),
            key=lambda x: self.features_scores[x]["combined_stability"],
            reverse=True,
        ):
            scores = self.features_scores[feature]
            importance = self.feature_importance_matrix[feature]
            status = "SELECTED" if feature in self.selected_features else "REJECTED"

            report_data.append(
                {
                    "feature": feature,
                    "status": status,
                    "temporal_stability": scores["temporal_stability"],
                    "regime_stability": scores["regime_stability"],
                    "combined_stability": scores["combined_stability"],
                    "mean_performance": scores["mean_performance"],
                    "std_performance": scores["std_performance"],
                    "importance": np.mean(importance) if importance else 0.0,
                }
            )

        return pl.DataFrame(report_data)


def _calculate_volatility(price: np.array, window: int = 20) -> np.array:
    returns = np.full(price.shape[0], np.nan)
    returns[1:] = np.diff(price) / price[:-1]
    n = len(returns)
    result = np.full(n, np.nan)

    for i in range(window - 1, n):
        window_data = returns[i - window + 1 : i + 1]
        result[i] = np.std(window_data)

    return result * np.sqrt(window)


def _create_regimes(price: np.array, volume: np.array, timestamp: np.array) -> np.array:
    volatility = _calculate_volatility(price)
    df = pl.DataFrame(
        {"volatility": volatility, "volume": volume, "timestamp": timestamp}
    )
    # Convert timestamp to datetime if it's Unix timestamp (integer)
    if df["timestamp"].dtype in [pl.Int64, pl.Int32, pl.Float64, pl.Float32]:
        df = df.with_columns(pl.from_epoch(pl.col("timestamp")).alias("timestamp"))

    regimes = (
        df.with_columns(
            [
                pl.col("timestamp").dt.hour().alias("hour"),
                pl.col("volume")
                .qcut(3, labels=["Low", "Medium", "High"])
                .alias("volume_regime"),
            ]
        )
        .with_columns(
            [
                # pl.when(pl.col("hour") < 8)
                # .then(pl.lit("Asian"))
                # .when(pl.col("hour") < 16)
                # .then(pl.lit("European"))
                # .otherwise(pl.lit("US"))
                # .alias("session"),
                pl.when(pl.col("volatility") < pl.col("volatility").median())
                .then(pl.lit("Low"))
                .otherwise(pl.lit("High"))
                .alias("volatility_regime"),
            ]
        )
        .with_columns(
            [
                pl.concat_str(
                    [
                        # pl.col("session"),
                        pl.col("volatility_regime"),
                        pl.col("volume_regime"),
                    ]
                ).alias("regime"),
                pl.col("timestamp").dt.week().alias("week"),
            ]
        )
    )
    return regimes


def _create_forward_splits(
    df: pl.DataFrame, train_weeks: int = 5, test_weeks: int = 2, gap_days: int = 3
) -> List[Tuple[pl.Expr, pl.Expr]]:
    unique_weeks = df.select(pl.col("week").unique().sort()).to_series().to_list()
    splits = []

    for i in range(len(unique_weeks) - train_weeks - test_weeks - gap_days + 1):
        train_weeks_range = unique_weeks[i : i + train_weeks]
        test_weeks_range = unique_weeks[
            i + train_weeks + gap_days : i + train_weeks + gap_days + test_weeks
        ]

        # Create Polars expressions for filtering
        train_expr = pl.col("week").is_in(train_weeks_range)
        test_expr = pl.col("week").is_in(test_weeks_range)

        splits.append((train_expr, test_expr))

    return splits
