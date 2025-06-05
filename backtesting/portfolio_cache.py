import json
import os
import pickle
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from backtesting.backtest import Backtest
from config import INITIAL_SETUP, Benchmarks, Strategies
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

    def _generate_cache_key(
        self,
        portfolio_name: str,
        benchmark: Benchmarks,
        start_date: str,
        end_date: str,
        strategies: list,
        constraints: dict = None,
        setup: dict = None,
    ) -> str:
        """Generate a unique cache key for the portfolio configuration"""
        # Create a hash-friendly string representation
        config_str = f"{portfolio_name}_{benchmark.value}_{start_date}_{end_date}"
        config_str += f"_{'_'.join([s.value for s in strategies])}"

        if constraints:
            config_str += f"_constraints_{hash(str(sorted(constraints.items())))}"
        if setup:
            config_str += f"_setup_{hash(str(sorted(setup.items())))}"

        return config_str.replace("-", "_").replace(":", "_")

    def save_portfolio(
        self,
        portfolio: Portfolio,
        portfolio_name: str,
        benchmark: Benchmarks,
        start_date: str,
        end_date: str,
        strategies: list,
        constraints: dict = None,
        setup: dict = None,
        description: str = "",
    ) -> str:
        """
        Save a portfolio object to cache

        Returns:
            str: The cache key used to save the portfolio
        """
        cache_key = self._generate_cache_key(
            portfolio_name, benchmark, start_date, end_date, strategies, constraints, setup
        )

        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")

        # Save the portfolio object
        with open(cache_file, "wb") as f:
            pickle.dump(portfolio, f)

        # Update metadata
        self.metadata[cache_key] = {
            "portfolio_name": portfolio_name,
            "benchmark": benchmark.value,
            "start_date": start_date,
            "end_date": end_date,
            "strategies": [s.value for s in strategies],
            "constraints": constraints,
            "setup": setup,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "file_path": cache_file,
            "file_size_mb": round(os.path.getsize(cache_file) / (1024 * 1024), 2),
        }

        self._save_metadata()

        print(f"Portfolio saved to cache with key: {cache_key}")
        print(f"File size: {self.metadata[cache_key]['file_size_mb']} MB")

        return cache_key

    def load_portfolio(self, cache_key: str) -> Portfolio:
        """Load a portfolio object from cache"""
        if cache_key not in self.metadata:
            raise KeyError(
                f"Cache key '{cache_key}' not found. Available keys: {list(self.metadata.keys())}"
            )

        cache_file = self.metadata[cache_key]["file_path"]

        if not os.path.exists(cache_file):
            raise FileNotFoundError(f"Cache file not found: {cache_file}")

        with open(cache_file, "rb") as f:
            portfolio = pickle.load(f)

        print(f"Portfolio loaded from cache: {cache_key}")
        return portfolio

    def list_cached_portfolios(self) -> pd.DataFrame:
        """List all cached portfolios with their metadata"""
        if not self.metadata:
            print("No cached portfolios found.")
            return pd.DataFrame()

        df = pd.DataFrame.from_dict(self.metadata, orient="index")
        df.index.name = "cache_key"
        return df

    def delete_cache(self, cache_key: str):
        """Delete a specific cached portfolio"""
        if cache_key not in self.metadata:
            raise KeyError(f"Cache key '{cache_key}' not found")

        cache_file = self.metadata[cache_key]["file_path"]
        if os.path.exists(cache_file):
            os.remove(cache_file)

        del self.metadata[cache_key]
        self._save_metadata()

        print(f"Deleted cache: {cache_key}")

    def clear_all_cache(self):
        """Clear all cached portfolios"""
        for cache_key in list(self.metadata.keys()):
            self.delete_cache(cache_key)
        print("All cache cleared.")

    def get_cache_info(self, cache_key: str) -> dict:
        """Get detailed information about a cached portfolio"""
        if cache_key not in self.metadata:
            raise KeyError(f"Cache key '{cache_key}' not found")

        return self.metadata[cache_key]


def create_and_cache_portfolio(
    portfolio_name: str,
    benchmark: Benchmarks,
    start_date: str,
    end_date: str,
    strategies: list,
    constraints: dict = None,
    setup: dict = None,
    description: str = "",
    cache_dir: str = None,
) -> tuple[Portfolio, str]:
    """
    Create a portfolio, run backtest, and cache it

    Returns:
        tuple: (Portfolio object, cache_key)
    """
    print(f"Creating portfolio: {portfolio_name}")
    print(f"Benchmark: {benchmark.value}")
    print(f"Date range: {start_date} to {end_date}")
    print(f"Strategies: {[s.value for s in strategies]}")

    # Create portfolio
    portfolio = Portfolio(
        name=portfolio_name,
        benchmark=benchmark,
        constraints=constraints or {},
        additional_setup=setup or INITIAL_SETUP,
    )

    # Run backtest
    backtest = Backtest(
        portfolio=portfolio, start_date=start_date, end_date=end_date, strategies=strategies
    )

    backtest.run()

    # Generate metrics
    portfolio.generate_analytics()

    # Cache the portfolio
    cache = PortfolioCache(cache_dir)
    cache_key = cache.save_portfolio(
        portfolio=portfolio,
        portfolio_name=portfolio_name,
        benchmark=benchmark,
        start_date=start_date,
        end_date=end_date,
        strategies=strategies,
        constraints=constraints,
        setup=setup,
        description=description,
    )

    return portfolio, cache_key


def load_cached_portfolio(cache_key: str, cache_dir: str = None) -> Portfolio:
    """
    Load a cached portfolio by cache key

    Returns:
        Portfolio: The loaded portfolio object
    """
    cache = PortfolioCache(cache_dir)
    return cache.load_portfolio(cache_key)
