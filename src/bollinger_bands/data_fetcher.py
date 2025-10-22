import yfinance as yf
import pandas as pd

class DataFetcher:
    """Fetches and resamples financial data from Yahoo Finance."""

    def fetch_daily_data(self, tickers: list, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetches daily adjusted close prices for the given tickers."""
        if not tickers:
            raise ValueError("No tickers provided.")

        try:
            daily_data = yf.download(tickers, start=start_date, end=end_date)['Adj Close']
            if daily_data.empty:
                raise ValueError(f"No data found for tickers: {tickers}.")
            daily_data.columns = tickers
            return daily_data
        except Exception as e:
            raise RuntimeError(f"Error downloading data: {e}")

    def resample_to_monthly(self, daily_data: pd.DataFrame) -> pd.DataFrame:
        """Resamples daily data to monthly closing prices."""
        if daily_data.empty:
            raise ValueError("No daily data provided for resampling.")
        return daily_data.resample('M').last()
