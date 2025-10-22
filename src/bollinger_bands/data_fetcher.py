import yfinance as yf
import pandas as pd

class DataFetcher:
    """Fetches and resamples financial data from Yahoo Finance."""

    def __init__(self):
        pass

    def fetch_daily_data(self, tickers: list, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetches daily adjusted close prices for the given tickers."""
        try:
            daily_data = yf.download(tickers, start=start_date, end=end_date)['Adj Close']
            daily_data.columns = tickers
            return daily_data
        except Exception as e:
            print(f"Error downloading data: {e}")
            return None

    def resample_to_monthly(self, daily_data: pd.DataFrame) -> pd.DataFrame:
        """Resamples daily data to monthly closing prices."""
        return daily_data.resample('M').last()
