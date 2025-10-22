import pandas as pd
from data_fetcher import DataFetcher
from plotter import Plotter

class BollingerBandsAnalyzer:
    """Calculates Bollinger Bands for a given ticker."""

    def __init__(self, ticker: str, start_date: str = '1990-01-01', end_date: str = '2025-10-21'):
        self.ticker = ticker
        self.start_date = start_date
        self.end_date = end_date
        self.data_fetcher = DataFetcher()
        self.plotter = Plotter()
        self.monthly_data = None

    def fetch_data(self) -> pd.DataFrame:
        """Fetches and resamples data for the ticker."""
        daily_data = self.data_fetcher.fetch_daily_data([self.ticker], self.start_date, self.end_date)
        self.monthly_data = self.data_fetcher.resample_to_monthly(daily_data)
        return self.monthly_data

    def calculate_bollinger_bands(self, window: int = 20) -> pd.DataFrame:
        """Calculates Bollinger Bands for the given window."""
        if self.monthly_data is None:
            self.fetch_data()

        self.monthly_data[f'middle_bb_{window}m'] = self.monthly_data[self.ticker].rolling(window=window).mean()
        self.monthly_data[f'std_dev_{window}m'] = self.monthly_data[self.ticker].rolling(window=window).std()
        self.monthly_data[f'upper_bb_{window}m'] = self.monthly_data[f'middle_bb_{window}m'] + (self.monthly_data[f'std_dev_{window}m'] * 2)
        self.monthly_data[f'lower_bb_{window}m'] = self.monthly_data[f'middle_bb_{window}m'] - (self.monthly_data[f'std_dev_{window}m'] * 2)
        return self.monthly_data

    def plot_bollinger_bands(self, windows: list = [20, 40]) -> None:
        """Plots Bollinger Bands for the specified windows."""
        if self.monthly_data is None:
            self.fetch_data()
        self.plotter.plot_bollinger_bands(self.monthly_data, self.ticker, windows)
