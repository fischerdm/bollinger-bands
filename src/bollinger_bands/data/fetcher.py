"""
Enhanced Data Fetcher with Storage Integration
Extends the original fetcher with smart caching and incremental updates.
"""

import yfinance as yf
import pandas as pd
from typing import Dict, List, Optional
import logging
from bollinger_bands.data.storage_manager import DataStorageManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataFetcher:
    """Fetches and resamples financial data from Yahoo Finance."""

    def __init__(self, storage_manager: Optional[DataStorageManager] = None):
        """
        Initialize the data fetcher.
        
        Args:
            storage_manager: Optional DataStorageManager for caching
        """
        self.storage_manager = storage_manager

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
        
    def fetch_ohlc_data(self, ticker: str, start_date: str, end_date: str, 
                       use_cache: bool = True) -> pd.DataFrame:
        """
        Fetches OHLC data for a single ticker with smart caching.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            use_cache: Whether to use cached data and merge with new data
            
        Returns:
            DataFrame with OHLC data
        """
        # If caching is disabled or no storage manager, fetch directly
        if not use_cache or self.storage_manager is None:
            return self._fetch_ohlc_direct(ticker, start_date, end_date)
        
        # Check for missing date ranges
        missing_ranges = self.storage_manager.get_missing_date_ranges(
            ticker, start_date, end_date
        )
        
        # Load existing data
        existing_data = self.storage_manager.load_ticker_data(ticker)
        
        # If no missing ranges, return existing data
        if not missing_ranges:
            if existing_data is not None:
                # Filter to requested date range
                mask = (existing_data.index >= start_date) & (existing_data.index <= end_date)
                filtered_data = existing_data[mask].copy()
                filtered_data.attrs['ticker'] = ticker
                return filtered_data
            else:
                # This shouldn't happen, but fetch directly if it does
                return self._fetch_ohlc_direct(ticker, start_date, end_date)
        
        # Fetch missing data ranges
        all_new_data = []
        for range_start, range_end in missing_ranges:
            logger.info(f"Fetching {ticker} data from {range_start} to {range_end}")
            new_data = self._fetch_ohlc_direct(ticker, range_start, range_end)
            if not new_data.empty:
                all_new_data.append(new_data)
        
        # Merge all new data
        if all_new_data:
            combined_new_data = pd.concat(all_new_data)
            
            # Merge with existing data
            merged_data = self.storage_manager.merge_data(existing_data, combined_new_data)
            
            # Get currency for this ticker
            ticker_currencies = self.storage_manager.get_ticker_currencies()
            currency = ticker_currencies.get(ticker, 'USD')
            
            # Save merged data (will auto-create USD version if needed)
            self.storage_manager.save_ticker_data(ticker, merged_data, currency=currency)
            
            # Filter to requested date range
            mask = (merged_data.index >= start_date) & (merged_data.index <= end_date)
            filtered_data = merged_data[mask].copy()
            filtered_data.attrs['ticker'] = ticker
            return filtered_data
        
        # If we couldn't fetch new data but have existing data, return that
        if existing_data is not None:
            mask = (existing_data.index >= start_date) & (existing_data.index <= end_date)
            filtered_data = existing_data[mask].copy()
            filtered_data.attrs['ticker'] = ticker
            return filtered_data
        
        # Last resort: direct fetch
        return self._fetch_ohlc_direct(ticker, start_date, end_date)
    
    def _fetch_ohlc_direct(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Direct fetch of OHLC data without caching (original implementation).
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            DataFrame with OHLC data
        """
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
    
    def fetch_and_store_all_tickers(self, start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """
        Fetch and store data for all enabled tickers.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            Dictionary mapping ticker symbols to DataFrames
        """
        if self.storage_manager is None:
            raise ValueError("Storage manager required for this operation")
        
        tickers = self.storage_manager.get_enabled_tickers()
        ticker_data = {}
        
        logger.info(f"Fetching data for {len(tickers)} tickers...")
        
        for ticker_info in tickers:
            ticker = ticker_info['symbol']
            logger.info(f"Processing {ticker}...")
            
            try:
                data = self.fetch_ohlc_data(ticker, start_date, end_date, use_cache=True)
                ticker_data[ticker] = data
            except Exception as e:
                logger.error(f"Failed to fetch {ticker}: {e}")
                # Continue with other tickers even if one fails
                continue
        
        logger.info(f"Successfully fetched data for {len(ticker_data)} tickers")
        return ticker_data
    
    def update_all_tickers(self, end_date: str) -> Dict[str, pd.DataFrame]:
        """
        Update all tickers with latest data up to end_date.
        Only fetches missing dates.
        Automatically creates/updates USD-normalized versions for non-USD tickers.
        
        Args:
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            Dictionary mapping ticker symbols to DataFrames (original currency)
        """
        if self.storage_manager is None:
            raise ValueError("Storage manager required for this operation")
        
        tickers = self.storage_manager.get_enabled_tickers()
        ticker_data = {}
        
        logger.info(f"Updating {len(tickers)} tickers...")
        
        for ticker_info in tickers:
            ticker = ticker_info['symbol']
            currency = ticker_info.get('currency', 'USD')
            
            try:
                # Get existing data range
                date_range = self.storage_manager.get_data_date_range(ticker)
                
                if date_range is None:
                    # No existing data - use default start date
                    start_date = self.storage_manager.config['data_settings']['default_start_date']
                    logger.info(f"{ticker}: No existing data, fetching from {start_date}")
                else:
                    # Start from existing data start date
                    start_date = date_range[0].strftime('%Y-%m-%d')
                
                # Fetch with caching (only missing dates will be downloaded)
                data = self.fetch_ohlc_data(ticker, start_date, end_date, use_cache=True)
                ticker_data[ticker] = data
                
                # Auto-create USD version if currency is not USD
                # This happens automatically via save_ticker_data with also_save_usd=True
                # (The save happens inside fetch_ohlc_data when use_cache=True)
                
            except Exception as e:
                logger.error(f"Failed to update {ticker}: {e}")
                # Try to load existing data if update fails
                existing = self.storage_manager.load_ticker_data(ticker)
                if existing is not None:
                    ticker_data[ticker] = existing
                continue
        
        logger.info(f"Update complete for {len(ticker_data)} tickers")
        logger.info("Note: USD-normalized versions auto-created for non-USD tickers")
        return ticker_data

    def resample_to_monthly(self, daily_data: pd.DataFrame) -> pd.DataFrame:
        """Resamples daily data to monthly closing prices."""
        if daily_data.empty:
            raise ValueError("No daily data provided for resampling.")
        return daily_data.resample('M').last()