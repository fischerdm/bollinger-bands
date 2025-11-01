# import pandas as pd
# from bollinger_bands.data.fetcher import DataFetcher
# from bollinger_bands.visualization.plotter import Plotter

# class BollingerBandsAnalyzer:
#     """Calculates Bollinger Bands for a given ticker."""

#     def __init__(self, ticker: str, start_date: str = '1990-01-01', end_date: str = '2025-10-21'):
#         if not ticker:
#             raise ValueError("Ticker cannot be empty.")
#         self.ticker = ticker
#         self.start_date = start_date
#         self.end_date = end_date
#         self.data_fetcher = DataFetcher()
#         self.monthly_data = None

#     def fetch_data(self) -> pd.DataFrame:
#         """Fetches and resamples data for the ticker."""
#         try:
#             daily_data = self.data_fetcher.fetch_daily_data([self.ticker], self.start_date, self.end_date)
#             self.monthly_data = self.data_fetcher.resample_to_monthly(daily_data)
#             return self.monthly_data
#         except Exception as e:
#             raise RuntimeError(f"Failed to fetch data: {e}")

#     def calculate_bollinger_bands(self, window: int = 20) -> pd.DataFrame:
#         """Calculates Bollinger Bands for the given window."""
#         if self.monthly_data is None:
#             self.fetch_data()

#         if self.monthly_data.empty:
#             raise ValueError("No monthly data available for Bollinger Bands calculation.")

#         self.monthly_data[f'middle_bb_{window}m'] = self.monthly_data[self.ticker].rolling(window=window).mean()
#         self.monthly_data[f'std_dev_{window}m'] = self.monthly_data[self.ticker].rolling(window=window).std()
#         self.monthly_data[f'upper_bb_{window}m'] = self.monthly_data[f'middle_bb_{window}m'] + (self.monthly_data[f'std_dev_{window}m'] * 2)
#         self.monthly_data[f'lower_bb_{window}m'] = self.monthly_data[f'middle_bb_{window}m'] - (self.monthly_data[f'std_dev_{window}m'] * 2)
#         return self.monthly_data


class BollingerBands:
    def __init__(self, window=20, num_std=2):
        self.window = window
        self.num_std = num_std
    
    def calculate(self, data):
        """Calculate Bollinger Bands"""
        sma = data['Close'].rolling(window=self.window).mean()
        std = data['Close'].rolling(window=self.window).std()
        
        upper_band = sma + (std * self.num_std)
        lower_band = sma - (std * self.num_std)
        
        return {
            'middle': sma,
            'upper': upper_band,
            'lower': lower_band
        }