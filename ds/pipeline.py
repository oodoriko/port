import json
import os
from collections import defaultdict
from pathlib import Path

import polars as pl
from config import load_configs_from_yaml
from ds_utils import get_historical_data_dict
from factory import IndicatorsFactory, TargetsFactory
from feature_selection import RegimeBasedFeatureSelector


def run_pipeline(
    config_path: str,
    start_date: str,
    end_date: str,
    data_dir: str,
    refresh_data: bool = False,
    refresh_results: bool = True,
):
    # load the config from yaml, yaml is manually created
    config = load_configs_from_yaml(config_path)

    trading_pair = config.trading_pair
    name = config.name

    features_config = config.features_config
    targets_config = config.targets_config

    if refresh_data:
        # build the indicators/targets based on the config, save the data to the data directory
        indicators_factory = IndicatorsFactory(
            name, trading_pair, features_config, start_date, end_date, data_dir
        )
        indicators_factory.build_and_save_indicators()

        targets_factory = TargetsFactory(
            name, trading_pair, targets_config, start_date, end_date, data_dir
        )
        targets_factory.build_and_save_targets()

    if refresh_results:
        # load the cached indicators
        indicators_path = (
            f"{data_dir}/indicators/coinbase_{trading_pair}_{name}.parquet"
        )
        indicators = pl.read_parquet(indicators_path)

        # load data for calculating regimes
        data = get_historical_data_dict(trading_pair, start_date, end_date)
        close = data["close"]
        volume = data["volume"]
        timestamp = data["timestamp"]

        # run it!
        results = defaultdict(lambda: defaultdict(dict))
        for target_file in os.listdir(f"{data_dir}/targets"):
            targets_data = pl.read_parquet(f"{data_dir}/targets/{target_file}")
            for target_col in ["label_vwap", "quant_vwap", "label_close"]:
                target_data = targets_data.select(["timestamp", target_col])
                selector = RegimeBasedFeatureSelector(
                    indicators=indicators,
                    targets=target_data,
                    price=close,
                    volume=volume,
                    timestamp=timestamp,
                    temporal_stability_threshold=0.8,
                    regime_stability_threshold=0.8,
                    performance_threshold=0.1,
                    gap_days=1,
                    target_col=target_col,
                )
                selector.fit()
                results[target_file][target_col] = {
                    "metrics": selector.get_metrics(),
                    "selected_features": selector.selected_features,
                    "feature_performance_matrix": selector.feature_performance_matrix,
                    "regime_performance_matrix": selector.regime_performance_matrix,
                }
                break
            break

        # save the results
        results_path = f"{data_dir}/results"
        save_results(results, results_path)


def save_results(results: dict, results_path: str):
    for target_file, file_results in results.items():
        for target_col, data in file_results.items():
            target_folder = (
                f"{results_path}/{target_file.replace('.parquet', '')}_{target_col}"
            )
            Path(target_folder).mkdir(exist_ok=True)

            if "metrics" in data:
                metrics_path = f"{target_folder}/metrics.parquet"
                data["metrics"].write_parquet(metrics_path)
                print(f"Saved metrics: {metrics_path}")

            if "selected_features" in data:
                features_path = f"{target_folder}/selected_features.json"
                with open(features_path, "w") as f:
                    json.dump(data["selected_features"], f, indent=2)
                print(f"Saved selected features: {features_path}")

            if "feature_performance_matrix" in data:
                perf_path = f"{target_folder}/feature_performance_matrix.json"
                with open(perf_path, "w") as f:
                    json.dump(data["feature_performance_matrix"], f, indent=2)
                print(f"Saved feature performance: {perf_path}")

            if "regime_performance_matrix" in data:
                regime_path = f"{target_folder}/regime_performance_matrix.json"
                with open(regime_path, "w") as f:
                    json.dump(data["regime_performance_matrix"], f, indent=2)
                print(f"Saved regime performance: {regime_path}")

            summary = {
                "target_file": target_file,
                "target_col": target_col,
                "num_selected_features": len(data.get("selected_features", [])),
                "total_features_tested": len(
                    data.get("feature_performance_matrix", {})
                ),
                "selection_rate": len(data.get("selected_features", []))
                / max(1, len(data.get("feature_performance_matrix", {}))),
            }

            summary_path = f"{target_folder}/summary.json"
            with open(summary_path, "w") as f:
                json.dump(summary, f, indent=2)
            print(f"Saved summary: {summary_path}")


def load_feature_selection_results(data_dir: str, target_folder: str):
    target_folder = f"{data_dir}/results/{target_folder}"

    result = {}

    metrics_path = f"{target_folder}/metrics.parquet"
    if metrics_path.exists():
        result["metrics"] = pl.read_parquet(metrics_path)

    features_path = f"{target_folder}/selected_features.json"
    if features_path.exists():
        with open(features_path, "r") as f:
            result["selected_features"] = json.load(f)

    perf_path = f"{target_folder}/feature_performance_matrix.json"
    if perf_path.exists():
        with open(perf_path, "r") as f:
            result["feature_performance_matrix"] = json.load(f)

    regime_path = f"{target_folder}/regime_performance_matrix.json"
    if regime_path.exists():
        with open(regime_path, "r") as f:
            result["regime_performance_matrix"] = json.load(f)

    summary_path = f"{target_folder}/summary.json"
    if summary_path.exists():
        with open(summary_path, "r") as f:
            result["summary"] = json.load(f)

    return result


if __name__ == "__main__":
    config_path = "features_sets/config_v_1.yaml"
    start_date = "2024-11-01"
    end_date = "2025-05-01"
    data_dir = "data"
    run_pipeline(config_path, start_date, end_date, data_dir)
    result = load_feature_selection_results(data_dir, "coinbase_BTC-USD_label_vwap")
    print(result)
