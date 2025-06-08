"""
Everything probably has to be numpy arrays implicitly indexed by dates when data gets too big... ugh
"""

import json
import os
import pickle
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf

from config import DEFAULT_PRODUCT_ATTRIBUTES, END_DATE, START_DATE, Benchmarks

RATE_LIMITING_AVAILABLE = True


class DataCacher:
    def __init__(self, cache_dir=None, cache_file="cache.pkl"):
        if cache_dir is None:
            cache_dir = os.path.join(os.path.dirname(__file__), "data_cache")
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, cache_file)
        self.cache = self.load_cache()
        os.makedirs(cache_dir, exist_ok=True)

    def load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "rb") as f:
                    return pickle.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}")
        return {}

    def save_cache(self):
        try:
            with open(self.cache_file, "wb") as f:
                pickle.dump(self.cache, f)
            print(f"Cached {len(self.cache)} entries")
        except Exception as e:
            print(f"Error saving cache: {e}")

    def is_cached(self, key):
        return key in self.cache  # key is ticker

    def get_from_cache(self, key) -> dict:
        return {k: self.cache.get(k) for k in key} if isinstance(key, list) else self.cache.get(key)

    def add_to_cache(self, key=None, data=None):
        if key is None and isinstance(data, dict):
            self.cache.update(data)
        else:
            self.cache[key] = data


class YFinance:
    @staticmethod
    def get_price_data(tickers, start_date=None, end_date=None, interval="1d", max_rows=50000):
        # only download daily
        if not start_date or not end_date:
            start_date = START_DATE
            end_date = END_DATE

        if isinstance(tickers, str):
            tickers = [tickers]

        days = (
            datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")
        ).days
        batch_size = max_rows // days  # max 50000 return rows per batch

        print(f"Starting {len(tickers) // batch_size} batches")
        results = {}
        for i in range(0, len(tickers), batch_size):
            batch_tickers = tickers[i : i + batch_size]
            try:
                prices = YFinance.download_price_batch(
                    batch_tickers, start_date, end_date, interval
                )
                results.update(prices)
            except Exception as e:
                print(f"Error downloading price data: {e}")
                continue
        return results

    @staticmethod
    def download_price_batch(tickers, start_date, end_date, interval):
        results = {}
        prices = yf.download(
            tickers,
            start=start_date,
            end=end_date,
            keepna=True,
            interval=interval,
            group_by="ticker",
            progress=False,
        )
        if prices is not None and not prices.empty:
            tickers = prices.columns.get_level_values(0).unique().tolist()
            for ticker in tickers:
                results[ticker] = prices[ticker].reset_index().to_dict("list")
        return results

    @staticmethod
    def get_product_data(tickers, attributes=DEFAULT_PRODUCT_ATTRIBUTES):
        """for now, use to exclude non-US tickers and calculate sector exposure, mkt cap constraints"""
        if isinstance(tickers, str):
            tickers = [tickers]

        product_data = yf.Tickers(tickers).tickers
        res = {}
        for ticker in tickers:  # some tickers are bmk composites, e.g. BRK, BF
            res[ticker] = {}
            for att in attributes:
                try:
                    res[ticker][att] = product_data[ticker].info[att]
                except Exception as e:
                    print("Cannot find", ticker, att, e)
                    continue
        return res


