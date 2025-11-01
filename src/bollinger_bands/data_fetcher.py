import yfinance as yf
import pandas as pd

class DataFetcher:
    """Fetches and resamples financial data from Yahoo Finance."""

    def fetch_daily_data(self, tickers: list, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetches daily adjusted close prices for the given tickers."""
        if not tickers:
            raise ValueError("No tickers provided.")

        try:
            # Download data - auto_adjust=True means 'Close' is already adjusted
            daily_data = yf.download(tickers, start=start_date, end=end_date, 
                                    progress=False, auto_adjust=True)

            if daily_data.empty:
                raise ValueError(f"No data found for tickers: {tickers}.")

            # Handle single ticker case
            if len(tickers) == 1:
                # With auto_adjust=True, use 'Close' instead of 'Adj Close'
                if isinstance(daily_data.columns, pd.MultiIndex):
                    if 'Close' in daily_data.columns.get_level_values(0):
                        daily_data = daily_data['Close']
                else:
                    if 'Close' in daily_data.columns:
                        daily_data = daily_data[['Close']]
                    else:
                        raise ValueError("No 'Close' column found.")
                
                # Rename to ticker name
                daily_data.columns = tickers
            
            # Handle multiple tickers case
            else:
                if isinstance(daily_data.columns, pd.MultiIndex):
                    if 'Close' in daily_data.columns.get_level_values(0):
                        daily_data = daily_data['Close']
                    else:
                        raise ValueError("No 'Close' column found.")
                else:
                    raise ValueError("Unexpected column structure for multiple tickers.")

            return daily_data
            
        except Exception as e:
            raise RuntimeError(f"Failed to fetch data: {e}")

    def resample_to_monthly(self, daily_data: pd.DataFrame) -> pd.DataFrame:
        """Resamples daily data to monthly closing prices."""
        if daily_data.empty:
            raise ValueError("No daily data provided for resampling.")
        return daily_data.resample('M').last()