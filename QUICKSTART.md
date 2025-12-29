# Quick Start Guide - Data Management

## What's New?

Your Bollinger Bands app now has **smart data caching**! This means:

✅ **Much faster loading** - 2-5 seconds instead of 30-60 seconds after first load
✅ **Incremental updates** - Only downloads missing dates, not everything
✅ **Longer history** - Build price history beyond free yfinance limits
✅ **Offline capable** - Work with cached data when internet is down
✅ **Easy configuration** - Manage tickers in YAML instead of Python code

## Installation

```bash
cd bollinger_bands_project
pip install pyyaml
```

That's it! (pyyaml is the only new dependency)

## Usage

### Option 1: Run the App (Recommended for Most Users)

```bash
python app_with_data_management.py
```

**What happens:**
1. Loads `config/tickers.yaml`
2. Checks `data/raw/` for cached data
3. Downloads only missing dates (if auto-update is on)
4. Shows "Update Data" button in UI for manual updates

### Option 2: Command Line (For Power Users)

```bash
# See what's in your cache
python manage_data.py info

# Update all tickers with latest data
python manage_data.py update

# Then run the app
python app_with_data_management.py
```

## Configuration

Edit `config/tickers.yaml` to add/remove tickers:

```yaml
tickers:
  - symbol: SPY
    name: "S&P 500 ETF"
    enabled: true     # Set to false to disable without deleting
```

## File Structure

```
bollinger_bands_project/
├── config/
│   └── tickers.yaml                 ← Edit this to manage tickers
├── data/
│   └── raw/                         ← Cached CSV files go here
│       ├── EEM.csv
│       ├── URTH.csv
│       └── ...
├── bollinger_bands/
│   └── data/
│       ├── storage_manager.py       ← Handles file operations
│       └── fetcher.py               ← Smart fetcher with caching
├── manage_data.py                   ← CLI tool
├── app_with_data_management.py      ← Enhanced app
└── example_integration.py           ← Integration example

```

## Common Tasks

### Add a New Ticker

1. Edit `config/tickers.yaml`:
   ```yaml
   - symbol: NEW.TICKER
     name: "My New ETF"
     enabled: true
   ```

2. Restart app or run:
   ```bash
   python manage_data.py fetch NEW.TICKER
   ```

### Update to Latest Data

**From UI:** Click "Update Data" button

**From CLI:**
```bash
python manage_data.py update
```

### Check Data Status

```bash
python manage_data.py info
```

Shows for each ticker:
- Date range
- Number of rows  
- File size
- Last modified time

### Clear and Re-download

```bash
# Clear specific ticker
python manage_data.py clear --ticker EEM

# Re-fetch
python manage_data.py fetch EEM
```

## How Smart Updates Work

**First run:**
```
Request: 2020-01-01 to 2024-12-29
Cache: Empty
Action: Download entire range (30 seconds)
```

**Second run (next day):**
```
Request: 2020-01-01 to 2024-12-30
Cache: 2020-01-01 to 2024-12-29
Action: Download only 2024-12-30 (1 second)
Result: Merge and save
```

**Result:** App loads in 2-5 seconds instead of 30-60!

## Troubleshooting

### "No data loaded"
```bash
python manage_data.py update
```

### Data seems stale
```bash
python manage_data.py info  # Check last update
python manage_data.py update  # Force update
```

### Start fresh
```bash
python manage_data.py clear --all
python manage_data.py update
```

## Integration with Existing Code

Minimal changes needed! See `example_integration.py` for full example.

**Before:**
```python
fetcher = DataFetcher()
tickers = ['EEM', 'URTH', ...]  # Hardcoded

for ticker in tickers:
    data = fetcher.fetch_ohlc_data(ticker, start, end)
```

**After:**
```python
storage = DataStorageManager('config/tickers.yaml')
fetcher = DataFetcher(storage)
enabled = storage.get_enabled_tickers()
tickers = [t['symbol'] for t in enabled]

for ticker in tickers:
    data = fetcher.fetch_ohlc_data(ticker, start, end, use_cache=True)
```

**Or even simpler:**
```python
ticker_data = fetcher.update_all_tickers(end_date)
```

## Tips

1. **Run updates daily**: `python manage_data.py update` in morning
2. **Backup your cache**: Copy `data/raw/` folder occasionally
3. **Use .gitignore**: Don't commit `data/` to version control
4. **Check status regularly**: `python manage_data.py info`

## Performance

| Scenario | Without Caching | With Caching |
|----------|----------------|--------------|
| First load (9 tickers) | 30-60s | 30-60s |
| Daily update | 30-60s | 1-3s |
| Restart app | 30-60s | 2-5s |
| Add new ticker | 30-60s | 5-10s |

## Next Steps

1. ✅ Install: `pip install pyyaml`
2. ✅ Configure: Edit `config/tickers.yaml` if needed
3. ✅ Update: Run `python manage_data.py update`
4. ✅ Launch: Run `python app_with_data_management.py`
5. ✅ Enjoy: Much faster loads from now on!

## Questions?

- Read full docs: `README_DATA_MANAGEMENT.md`
- Run example: `python example_integration.py`
- Check status: `python manage_data.py info`

**Happy trading!** 📈
