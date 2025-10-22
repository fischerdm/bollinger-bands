import pandas as pd
from data_fetcher import DataFetcher
from plotter import Plotter

class RelativeStrengthAnalyzer:
    """Calculates relative strength between a ticker and a benchmark."""

    def __init__(self, ticker: str, benchmark: str, start_date: str = '1990-01-01', end_date: str = '2025-10-21'):
        self.ticker = ticker
        self.benchmark = benchmark
        self.start_date = start_date
        self.end_date = end_date
        self.data_fetcher = DataFetcher()
        self.plotter = Plotter()
        self.monthly_data = None

    def fetch_data(self) -> pd.DataFrame:
        """Fetches and resamples data for both ticker and benchmark."""
        daily_data = self.data_fetcher.fetch_daily_data([self.ticker, self.benchmark], self.start_date, self.end_date)
        self.monthly_data = self.data_fetcher.resample_to_monthly(daily_data)
        return self.monthly_data

    def calculate_relative_strength(self) -> pd.DataFrame:
        """Calculates relative strength (ticker / benchmark)."""
        if self.monthly_data is None:
            self.fetch_data()

        self.monthly_data['relative_strength'] = self.monthly_data[self.ticker] / self.monthly_data[self.benchmark]
        return self.monthly_data

    def plot_relative_strength(self) -> None:
        """Plots relative strength over time."""
        if self.monthly_data is None:
            self.fetch_data()
        self.plotter.plot_relative_strength(self.monthly_data, self.ticker, self.benchmark)
