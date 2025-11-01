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
        
    def fetch_ohlc_data(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetches OHLC data for a single ticker."""
        try:
            data = yf.download(ticker, start=start_date, end=end_date, 
                            progress=False, auto_adjust=True)
            
            if data.empty:
                raise ValueError(f"No data found for ticker: {ticker}")
            
            ohlc_data = data[['Open', 'High', 'Low', 'Close']].copy()
            
            # Flatten MultiIndex columns if present
            if isinstance(ohlc_data.columns, pd.MultiIndex):
                ohlc_data.columns = ohlc_data.columns.get_level_values(0)
            
            # Store ticker as attribute (metadata)
            ohlc_data.attrs['ticker'] = ticker
            
            return ohlc_data
        
        except Exception as e:
            raise RuntimeError(f"Failed to fetch OHLC data: {e}")

    def resample_to_monthly(self, daily_data: pd.DataFrame) -> pd.DataFrame:
        """Resamples daily data to monthly closing prices."""
        if daily_data.empty:
            raise ValueError("No daily data provided for resampling.")
        return daily_data.resample('M').last()