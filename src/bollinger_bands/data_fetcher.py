import yfinance as yf
import pandas as pd

# class DataFetcher:
#     """Fetches and resamples financial data from Yahoo Finance."""

#     def fetch_daily_data(self, tickers: list, start_date: str, end_date: str) -> pd.DataFrame:
#         """Fetches daily adjusted close prices for the given tickers."""
#         if not tickers:
#             raise ValueError("No tickers provided.")

#         try:
#             daily_data = yf.download(tickers, start=start_date, end=end_date)['Adj Close']
#             if daily_data.empty:
#                 raise ValueError(f"No data found for tickers: {tickers}.")
#             daily_data.columns = tickers
#             return daily_data
#         except Exception as e:
#             raise RuntimeError(f"Error downloading data: {e}")

#     def resample_to_monthly(self, daily_data: pd.DataFrame) -> pd.DataFrame:
#         """Resamples daily data to monthly closing prices."""
#         if daily_data.empty:
#             raise ValueError("No daily data provided for resampling.")
#         return daily_data.resample('M').last()

# class DataFetcher:
#     """Fetches and resamples financial data from Yahoo Finance."""

#     def fetch_daily_data(self, tickers: list, start_date: str, end_date: str) -> pd.DataFrame:
#         """Fetches daily adjusted close prices for the given tickers."""
#         if not tickers:
#             raise ValueError("No tickers provided.")

#         try:
#             daily_data = yf.download(tickers, start=start_date, end=end_date)
#             if daily_data.empty:
#                 raise ValueError(f"No data found for tickers: {tickers}.")

#             if len(tickers) == 1:
#                 # Single ticker: yfinance returns a DataFrame with 'Adj Close' as a column
#                 if 'Adj Close' in daily_data.columns:
#                     daily_data = daily_data[['Adj Close']]
#                 else:
#                     raise ValueError("No 'Adj Close' column found in the data.")
#             else:
#                 # Multiple tickers: yfinance returns a DataFrame with MultiIndex columns
#                 adj_close_cols = [col for col in daily_data.columns if 'Adj Close' in str(col)]
#                 if not adj_close_cols:
#                     raise ValueError("No 'Adj Close' columns found in the data.")
#                 daily_data = daily_data[adj_close_cols]
#             daily_data.columns = tickers  # Rename columns to ticker names
#             return daily_data
#         except Exception as e:
#             raise RuntimeError(f"Error downloading data: {e}")

#     def resample_to_monthly(self, daily_data: pd.DataFrame) -> pd.DataFrame:
#         """Resamples daily data to monthly closing prices."""
#         if daily_data.empty:
#             raise ValueError("No daily data provided for resampling.")
#         return daily_data.resample('M').last()

# class DataFetcher:
#     """Fetches and resamples financial data from Yahoo Finance."""

#     def fetch_daily_data(self, tickers: list, start_date: str, end_date: str) -> pd.DataFrame:
#         """Fetches daily adjusted close prices for the given tickers."""
#         if not tickers:
#             raise ValueError("No tickers provided.")

#         try:
#             daily_data = yf.download(tickers, start=start_date, end=end_date)

#             if daily_data.empty:
#                 raise ValueError(f"No data found for tickers: {tickers}.")

#             if isinstance(daily_data, pd.DataFrame):
#                 # For single ticker, yfinance returns a DataFrame with 'Adj Close' as a column
#                 if 'Adj Close' in daily_data.columns:
#                     daily_data = daily_data[['Adj Close']]
#                 else:
#                     # If 'Adj Close' is not found, try accessing the first level of columns
#                     if isinstance(daily_data.columns, pd.MultiIndex):
#                         adj_close_data = daily_data.xs('Adj Close', level=1, axis=1, drop_level=True)
#                         if not adj_close_data.empty:
#                             daily_data = adj_close_data
#                         else:
#                             raise ValueError("No 'Adj Close' data found in the DataFrame.")
#                     else:
#                         raise ValueError("No 'Adj Close' column found in the data.")
#             elif isinstance(daily_data, pd.Series):
#                 # If a Series is returned, convert it to a DataFrame
#                 daily_data = daily_data.to_frame(name=tickers[0])
#             else:
#                 raise ValueError("Unexpected data format returned by yfinance.")

#             daily_data.columns = tickers
#             return daily_data
#         except Exception as e:
#             raise RuntimeError(f"Error downloading data: {e}")

#     def resample_to_monthly(self, daily_data: pd.DataFrame) -> pd.DataFrame:
#         """Resamples daily data to monthly closing prices."""
#         if daily_data.empty:
#             raise ValueError("No daily data provided for resampling.")
#         return daily_data.resample('M').last()


# class DataFetcher:
#     """Fetches and resamples financial data from Yahoo Finance."""

#     def fetch_daily_data(self, tickers: list, start_date: str, end_date: str) -> pd.DataFrame:
#         """Fetches daily adjusted close prices for the given tickers."""
#         if not tickers:
#             raise ValueError("No tickers provided.")

#         try:
#             # Fetch data
#             daily_data = yf.download(tickers, start=start_date, end=end_date)

#             if daily_data.empty:
#                 raise ValueError(f"No data found for tickers: {tickers}.")

