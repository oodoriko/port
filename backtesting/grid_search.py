import traceback
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from typing import Any, List, Optional

import numpy as np
import pandas as pd
from tqdm import tqdm

from backtesting.backtest import Backtest
from backtesting.scenarios import Scenario
from strategies.strategy import Strategy, StrategyTypes


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

    def set_grid_params(self, grid_params: list[dict[str, Any]]):
        self.grid_params = grid_params

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
            [
                {"grid_num": k, "param_name": v["param_name"]}
                for k, v in self.results.items()
            ]
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
