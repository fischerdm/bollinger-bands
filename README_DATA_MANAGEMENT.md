# Bollinger Bands Trading App - Data Management

## Overview

This enhanced version adds local data storage and smart incremental updates to the Bollinger Bands trading application. Data is cached locally to enable:

- **Faster loading**: Load from local storage instead of downloading every time
- **Longer history**: Build price histories beyond yfinance free tier limits
- **Incremental updates**: Only download missing dates, not the entire dataset
- **Offline capability**: Work with cached data when internet is unavailable

## New Features

### 1. YAML Configuration (`config/tickers.yaml`)

Easily manage your tickers in a YAML file instead of hardcoded Python lists:

```yaml
tickers:
  - symbol: EEM
    name: "Emerging Markets (EEM)"
    enabled: true
```

### 2. Local Data Storage

Data is stored in `data/raw/` as CSV files:
```
data/raw/
├── EEM.csv
├── URTH.csv
├── GDX.csv
└── ...
```

### 3. Smart Incremental Updates

The system intelligently:
- Detects which dates are missing from local storage
- Only downloads missing data ranges
- Merges new data with existing data
- Removes duplicates automatically

### 4. Data Management UI

New controls in the web app:
- **Data Status**: Shows number of loaded tickers and latest data date
- **Update Data** button: Fetch latest data for all tickers
- **View Details** button: See detailed info for each ticker (dates, file sizes, etc.)

### 5. Command-Line Tool (`manage_data.py`)

Manage data without launching the full app.

## Installation

```bash
# Install additional dependencies
pip install pyyaml

# Or if using requirements.txt
pip install -r requirements.txt
```

## Quick Start

### Method 1: Use the Web App

```bash
python app_with_data_management.py
```

The app will automatically:
1. Load configuration from `config/tickers.yaml`
2. Check for existing data in `data/raw/`
3. Fetch only missing dates (auto-update enabled by default)
4. Display data status in the UI

### Method 2: Use the CLI Tool

```bash
# View current data status
python manage_data.py info

# Update all tickers with latest data
python manage_data.py update

# Fetch data for specific ticker
python manage_data.py fetch EEM --start-date 2020-01-01

# View configuration
python manage_data.py config

# Clear data for a ticker
python manage_data.py clear --ticker EEM

# Clear all data
python manage_data.py clear --all
```

## Configuration

Edit `config/tickers.yaml` to customize:

```yaml
# Data settings
data_settings:
  # Default start date for initial fetch
  default_start_date: "2000-01-01"
  
  # Directory for storing data
  data_directory: "data/raw"
  
  # Auto-update on app startup
  auto_update_on_startup: true
  
  # Max cache age (null = never expire)
  max_cache_days: null
```

### Adding New Tickers

Add to `tickers` section in `config/tickers.yaml`:

```yaml
tickers:
  - symbol: SPY
    name: "S&P 500 ETF"
    enabled: true
```

### Disabling Tickers

Set `enabled: false` to skip a ticker without removing it:

```yaml
tickers:
  - symbol: OLD.TICKER
    name: "Old Ticker"
    enabled: false
```

## Architecture

### Modules

1. **`storage_manager.py`**: Handles all file I/O operations
   - Load/save CSV files
   - Merge data with duplicate removal
   - Track date ranges
   - Manage configuration

2. **`fetcher.py`**: Enhanced data fetcher with caching
   - Original yfinance interface preserved
   - Smart incremental updates
   - Automatic merge with cached data

3. **`manage_data.py`**: Command-line interface
   - Info, update, fetch, clear commands
   - Progress reporting
   - Batch operations

### Data Flow

```
User Request
    ↓
Fetcher checks storage_manager
    ↓
Missing dates identified
    ↓
Only missing data downloaded from yfinance
    ↓
New data merged with existing
    ↓
Merged data saved and returned
```

## Usage Examples

### Example 1: Initial Setup

```bash
# 1. Configure tickers
vim config/tickers.yaml

# 2. Fetch initial data
python manage_data.py update

# 3. View status
python manage_data.py info
```

### Example 2: Daily Update Workflow

```bash
# Quick update (only fetches new dates)
python manage_data.py update

# Then launch app
python app_with_data_management.py
```

### Example 3: Backfilling Historical Data

```bash
# Fetch older data for specific ticker
python manage_data.py fetch EEM --start-date 1990-01-01

# Verify
python manage_data.py info --ticker EEM
```

### Example 4: Troubleshooting