#             # For single ticker
#             if len(tickers) == 1:
#                 ticker = tickers[0]
#                 if isinstance(daily_data, pd.DataFrame):
#                     if 'Adj Close' in daily_data.columns:
#                         daily_data = daily_data[['Adj Close']]
#                     else:
#                         # If 'Adj Close' is not a column, it might be a MultiIndex
#                         if isinstance(daily_data.columns, pd.MultiIndex):
#                             adj_close = daily_data.xs('Adj Close', axis=1, level=1, drop_level=True)
#                             if not adj_close.empty:
#                                 daily_data = adj_close
#                             else:
#                                 raise ValueError("No 'Adj Close' data found.")
#                         else:
#                             raise ValueError("No 'Adj Close' column found.")
#                 elif isinstance(daily_data, pd.Series):
#                     daily_data = daily_data.to_frame(name='Adj Close')
#                 else:
#                     raise ValueError("Unexpected data format returned by yfinance.")
#                 daily_data.columns = [ticker]
#             # For multiple tickers
#             else:
#                 adj_close_cols = []
#                 for ticker in tickers:
#                     if f"{ticker} Adj Close" in daily_data.columns:
#                         adj_close_cols.append(f"{ticker} Adj Close")
#                     elif 'Adj Close' in daily_data.columns:
#                         adj_close_cols.append('Adj Close')
#                 if not adj_close_cols:
#                     raise ValueError("No 'Adj Close' columns found.")
#                 daily_data = daily_data[adj_close_cols]
#                 daily_data.columns = tickers

#             return daily_data
#         except Exception as e:
#             raise RuntimeError(f"Error downloading data: {e}")

#     def resample_to_monthly(self, daily_data: pd.DataFrame) -> pd.DataFrame:
#         """Resamples daily data to monthly closing prices."""
#         if daily_data.empty:
#             raise ValueError("No daily data provided for resampling.")
#         return daily_data.resample('M').last()
    


# class DataFetcher:
#     """Fetches and resamples financial data from Yahoo Finance."""

#     def fetch_daily_data(self, tickers: list, start_date: str, end_date: str) -> pd.DataFrame:
#         """Fetches daily adjusted close prices for the given tickers."""
#         if not tickers:
#             raise ValueError("No tickers provided.")

#         try:
#             daily_data = yf.download(tickers, start=start_date, end=end_date)

#             if daily_data.empty:
#                 raise ValueError(f"No data found for tickers: {tickers}.")

#             # For single ticker
#             if len(tickers) == 1:
#                 if 'Adj Close' in daily_data.columns:
#                     daily_data = daily_data[['Adj Close']]
#                 else:
#                     raise ValueError("No 'Adj Close' column found.")
#                 daily_data.columns = tickers
#             # For multiple tickers
#             else:
#                 adj_close_data = pd.DataFrame()
#                 for ticker in tickers:
#                     ticker_data = yf.download(ticker, start=start_date, end=end_date)
#                     if 'Adj Close' in ticker_data.columns:
#                         adj_close_data[ticker] = ticker_data['Adj Close']
#                     else:
#                         raise ValueError(f"No 'Adj Close' column found for ticker: {ticker}.")
#                 daily_data = adj_close_data
#             return daily_data
#         except Exception as e:
#             raise RuntimeError(f"Error downloading data: {e}")

#     def resample_to_monthly(self, daily_data: pd.DataFrame) -> pd.DataFrame:
#         """Resamples daily data to monthly closing prices."""
#         if daily_data.empty:
#             raise ValueError("No daily data provided for resampling.")
#         return daily_data.resample('M').last()


# def fetch_daily_data(self, tickers: list, start_date: str, end_date: str) -> pd.DataFrame:
#     """Fetches daily adjusted close prices for the given tickers."""
#     if not tickers:
#         raise ValueError("No tickers provided.")

#     try:
#         # Download data for all tickers at once
#         daily_data = yf.download(tickers, start=start_date, end=end_date, progress=False)

#         if daily_data.empty:
#             raise ValueError(f"No data found for tickers: {tickers}.")

#         # Handle single ticker case
#         if len(tickers) == 1:
#             # yfinance returns single-level columns for one ticker
#             if isinstance(daily_data.columns, pd.MultiIndex):
#                 # Multi-index case (shouldn't happen with single ticker, but just in case)
#                 if 'Adj Close' in daily_data.columns.get_level_values(0):
#                     daily_data = daily_data['Adj Close']
#             else:
#                 # Single-level columns
#                 if 'Adj Close' in daily_data.columns:
#                     daily_data = daily_data[['Adj Close']]
#                 else:
#                     raise ValueError("No 'Adj Close' column found.")
            
#             # Rename to ticker name
#             daily_data.columns = tickers
        
#         # Handle multiple tickers case
#         else:
#             # yfinance returns MultiIndex columns for multiple tickers
#             if isinstance(daily_data.columns, pd.MultiIndex):
#                 if 'Adj Close' in daily_data.columns.get_level_values(0):
#                     daily_data = daily_data['Adj Close']
#                 else:
#                     raise ValueError("No 'Adj Close' column found.")
#             else:
#                 raise ValueError("Unexpected column structure for multiple tickers.")

#         return daily_data
        
#     except Exception as e:
#         raise RuntimeError(f"Failed to fetch data: {e}")
    


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