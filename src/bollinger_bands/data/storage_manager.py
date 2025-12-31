"""
Data Storage Manager with Currency Normalization

Handles saving, loading, and merging of historical stock data.
Stores both original currency data AND USD-normalized data for metrics.
"""

import os
import pandas as pd
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataStorageManager:
    """Manages local storage and retrieval of stock data with currency support."""
    
    def __init__(self, config_path: str = "config/tickers.yaml", currency_converter=None):
        """
        Initialize the data storage manager.
        
        Args:
            config_path: Path to the ticker configuration YAML file
            currency_converter: CurrencyConverter instance for normalization
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.data_dir = Path(self.config['data_settings']['data_directory'])
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Currency conversion support
        self.currency_converter = currency_converter
        self.usd_data_dir = self.data_dir / "usd_normalized"
        self.usd_data_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Config file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing config file: {e}")
            raise
    
    def get_enabled_tickers(self) -> List[Dict[str, str]]:
        """
        Get list of enabled tickers from configuration.
        
        Returns:
            List of dicts with 'symbol', 'name', and 'currency' keys
        """
        tickers = []
        for ticker in self.config['tickers']:
            if ticker.get('enabled', True):  # Default to enabled if not specified
                tickers.append({
                    'symbol': ticker['symbol'],
                    'name': ticker['name'],
                    'currency': ticker.get('currency', 'USD')  # Default to USD
                })
        return tickers
    
    def get_ticker_currencies(self) -> Dict[str, str]:
        """
        Get mapping of ticker symbols to their currencies.
        
        Returns:
            Dictionary of {symbol: currency}
        """
        ticker_currencies = {}
        for ticker in self.config['tickers']:
            if ticker.get('enabled', True):
                ticker_currencies[ticker['symbol']] = ticker.get('currency', 'USD')
        return ticker_currencies
    
    def get_data_date_range(self, ticker_symbol: str) -> Optional[tuple]:
        """
        Get the date range of existing data for a ticker.
        
        Args:
            ticker_symbol: Stock ticker symbol
            
        Returns:
            Tuple of (start_date, end_date) as Timestamps, or None if no data
        """
        data = self.load_ticker_data(ticker_symbol, prefer_usd=False)
        
        if data is None or data.empty:
            return None
        
        return (data.index.min(), data.index.max())
    
    def get_missing_date_ranges(self, ticker_symbol: str, 
                                start_date: str, end_date: str) -> List[tuple]:
        """
        Get list of missing date ranges for a ticker.
        
        Args:
            ticker_symbol: Stock ticker symbol
            start_date: Desired start date (YYYY-MM-DD)
            end_date: Desired end date (YYYY-MM-DD)
            
        Returns:
            List of (start_date, end_date) tuples for missing ranges
        """
        data = self.load_ticker_data(ticker_symbol, prefer_usd=False)
        
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        
        # If no data exists, entire range is missing
        if data is None or data.empty:
            return [(start_date, end_date)]
        
        # Get existing date range
        existing_start = data.index.min()
        existing_end = data.index.max()
        
        missing_ranges = []
        
        # Check if we need data before existing range
        if start_ts < existing_start:
            missing_ranges.append((start_date, (existing_start - pd.Timedelta(days=1)).strftime('%Y-%m-%d')))
        
        # Check if we need data after existing range
        if end_ts > existing_end:
            missing_ranges.append(((existing_end + pd.Timedelta(days=1)).strftime('%Y-%m-%d'), end_date))
        
        return missing_ranges
    
    def get_ticker_filepath(self, ticker_symbol: str, usd_normalized: bool = False) -> Path:
        """
        Get the filepath for a ticker's data file.
        
        Args:
            ticker_symbol: Stock ticker symbol
            usd_normalized: If True, returns path for USD-normalized data
            
        Returns:
            Path to the data file
        """
        if usd_normalized:
            return self.usd_data_dir / f"{ticker_symbol}_USD.csv"
        else:
            return self.data_dir / f"{ticker_symbol}.csv"
    
    def save_ticker_data(self, ticker_symbol: str, data: pd.DataFrame, 
                        currency: str = 'USD', also_save_usd: bool = True) -> None:
        """
        Save ticker data to CSV file. Optionally also saves USD-normalized version.
        
        Args:
            ticker_symbol: Stock ticker symbol
            data: DataFrame with OHLC data (index must be DatetimeIndex)
            currency: Original currency of the data
            also_save_usd: If True and currency != USD, also save USD-normalized version
        """
        if data.empty:
            logger.warning(f"No data to save for {ticker_symbol}")
            return
        
        # Ensure index is datetime
        if not isinstance(data.index, pd.DatetimeIndex):
            logger.error(f"Data index must be DatetimeIndex for {ticker_symbol}")
            return
        
        # Save original currency data
        filepath = self.get_ticker_filepath(ticker_symbol, usd_normalized=False)
        try:
            data.to_csv(filepath, index=True)
            logger.info(f"✓ Saved {len(data)} rows for {ticker_symbol} ({currency}) to {filepath}")
        except Exception as e:
            logger.error(f"Error saving data for {ticker_symbol}: {e}")
            raise
        
        # Save USD-normalized version if requested and not already in USD
        if also_save_usd and currency != 'USD' and self.currency_converter is not None:
            try:
                logger.info(f"Converting {ticker_symbol} from {currency} to USD...")
                usd_data = self.currency_converter.convert_ohlc_data(
                    data.copy(),
                    from_currency=currency,
                    to_currency='USD',
                    use_cache=True
                )
                
                usd_filepath = self.get_ticker_filepath(ticker_symbol, usd_normalized=True)
                usd_data.to_csv(usd_filepath, index=True)
                logger.info(f"✓ Saved USD-normalized data to {usd_filepath}")
                
            except Exception as e:
                logger.warning(f"Could not create USD-normalized data for {ticker_symbol}: {e}")
                logger.warning(f"USD-normalized data will not be available for metrics")
    
    def load_ticker_data(self, ticker_symbol: str, prefer_usd: bool = False) -> Optional[pd.DataFrame]:
        """
        Load ticker data from CSV file.
        
        Args:
            ticker_symbol: Stock ticker symbol
            prefer_usd: If True, tries to load USD-normalized data first (for metrics)
            
        Returns:
            DataFrame with OHLC data, or None if file doesn't exist
        """
        # Try USD-normalized first if requested
        if prefer_usd:
            usd_filepath = self.get_ticker_filepath(ticker_symbol, usd_normalized=True)
            if usd_filepath.exists():
                try:
                    data = pd.read_csv(usd_filepath, index_col=0, parse_dates=True)
                    logger.debug(f"Loaded USD-normalized data for {ticker_symbol}")
                    return data
                except Exception as e:
                    logger.warning(f"Error loading USD data for {ticker_symbol}: {e}")
        
        # Load original currency data
        filepath = self.get_ticker_filepath(ticker_symbol, usd_normalized=False)
        
        if not filepath.exists():
            logger.debug(f"No data file found for {ticker_symbol}")
            return None
        
        try:
            data = pd.read_csv(filepath, index_col=0, parse_dates=True)
            logger.debug(f"Loaded {len(data)} rows for {ticker_symbol}")
            return data
        except Exception as e:
            logger.error(f"Error loading data for {ticker_symbol}: {e}")
            return None
    
    def load_all_ticker_data(self, prefer_usd: bool = False) -> Dict[str, pd.DataFrame]:
        """
        Load data for all enabled tickers.
        
        Args:
            prefer_usd: If True, tries to load USD-normalized data (for metrics)
            
        Returns:
            Dictionary mapping ticker symbols to DataFrames
        """
        ticker_data = {}
        enabled_tickers = self.get_enabled_tickers()
        
        for ticker_info in enabled_tickers:
            symbol = ticker_info['symbol']
            data = self.load_ticker_data(symbol, prefer_usd=prefer_usd)
            
            if data is not None:
                ticker_data[symbol] = data
            else:
                logger.warning(f"Could not load data for {symbol}")
        
        logger.info(f"Loaded {len(ticker_data)} tickers (prefer_usd={prefer_usd})")
        return ticker_data
    
    def merge_and_save(self, ticker_symbol: str, new_data: pd.DataFrame, 
                      currency: str = 'USD') -> pd.DataFrame:
        """
        Merge new data with existing data and save.
        
        Args:
            ticker_symbol: Stock ticker symbol
            new_data: New DataFrame to merge
            currency: Currency of the new data
            
        Returns:
            Merged DataFrame
        """
        # Load existing data
        existing_data = self.load_ticker_data(ticker_symbol, prefer_usd=False)
        
        if existing_data is None:
            # No existing data, just save new data
            self.save_ticker_data(ticker_symbol, new_data, currency=currency)
            return new_data
        
        # Merge data
        merged_data = pd.concat([existing_data, new_data])
        merged_data = merged_data[~merged_data.index.duplicated(keep='last')]
        merged_data = merged_data.sort_index()
        
        # Save merged data
        self.save_ticker_data(ticker_symbol, merged_data, currency=currency)
        
        return merged_data
    
    def merge_and_save(self, ticker_symbol: str, new_data: pd.DataFrame, 
                      currency: str = 'USD') -> pd.DataFrame:
        """
        Merge new data with existing data and save.
        
        Args:
            ticker_symbol: Stock ticker symbol
            new_data: New DataFrame to merge
            currency: Currency of the new data
            
        Returns:
            Merged DataFrame
        """
        # Load existing data
        existing_data = self.load_ticker_data(ticker_symbol, prefer_usd=False)
        
        if existing_data is None:
            # No existing data, just save new data
            self.save_ticker_data(ticker_symbol, new_data, currency=currency)
            return new_data
        
        # Merge data
        merged_data = self.merge_data(existing_data, new_data)
        
        # Save merged data
        self.save_ticker_data(ticker_symbol, merged_data, currency=currency)
        
        return merged_data
    
    def merge_data(self, existing_data: Optional[pd.DataFrame], 
                   new_data: pd.DataFrame) -> pd.DataFrame:
        """
        Merge existing and new data, handling duplicates.
        
        Args:
            existing_data: Existing DataFrame (or None)
            new_data: New DataFrame to merge
            
        Returns:
            Merged DataFrame
        """
        if existing_data is None or existing_data.empty:
            return new_data.copy()
        
        if new_data.empty:
            return existing_data.copy()
        
        # Concatenate
        merged = pd.concat([existing_data, new_data])
        
        # Remove duplicates (keep last)
        merged = merged[~merged.index.duplicated(keep='last')]
        
        # Sort by index
        merged = merged.sort_index()
        
        return merged
    
    def get_data_info(self, ticker_symbol: str) -> Dict[str, any]:
        """
        Get information about stored data for a ticker.
        
        Returns:
            Dictionary with data info (dates, count, currencies available, etc.)
        """
        info = {
            'symbol': ticker_symbol,
            'has_original': False,
            'has_usd': False,
            'original_rows': 0,
            'usd_rows': 0,
            'start_date': None,
            'end_date': None,
            'status': 'Not Found'
        }
        
        # Check original data
        original_data = self.load_ticker_data(ticker_symbol, prefer_usd=False)
        if original_data is not None:
            info['has_original'] = True
            info['original_rows'] = len(original_data)
            info['start_date'] = original_data.index.min().strftime('%Y-%m-%d')
            info['end_date'] = original_data.index.max().strftime('%Y-%m-%d')
            info['status'] = 'OK'
        
        # Check USD-normalized data
        usd_filepath = self.get_ticker_filepath(ticker_symbol, usd_normalized=True)
        if usd_filepath.exists():
            usd_data = self.load_ticker_data(ticker_symbol, prefer_usd=True)
            if usd_data is not None:
                info['has_usd'] = True
                info['usd_rows'] = len(usd_data)
        
        return info
    
    def get_all_data_info(self) -> pd.DataFrame:
        """
        Get information about all enabled tickers.
        
        Returns:
            DataFrame with info for all tickers
        """
        info_list = []
        enabled_tickers = self.get_enabled_tickers()
        
        for ticker_info in enabled_tickers:
            symbol = ticker_info['symbol']
            currency = ticker_info['currency']
            info = self.get_data_info(symbol)
            info['name'] = ticker_info['name']
            info['currency'] = currency
            info_list.append(info)
        
        return pd.DataFrame(info_list)