```bash
# Check what's wrong
python manage_data.py info

# Clear corrupted data
python manage_data.py clear --ticker PROBLEM.TICKER

# Re-fetch
python manage_data.py fetch PROBLEM.TICKER
```

## Migration from Original App

To convert your existing `app.py` to use data management:

1. **Replace hardcoded lists**:
   ```python
   # OLD
   tickers = ['EEM', 'URTH', ...]
   
   # NEW
   storage_manager = DataStorageManager('config/tickers.yaml')
   enabled_tickers = storage_manager.get_enabled_tickers()
   tickers = [t['symbol'] for t in enabled_tickers]
   ```

2. **Replace fetcher initialization**:
   ```python
   # OLD
   fetcher = DataFetcher()
   
   # NEW
   fetcher = DataFetcher(storage_manager)
   ```

3. **Use cached fetching**:
   ```python
   # OLD
   data = fetcher.fetch_ohlc_data(ticker, start_date, end_date)
   
   # NEW (automatically uses cache)
   data = fetcher.fetch_ohlc_data(ticker, start_date, end_date, use_cache=True)
   ```

4. **Add data management UI** (see `app_with_data_management.py` for examples)

## Performance Benefits

### Before (No Caching)
- **App startup**: 30-60 seconds (downloads all data every time)
- **Data range**: Limited by yfinance free tier
- **Network**: Required for every launch

### After (With Caching)
- **Initial startup**: 30-60 seconds (first time only)
- **Subsequent startups**: 2-5 seconds (loads from cache)
- **Daily updates**: 1-3 seconds (only new dates)
- **Data range**: Unlimited (build history over time)
- **Network**: Only needed for updates

## File Formats

### CSV Structure

Each ticker is stored as a CSV with columns:
```csv
Date,Open,High,Low,Close
2020-01-02,327.17,329.01,326.20,328.57
2020-01-03,328.64,329.48,327.35,327.95
...
```

### Metadata

Ticker symbol is stored in DataFrame attributes:
```python
data.attrs['ticker'] = 'EEM'
```

## Troubleshooting

### Issue: "No data loaded"

```bash
# Check if files exist
ls -la data/raw/

# Try manual fetch
python manage_data.py fetch EEM

# Check for errors
python manage_data.py info
```

### Issue: Data seems outdated

```bash
# Force update
python manage_data.py update

# Or clear and re-fetch
python manage_data.py clear --ticker EEM
python manage_data.py fetch EEM
```

### Issue: Config file not found

```bash
# Check path
python manage_data.py config --config config/tickers.yaml

# Or use absolute path
python manage_data.py --config /full/path/to/config.yaml info
```

## Advanced Usage

### Programmatic Access

```python
from bollinger_bands.data.storage_manager import DataStorageManager
from bollinger_bands.data.fetcher import DataFetcher

# Initialize
storage = DataStorageManager('config/tickers.yaml')
fetcher = DataFetcher(storage)

# Get missing date ranges
missing = storage.get_missing_date_ranges('EEM', '2020-01-01', '2024-12-31')
print(f"Missing ranges: {missing}")

# Fetch with caching
data = fetcher.fetch_ohlc_data('EEM', '2020-01-01', '2024-12-31', use_cache=True)

# Get data info
info = storage.get_data_info('EEM')
print(f"Data range: {info['start_date']} to {info['end_date']}")
```

### Custom Data Processing

```python
# Load raw data
data = storage.load_ticker_data('EEM')

# Process
data['SMA_20'] = data['Close'].rolling(20).mean()

# Save back
storage.save_ticker_data('EEM', data)
```

## Best Practices

1. **Run daily updates**: Keep data current with `python manage_data.py update`
2. **Back up data folder**: Regularly backup `data/raw/` directory
3. **Version control config**: Commit `config/tickers.yaml` to git
4. **Don't commit data**: Add `data/` to `.gitignore`
5. **Monitor disk space**: CSV files are small but can add up over time
6. **Validate after updates**: Use `manage_data.py info` to verify

## Future Enhancements

Potential improvements:
- [ ] Parallel downloads for faster updates
- [ ] Compression for older data
- [ ] Database backend option (SQLite)
- [ ] Data validation and quality checks
- [ ] Automatic backup/restore
- [ ] Web-based configuration editor
- [ ] Real-time data streaming

## Support

For issues or questions:
1. Check this README
2. Run `python manage_data.py info` to diagnose
3. Check log output for error messages
4. Verify `config/tickers.yaml` is valid YAML

## License

[Your License Here]