class PriceData(DataCacher):
    def __init__(self):
        super().__init__(cache_file="price_cache.pkl")

    def get_data(self, tickers, start_date=None, end_date=None) -> pd.DataFrame:
        if not start_date:
            start_date = START_DATE
        if not end_date:
            end_date = END_DATE

        cache_invalid = self._is_date_range_invalid(start_date, end_date)

        if cache_invalid:
            print(
                f"Requested date range ({start_date} to {end_date}) exceeds cached range. Redownloading all data..."
            )
            self.cache = {}
            price_data = YFinance.get_price_data(
                tickers=tickers, start_date=start_date, end_date=end_date
            )
            self.add_to_cache(data=price_data)
            self._store_date_range(start_date, end_date)
            self.save_cache()
        else:
            new_tickers = [ticker for ticker in tickers if not self.is_cached(ticker)]

            if new_tickers:
                price_data = YFinance.get_price_data(
                    tickers=new_tickers, start_date=start_date, end_date=end_date
                )
                self.add_to_cache(data=price_data)
                self.save_cache()

        results_dict = self.get_from_cache(tickers)
        dates = results_dict[tickers[0]]["Date"]  # assume all tickers have the same dates
        return {
            "open": pd.DataFrame(
                {ticker: price["Open"] for ticker, price in results_dict.items()}
            ).assign(Date=dates),
            "close": pd.DataFrame(
                {ticker: price["Close"] for ticker, price in results_dict.items()}
            ).assign(Date=dates),
            "volume": pd.DataFrame(
                {ticker: price["Volume"] for ticker, price in results_dict.items()}
            ).assign(Date=dates),
        }

    def _is_date_range_invalid(self, start_date, end_date):
        cached_range = self.cache.get("_date_range")
        if not cached_range:
            return True

        cached_start = cached_range.get("start_date")
        cached_end = cached_range.get("end_date")

        if not cached_start or not cached_end:
            return True

        try:
            req_start = datetime.strptime(start_date, "%Y-%m-%d")
            req_end = datetime.strptime(end_date, "%Y-%m-%d")
            cache_start = datetime.strptime(cached_start, "%Y-%m-%d")
            cache_end = datetime.strptime(cached_end, "%Y-%m-%d")
            return req_start < cache_start or req_end > cache_end
        except:
            return True

    def _store_date_range(self, start_date, end_date):
        self.cache["_date_range"] = {"start_date": start_date, "end_date": end_date}


class ProductData(DataCacher):
    def __init__(self):
        super().__init__(cache_file="product_cache.pkl")

    def get_data(self, tickers) -> pd.DataFrame:
        new_tickers = [ticker for ticker in tickers if not self.is_cached(ticker)]

        if new_tickers:
            price_data = YFinance.get_product_data(new_tickers)
            self.add_to_cache(data=price_data)
            self.save_cache()
        result_dict = self.get_from_cache(tickers)
        return (
            pd.DataFrame(result_dict).T.reset_index(drop=False).rename(columns={"index": "ticker"})
        )


class BenchmarkData(DataCacher):
    def __init__(self):
        super().__init__(cache_file="benchmark_cache.pkl")

    def get_constituents(self, benchmark: Benchmarks) -> list:
        if self.is_cached(benchmark.value):
            cached_data = self.get_from_cache(benchmark.value)
            return cached_data.get("tickers", [])

        tickers = self._scrape_wikipedia_constituents(benchmark)

        if tickers:
            self.add_to_cache(key=benchmark.value, data={"tickers": tickers})
            self.save_cache()

        return tickers

    def _scrape_wikipedia_constituents(self, benchmark: Benchmarks) -> list:
        url_map = {
            Benchmarks.SP500: "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            Benchmarks.NASDAQ: "https://en.wikipedia.org/wiki/NASDAQ-100",
            Benchmarks.DOWJONES: "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average",
        }
        try:
            tables = pd.read_html(url_map[benchmark])
            for table in tables:
                if "Symbol" in table.columns or "Ticker" in table.columns:
                    symbol_col = "Symbol" if "Symbol" in table.columns else "Ticker"
                    tickers = table[symbol_col].dropna().tolist()
                    tickers = [str(ticker).strip() for ticker in tickers if str(ticker).strip()]
                    print(f"Scraped {len(tickers)} tickers for {benchmark.name} from Wikipedia")
                    return tickers

            print(f"Could not find symbol table for {benchmark.name} on Wikipedia")
            return []
        except Exception as e:
            print(f"Error scraping Wikipedia for {benchmark.name}: {e}")
            return []


def get_prices_by_dates(
    prices: pd.DataFrame,
    end_date: str = None,
    start_date: str = None,
    lookback_window: int = np.inf,
    lookahead_window: int = np.inf,
) -> pd.DataFrame:
    # window is easier bc i don't have to get exchange open dates
    # exclude current day to avoid lookahead bias
    if lookback_window != np.inf or lookahead_window != np.inf:
        if lookback_window != np.inf:
            return prices[prices.index < end_date].iloc[-lookback_window:]
        elif lookahead_window != np.inf:
            return prices[prices.index > start_date].iloc[:lookahead_window]
        return prices
    return prices[(prices.index >= start_date) & (prices.index <= end_date)]
