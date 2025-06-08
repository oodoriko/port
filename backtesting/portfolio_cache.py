import hashlib
import json
import os
import pickle
from datetime import datetime

import pandas as pd

from backtesting.backtest import Backtest
from config import Benchmarks, StrategyTypes
from portfolio.constraints import Constraints
from portfolio.portfolio import Portfolio


class PortfolioCache:
    """
    A caching system for Portfolio objects to avoid re-running expensive backtests.

    Features:
    - Save/load complete portfolio objects with all historical data
    - Metadata tracking for cache management
    - Compression for large portfolio objects
    - Validation to ensure cache integrity
    """

    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            # Use portfolio_cache directory relative to this file's location
            cache_dir = os.path.join(os.path.dirname(__file__), "portfolio_cache")
        self.cache_dir = cache_dir
        self.metadata_file = os.path.join(cache_dir, "cache_metadata.json")
        self._ensure_cache_dir()
        self._load_metadata()

    def _ensure_cache_dir(self):
        """Create cache directory if it doesn't exist"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def _load_metadata(self):
        """Load cache metadata"""
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, "r") as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {}

    def _save_metadata(self):
        """Save cache metadata"""
        with open(self.metadata_file, "w") as f:
            json.dump(self.metadata, f, indent=2, default=str)

    def _serialize_constraints(self, constraints):
        """Properly serialize constraints object to dict"""
        if constraints is None:
            return None
        if isinstance(constraints, Constraints):
            return constraints.list_constraints()
        return constraints

    def _serialize_setup(self, setup):
        """Properly serialize setup dict, converting enum objects to strings"""
        if setup is None:
            return None

        serialized_setup = {}
        for key, value in setup.items():
            if hasattr(value, "value"):  # Handle enum objects
                if isinstance(value, list):
                    serialized_setup[key] = [
                        item.value if hasattr(item, "value") else item for item in value
                    ]
                else:
                    serialized_setup[key] = value.value
            elif isinstance(value, list):
                serialized_setup[key] = [
                    item.value if hasattr(item, "value") else item for item in value
                ]
            else:
                serialized_setup[key] = value
        return serialized_setup

    def _generate_long_name(
        self,
        portfolio_name: str,
        benchmark: Benchmarks,
        start_date: str = "",
        end_date: str = "",
        strategies: list[StrategyTypes] = [],
        constraints: Constraints = None,
        setup: dict = None,
    ) -> str:
        """Generate a unique cache key for the portfolio configuration"""
        # Create a hash-friendly string representation
        config_str = f"{portfolio_name}_{benchmark.value}_{start_date}_{end_date}"
        config_str += f"_{'_'.join([s.value for s in strategies])}"

        if constraints:
            constraints_dict = self._serialize_constraints(constraints)
            config_str += f"_constraints_{hash(str(sorted(constraints_dict.items())))}"
        if setup:
            setup_dict = self._serialize_setup(setup)
            config_str += f"_setup_{hash(str(sorted(setup_dict.items())))}"

        return config_str.replace("-", "_").replace(":", "_")

    def save_portfolio(
        self,
        portfolio: Portfolio,
        portfolio_name: str = None,
        benchmark: Benchmarks = None,
        constraints: dict = None,
        setup: dict = None,
        description: str = "",
    ) -> str:
        # Extract data from portfolio if not provided
        portfolio_name = portfolio_name or portfolio.name
        benchmark = benchmark or portfolio.benchmark
        constraints = constraints or portfolio.constraints
        setup = setup or portfolio.setup

        portfolio_long_name = self._generate_long_name(
            portfolio_name, benchmark, "", "", [], constraints, setup
        )
        cache_key = hashlib.sha256(portfolio_long_name.encode()).hexdigest()[:10]

        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")

        # Save the portfolio object
        with open(cache_file, "wb") as f:
            pickle.dump(portfolio, f)

        # Update metadata with properly serialized data
        self.metadata[cache_key] = {
            "portfolio_name": portfolio_name,
            "benchmark": benchmark.value,
            "start_date": "",
            "end_date": "",
            "strategies": [],
            "constraints": self._serialize_constraints(constraints),
            "setup": self._serialize_setup(setup),
            "description": description,
            "created_at": datetime.now().isoformat(),
            "file_path": cache_file,
            "file_size_mb": round(os.path.getsize(cache_file) / (1024 * 1024), 2),
        }

        self._save_metadata()

        print(f"Portfolio saved to cache with key: {cache_key}")
        print(f"File size: {self.metadata[cache_key]['file_size_mb']} MB")

        return cache_key

    def save_backtest(
        self,
        backtest: Backtest,
        description: str = "",
    ) -> str:
        portfolio = backtest.get_portfolio()
        portfolio_name = portfolio.name
        benchmark = portfolio.benchmark
        start_date = backtest.start_date
        end_date = backtest.end_date
        strategies = backtest.strategies
        constraints = portfolio.constraints
        setup = portfolio.setup

        portfolio_long_name = self._generate_long_name(
            portfolio_name, benchmark, start_date, end_date, strategies, constraints, setup
        )
        cache_key = hashlib.sha256(portfolio_long_name.encode()).hexdigest()[:10]

        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")

        # Save the backtest object
        with open(cache_file, "wb") as f:
            pickle.dump(backtest, f)

        # Update metadata with properly serialized data
        self.metadata[cache_key] = {
            "portfolio_name": portfolio_name,
            "benchmark": benchmark.value,
            "start_date": start_date,
            "end_date": end_date,
            "strategies": [s.value for s in strategies],
            "constraints": self._serialize_constraints(constraints),
            "setup": self._serialize_setup(setup),
            "description": description,
            "created_at": datetime.now().isoformat(),
            "file_path": cache_file,
            "file_size_mb": round(os.path.getsize(cache_file) / (1024 * 1024), 2),
        }

        self._save_metadata()

        print(f"Backtest saved to cache with key: {cache_key}")
        print(f"File size: {self.metadata[cache_key]['file_size_mb']} MB")

        return cache_key

    def load_cache(self, cache_key: str) -> Portfolio | Backtest:
        if cache_key not in self.metadata:
            raise KeyError(
                f"Cache key '{cache_key}' not found. Available keys: {list(self.metadata.keys())}"
            )

        cache_file = self.metadata[cache_key]["file_path"]

        if not os.path.exists(cache_file):
            raise FileNotFoundError(f"Cache file not found: {cache_file}")

        with open(cache_file, "rb") as f:
            cached_object = pickle.load(f)

        print(f"Loaded from cache: {cache_key}")
        return cached_object

    def list_cached_objects(self) -> pd.DataFrame:
        """List all cached objects with their metadata"""
        if not self.metadata:
            print("No cached objects found.")
            return pd.DataFrame()

        df = pd.DataFrame.from_dict(self.metadata, orient="index")
        df.index.name = "cache_key"
        return df

    def delete_cache(self, cache_key: str):
        """Delete a specific cached object"""
        if cache_key not in self.metadata:
            raise KeyError(f"Cache key '{cache_key}' not found")

        cache_file = self.metadata[cache_key]["file_path"]
        if os.path.exists(cache_file):
            os.remove(cache_file)

        del self.metadata[cache_key]
        self._save_metadata()

        print(f"Deleted cache: {cache_key}")

    def clear_all_cache(self):
        """Clear all cached objects"""
        for cache_key in list(self.metadata.keys()):
            self.delete_cache(cache_key)
        print("All cache cleared.")

    def get_cache_info(self, cache_key: str) -> dict:
        """Get detailed information about a cached object"""
        if cache_key not in self.metadata:
            raise KeyError(f"Cache key '{cache_key}' not found")

        return self.metadata[cache_key]

    def repair_metadata(self):
        """Repair metadata entries that have improperly serialized constraints"""
        updated = False
        for cache_key, metadata in self.metadata.items():
            if (
                isinstance(metadata.get("constraints"), str)
                and "object at" in metadata["constraints"]
            ):
                # Try to load the actual object and re-serialize constraints
                try:
                    cached_object = self.load_cache(cache_key)
                    if hasattr(cached_object, "get_portfolio"):
                        # It's a backtest
                        portfolio = cached_object.get_portfolio()
                    else:
                        # It's a portfolio
                        portfolio = cached_object

                    metadata["constraints"] = self._serialize_constraints(portfolio.constraints)
                    metadata["setup"] = self._serialize_setup(portfolio.setup)
                    updated = True
                    print(f"Repaired metadata for cache key: {cache_key}")
                except Exception as e:
                    print(f"Could not repair cache key {cache_key}: {e}")

        if updated:
            self._save_metadata()
            print("Metadata repair completed.")
        else:
            print("No metadata repairs needed.")


def cache_portfolio(
    portfolio: Portfolio,
    description: str = "",
    cache_dir: str = None,
) -> tuple[Portfolio, str]:
    print(f"Caching portfolio: {portfolio.name}")
    cache = PortfolioCache(cache_dir)

    cache_key = cache.save_portfolio(portfolio, description)
    print(f"Cached portfolio with key: {cache_key}")
    return cache_key


def cache_backtest(
    backtest: Backtest,
    description: str = "",
    cache_dir: str = None,
) -> tuple[Portfolio, str]:
    # Cache the portfolio
    cache = PortfolioCache(cache_dir)
    cache_key = cache.save_backtest(backtest, description)
    print(f"Cached backtest with key: {cache_key}")
    return cache_key


def load_cached_object(cache_key: str, cache_dir: str = None) -> Portfolio | Backtest:
    cache = PortfolioCache(cache_dir)
    return cache.load_cache(cache_key)


def list_cached_objects(cache_dir: str = None) -> pd.DataFrame:
    cache = PortfolioCache(cache_dir)
    return cache.list_cached_objects()


def repair_cache_metadata(cache_dir: str = None) -> None:
    """Utility function to repair cache metadata with improperly serialized constraints"""
    cache = PortfolioCache(cache_dir)
    cache.repair_metadata()
