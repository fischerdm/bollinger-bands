"""
Data Storage Manager
Handles saving, loading, and merging of historical stock data.
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
    """Manages local storage and retrieval of stock data."""
    
    def __init__(self, config_path: str = "config/tickers.yaml"):
        """
        Initialize the data storage manager.
        
        Args:
            config_path: Path to the ticker configuration YAML file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.data_dir = Path(self.config['data_settings']['data_directory'])
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
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
            List of dicts with 'symbol' and 'name' keys
        """
        tickers = []
        for ticker in self.config['tickers']:
            if ticker.get('enabled', True):  # Default to enabled if not specified
                tickers.append({
                    'symbol': ticker['symbol'],
                    'name': ticker['name']
                })
        return tickers
    
    def get_ticker_filepath(self, ticker_symbol: str) -> Path:
        """Get the filepath for a ticker's data file."""
        return self.data_dir / f"{ticker_symbol}.csv"
    
    def save_ticker_data(self, ticker_symbol: str, data: pd.DataFrame) -> None:
        """
        Save ticker data to CSV file.
        
        Args:
            ticker_symbol: Stock ticker symbol
            data: DataFrame with OHLC data (index must be DatetimeIndex)
        """
        if data.empty:
            logger.warning(f"No data to save for {ticker_symbol}")
            return
        
        filepath = self.get_ticker_filepath(ticker_symbol)
        
        # Ensure index is datetime
        if not isinstance(data.index, pd.DatetimeIndex):
            logger.error(f"Data index must be DatetimeIndex for {ticker_symbol}")
            return
        
        # Save with metadata in filename comment
        try:
            data.to_csv(filepath, index=True)
            logger.info(f"Saved {len(data)} rows for {ticker_symbol} to {filepath}")
        except Exception as e:
            logger.error(f"Error saving data for {ticker_symbol}: {e}")
            raise
    
    def load_ticker_data(self, ticker_symbol: str) -> Optional[pd.DataFrame]:
        """
        Load ticker data from CSV file.
        
        Args:
            ticker_symbol: Stock ticker symbol
            
        Returns:
            DataFrame with OHLC data, or None if file doesn't exist
        """
        filepath = self.get_ticker_filepath(ticker_symbol)
        
        if not filepath.exists():
            logger.info(f"No stored data found for {ticker_symbol}")
            return None
        
        try:
            data = pd.read_csv(filepath, index_col=0, parse_dates=True)
            logger.info(f"Loaded {len(data)} rows for {ticker_symbol} from {filepath}")
            return data
        except Exception as e:
            logger.error(f"Error loading data for {ticker_symbol}: {e}")
            return None
    
    def get_data_date_range(self, ticker_symbol: str) -> Optional[Tuple[pd.Timestamp, pd.Timestamp]]:
        """
        Get the date range of stored data for a ticker.
        
        Args:
            ticker_symbol: Stock ticker symbol
            
        Returns:
            Tuple of (start_date, end_date) or None if no data exists
        """
        data = self.load_ticker_data(ticker_symbol)
        if data is None or data.empty:
            return None
        return (data.index[0], data.index[-1])
    
    def merge_data(self, existing_data: pd.DataFrame, new_data: pd.DataFrame) -> pd.DataFrame:
        """
        Merge existing and new data, removing duplicates and sorting by date.
        
        Args:
            existing_data: Previously stored data
            new_data: Newly fetched data
            
        Returns:
            Merged and deduplicated DataFrame
        """
        if existing_data is None or existing_data.empty:
            return new_data
        
        if new_data is None or new_data.empty:
            return existing_data
        
        # Combine data
        combined = pd.concat([existing_data, new_data])
        
        # Remove duplicates (keep last occurrence)
        combined = combined[~combined.index.duplicated(keep='last')]
        
        # Sort by date
        combined = combined.sort_index()
        
        logger.info(f"Merged data: {len(existing_data)} existing + {len(new_data)} new = {len(combined)} total rows")
        
        return combined
    
    def get_missing_date_ranges(self, ticker_symbol: str, target_start_date: str, 
                               target_end_date: str) -> List[Tuple[str, str]]:
        """
        Determine which date ranges are missing from stored data.
        
        Args:
            ticker_symbol: Stock ticker symbol
            target_start_date: Desired start date (YYYY-MM-DD)
            target_end_date: Desired end date (YYYY-MM-DD)
            
        Returns:
            List of (start, end) date tuples that need to be fetched
        """
        stored_range = self.get_data_date_range(ticker_symbol)
        
        target_start = pd.Timestamp(target_start_date)
        target_end = pd.Timestamp(target_end_date)
        
        # No stored data - fetch entire range
        if stored_range is None:
            return [(target_start_date, target_end_date)]
        
        stored_start, stored_end = stored_range
        missing_ranges = []
        
        # Check for gap before stored data
        if target_start < stored_start:
            # Fetch up to one day before stored data to avoid overlap
            gap_end = (stored_start - timedelta(days=1)).strftime('%Y-%m-%d')
            missing_ranges.append((target_start_date, gap_end))
        
        # Check for gap after stored data
        if target_end > stored_end:
            # Fetch from one day after stored data
            gap_start = (stored_end + timedelta(days=1)).strftime('%Y-%m-%d')
            missing_ranges.append((gap_start, target_end_date))
        
        if not missing_ranges:
            logger.info(f"{ticker_symbol}: All data up to date ({stored_start.date()} to {stored_end.date()})")
        else:
            logger.info(f"{ticker_symbol}: Missing ranges: {missing_ranges}")
        
        return missing_ranges
    
    def get_data_info(self, ticker_symbol: str) -> Dict[str, any]:
        """
        Get information about stored data for a ticker.
        
        Args:
            ticker_symbol: Stock ticker symbol
            
        Returns:
            Dictionary with data info (date range, row count, file size, etc.)
        """
        filepath = self.get_ticker_filepath(ticker_symbol)
        info = {
            'ticker': ticker_symbol,
            'file_exists': filepath.exists(),
            'filepath': str(filepath)
        }
        
        if not filepath.exists():
            info['status'] = 'No data'
            return info
        
        try:
            # Get file stats
            stat = filepath.stat()
            info['file_size_kb'] = round(stat.st_size / 1024, 2)
            info['last_modified'] = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            # Get data stats
            data = self.load_ticker_data(ticker_symbol)
            if data is not None and not data.empty:
                info['row_count'] = len(data)
                info['start_date'] = data.index[0].strftime('%Y-%m-%d')
                info['end_date'] = data.index[-1].strftime('%Y-%m-%d')
                info['columns'] = list(data.columns)
                info['status'] = 'OK'
            else:
                info['status'] = 'Empty file'
                
        except Exception as e:
            info['status'] = f'Error: {str(e)}'
        
        return info
    
    def clear_ticker_data(self, ticker_symbol: str) -> bool:
        """
        Delete stored data file for a ticker.
        
        Args:
            ticker_symbol: Stock ticker symbol
            
        Returns:
            True if file was deleted, False otherwise
        """
        filepath = self.get_ticker_filepath(ticker_symbol)
        if filepath.exists():
            try:
                filepath.unlink()
                logger.info(f"Deleted data file for {ticker_symbol}")
                return True
            except Exception as e:
                logger.error(f"Error deleting file for {ticker_symbol}: {e}")
                return False
        return False
    
    def get_all_data_info(self) -> pd.DataFrame:
        """
        Get information about all stored ticker data.
        
        Returns:
            DataFrame with info for all tickers
        """
        tickers = self.get_enabled_tickers()
        info_list = []
        
        for ticker in tickers:
            info = self.get_data_info(ticker['symbol'])
            info['name'] = ticker['name']
            info_list.append(info)
        
        df = pd.DataFrame(info_list)
        
        # Reorder columns for better display
        cols = ['ticker', 'name', 'status', 'start_date', 'end_date', 'row_count', 
                'file_size_kb', 'last_modified']
        existing_cols = [c for c in cols if c in df.columns]
        return df[existing_cols]
