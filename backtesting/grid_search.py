import os
import traceback
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime
from itertools import combinations, product
from typing import Any, List, Optional

import numpy as np
import pandas as pd
from tqdm import tqdm

from backtesting.backtest import Backtest
from backtesting.scenarios import Scenario
from strategies.strategy import StrategyTypes


class GridSearch:
    def __init__(
        self,
        base_scenario: Scenario,
        max_workers: Optional[int] = None,
        verbose: bool = False,
    ):
        self.base_scenario = base_scenario
        self.max_workers = max_workers
        self.grid_params = None
        self.results = []
        self.verbose = verbose

    def set_grid_params(
        self,
        grid_params: list[dict[str, Any]] | list[StrategyTypes],
        max_signal: int = 4,
        max_filter: int = 4,
        min_signal: int = 0,
        min_filter: int = 0,
    ):
        if (
            grid_params is not None
            and len(grid_params) > 0
            and isinstance(grid_params[0], StrategyTypes)
        ):
            grid_params = self._generate_grid_params(
                grid_params,
                max_signal=max_signal,
                max_filter=max_filter,
                min_signal=min_signal,
                min_filter=min_filter,
            )
        self.grid_params = grid_params

    def _generate_grid_params(
        self,
        strategy_types: list[StrategyTypes],
        max_signal: int,
        max_filter: int,
        min_signal: int,
        min_filter: int,
    ):
        all_combinations = []
        for r in range(1, len(strategy_types) + 1):
            for combo in combinations(strategy_types, r):
                for truth_values in product([True, False], repeat=len(combo)):
                    true_count = truth_values.count(True)
                    false_count = truth_values.count(False)
                    if (min_signal <= true_count <= max_signal) and (
                        min_filter <= false_count <= max_filter
                    ):
                        all_combinations.append(dict(zip(combo, truth_values)))
        print(f"Generated {len(all_combinations)} grid parameter combinations")
        return all_combinations

    def _generate_grid_params_combo(
        self,
        grid_params: list[dict[str, Any]],
    ):
        """not the classic auto cartesian product way YET"""
        param_names = []
        param_values = []
        for param in grid_params:
            name_map = {True: "Pos", False: "Neg"}
            strategy_names = defaultdict(list)
            for strategy, is_positive in param.items():
                strategy_names[name_map[is_positive]].append(strategy.value)
            strategy_names = {
                k: strategy_names[k] for k in ["Pos", "Neg"] if len(strategy_names[k]) > 0
            }  # enforced key order for formatting
            param_values.append(param)
            param_names.append(strategy_names)

        param_names = [
            " ".join([f"**{key}: {' || '.join(value)}" for key, value in param.items()])
            for param in param_names
        ]
        return param_names, param_values

    def _create_scenarios(self) -> List[Scenario]:
        param_names, param_values = self._generate_grid_params_combo(self.grid_params)
        scenarios = {}
        for i, (param_name, param_value) in enumerate(zip(param_names, param_values)):
            scenario = deepcopy(self.base_scenario)
            scenario.set_strategies(param_value)
            scenario.set_name(f"grid_{i+1}")
            scenario.portfolio.set_name(f"{param_name}")
            scenarios[f"grid_{i+1}"] = scenario
        return scenarios

    def _run_single_backtest(self, scenario: Scenario) -> dict:
        try:
            backtest = Backtest(scenario)
            backtest.run_batch(verbose=False)
            analytics = backtest.generate_analytics()

            performance_metrics = analytics.performance_metrics()
            holdings_metrics = analytics.holdings_metrics()
            average_holding_period = np.mean(list(holdings_metrics.values()))
            max_holding_amount = max(holdings_metrics.values())

            return {
                "grid_num": scenario.name,
                "param_name": scenario.portfolio.name,
                "total_return": performance_metrics["total_return"],
                "annualized_return": performance_metrics["annualized_return"],
                "annualized_sharpe": performance_metrics["annualized_sharpe"],
                "annualized_ir": performance_metrics["annualized_ir"],
                "average_holding_period": average_holding_period,
                "max_holding_amount": max_holding_amount,
            }
        except Exception as e:
            print(traceback.format_exc())
            print(f"Error running backtest for {scenario.name}")
            return None

    def run(self, parallel: bool = True) -> List[dict]:
        scenarios = self._create_scenarios()
        print(f"Running grid search with {len(scenarios)} parameter combinations...")

        self.results = {}

        if parallel and len(scenarios) > 1:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_scenario = {
                    executor.submit(self._run_single_backtest, scenario): scenario
                    for scenario in scenarios.values()
                }

                for future in tqdm(
                    as_completed(future_to_scenario),
                    total=len(scenarios),
                    desc="Grid search progress",
                    disable=not self.verbose,
                ):
                    result = future.result()
                    if result is not None:
                        self.results[result["grid_num"].split("_")[-1]] = result
        else:
            for scenario in tqdm(scenarios.values(), desc="Grid search progress"):
                result = self._run_single_backtest(scenario)
                if result is not None:
                    self.results[result["grid_num"].split("_")[-1]] = result

        print(f"Grid search completed! Found {len(self.results)} valid results.")

    def get_results(self) -> dict:
        return self.results

    def get_grid_search_schedule(self) -> pd.DataFrame:
        return pd.DataFrame(
            [{"grid_num": k, "param_name": v["param_name"]} for k, v in self.results.items()]
        ).sort_values(by="grid_num", ascending=True)

    def results_to_dataframe(self) -> pd.DataFrame:
        if not self.results:
            return pd.DataFrame()

        data = []
        for key, result in self.results.items():
            row = {
                "grid_num": key,
                "param_name": result["param_name"],
                "total_return": result["total_return"],
                "annualized_return": result["annualized_return"],
                "annualized_sharpe": result["annualized_sharpe"],
                "annualized_ir": result["annualized_ir"],
                "average_holding_period": result["average_holding_period"],
                "max_holding_amount": result["max_holding_amount"],
            }
            data.append(row)

        return pd.DataFrame(data).sort_values(by="grid_num", ascending=True)

    def results_to_csv(self, filename: str = None):
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"outputs/grid_search/gs_results_{timestamp}.csv"
        elif not filename.endswith(".csv"):
            filename = f"outputs/grid_search/{filename}.csv"
        else:
            filename = f"outputs/grid_search/{filename}"

        os.makedirs("outputs/grid_search", exist_ok=True)
        df = self.results_to_dataframe()
        df.sort_values(by="annualized_return", ascending=False, inplace=True)
        df.to_csv(filename, index=False)

    def results_to_text(self, filename: str = None):
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"outputs/grid_search/gs_results_{timestamp}.txt"
        elif not filename.endswith(".txt"):
            filename = f"outputs/grid_search/{filename}.txt"
        else:
            filename = f"outputs/grid_search/{filename}"

        os.makedirs("outputs/grid_search", exist_ok=True)

        d = self.results_to_dataframe()
        d.sort_values(by="annualized_return", ascending=False, inplace=True)
        d[["total_return", "annualized_return"]] = d[
            ["total_return", "annualized_return"]
        ].applymap(lambda x: f"{x*100:.2f}%")
        d[["annualized_sharpe", "annualized_ir"]] = d[
            ["annualized_sharpe", "annualized_ir"]
        ].applymap(lambda x: f"{x:.2f}")
        d[["average_holding_period", "max_holding_amount"]] = d[
            ["average_holding_period", "max_holding_amount"]
        ].applymap(lambda x: f"{x:.0f}")

        print(d.to_string(index=False))
        with open(filename, "w") as f:
            f.write(d.to_string(index=False))
