#!/usr/bin/env python3
"""
Data Management CLI Tool
Provides command-line utilities for managing stock data.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from bollinger_bands.data.storage_manager import DataStorageManager
from bollinger_bands.data.fetcher import DataFetcher


def cmd_info(args):
    """Display information about stored data."""
    storage = DataStorageManager(args.config)
    
    if args.ticker:
        # Show info for specific ticker
        info = storage.get_data_info(args.ticker)
        print(f"\n{'='*60}")
        print(f"Data Information: {args.ticker}")
        print(f"{'='*60}")
        for key, value in info.items():
            print(f"{key:20s}: {value}")
        print(f"{'='*60}\n")
    else:
        # Show info for all tickers
        df = storage.get_all_data_info()
        print(f"\n{'='*80}")
        print("All Ticker Data Information")
        print(f"{'='*80}")
        print(df.to_string(index=False))
        print(f"{'='*80}\n")


def cmd_update(args):
    """Update data for all tickers."""
    storage = DataStorageManager(args.config)
    fetcher = DataFetcher(storage)
    
    end_date = args.end_date or datetime.now().strftime('%Y-%m-%d')
    
    print(f"\nUpdating all tickers to {end_date}...")
    print(f"{'='*60}")
    
    ticker_data = fetcher.update_all_tickers(end_date)
    
    print(f"\n{'='*60}")
    print(f"Update complete! Updated {len(ticker_data)} tickers")
    print(f"{'='*60}\n")


def cmd_fetch(args):
    """Fetch data for specific ticker."""
    storage = DataStorageManager(args.config)
    fetcher = DataFetcher(storage)
    
    start_date = args.start_date or storage.config['data_settings']['default_start_date']
    end_date = args.end_date or datetime.now().strftime('%Y-%m-%d')
    
    print(f"\nFetching {args.ticker} from {start_date} to {end_date}...")
    print(f"{'='*60}")
    
    data = fetcher.fetch_ohlc_data(args.ticker, start_date, end_date, use_cache=not args.no_cache)
    
    print(f"\n{'='*60}")
    print(f"Fetched {len(data)} rows")
    print(f"Date range: {data.index[0]} to {data.index[-1]}")
    print(f"{'='*60}\n")
    
    if args.show_head:
        print("First 10 rows:")
        print(data.head(10))
        print()


def cmd_clear(args):
    """Clear stored data for ticker."""
    storage = DataStorageManager(args.config)
    
    if args.all:
        # Clear all tickers
        response = input("Are you sure you want to delete all stored data? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return
        
        tickers = storage.get_enabled_tickers()
        deleted_count = 0
        for ticker_info in tickers:
            if storage.clear_ticker_data(ticker_info['symbol']):
                deleted_count += 1
        
        print(f"\nDeleted data for {deleted_count} tickers")
    
    elif args.ticker:
        # Clear specific ticker
        response = input(f"Delete stored data for {args.ticker}? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return
        
        if storage.clear_ticker_data(args.ticker):
            print(f"\nDeleted data for {args.ticker}")
        else:
            print(f"\nNo data found for {args.ticker}")
    else:
        print("Error: Specify --ticker or --all")


def cmd_config(args):
    """Display configuration."""
    storage = DataStorageManager(args.config)
    
    print(f"\n{'='*60}")
    print("Configuration")
    print(f"{'='*60}")
    print(f"Config file: {storage.config_path}")
    print(f"Data directory: {storage.data_dir}")
    print(f"Default start date: {storage.config['data_settings']['default_start_date']}")
    print(f"Auto update: {storage.config['data_settings']['auto_update_on_startup']}")
    print(f"\nEnabled tickers: {len(storage.get_enabled_tickers())}")
    for ticker_info in storage.get_enabled_tickers():
        print(f"  - {ticker_info['symbol']:10s} {ticker_info['name']}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Stock Data Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--config', 
        default='config/tickers.yaml',
        help='Path to configuration file (default: config/tickers.yaml)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show data information')
    info_parser.add_argument('--ticker', help='Show info for specific ticker')
    info_parser.set_defaults(func=cmd_info)
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update all tickers with latest data')
    update_parser.add_argument('--end-date', help='End date (YYYY-MM-DD, default: today)')
    update_parser.set_defaults(func=cmd_update)
    
    # Fetch command
    fetch_parser = subparsers.add_parser('fetch', help='Fetch data for specific ticker')
    fetch_parser.add_argument('ticker', help='Ticker symbol')
    fetch_parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    fetch_parser.add_argument('--end-date', help='End date (YYYY-MM-DD, default: today)')
    fetch_parser.add_argument('--no-cache', action='store_true', help='Ignore cached data')
    fetch_parser.add_argument('--show-head', action='store_true', help='Show first 10 rows')
    fetch_parser.set_defaults(func=cmd_fetch)
    
    # Clear command
    clear_parser = subparsers.add_parser('clear', help='Delete stored data')
    clear_parser.add_argument('--ticker', help='Ticker symbol to clear')
    clear_parser.add_argument('--all', action='store_true', help='Clear all tickers')
    clear_parser.set_defaults(func=cmd_clear)
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Show configuration')
    config_parser.set_defaults(func=cmd_config)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    try:
        args.func(args)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
