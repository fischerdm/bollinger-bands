# Currency Conversion System - Complete Documentation

## Overview

The Bollinger Bands application supports multi-currency analysis with automatic conversion between USD, EUR, CHF, GBP, and JPY. This allows fair comparison of assets traded in different currencies.

## Architecture

### Dual Data Storage

The system maintains two versions of data:

```
data/
├── raw/                          # Original currency data
│   ├── URTH.csv                 # USD (no conversion needed)
│   ├── ^SSMI.csv                # CHF (as traded)
│   ├── ^GDAXI.csv               # EUR (as traded)
│   └── ^FTSE.csv                # GBP (as traded)
│
├── usd_normalized/               # USD-normalized for metrics
│   ├── ^SSMI_USD.csv            # CHF → USD
│   ├── ^GDAXI_USD.csv           # EUR → USD
│   └── ^FTSE_USD.csv            # GBP → USD
│
└── currencies/                   # Exchange rate cache
    ├── USDCHF.csv               # USD to CHF rates
    ├── USDEUR.csv               # USD to EUR rates (inverted from EURUSD)
    └── USDGBP.csv               # USD to GBP rates (inverted from GBPUSD)
```

### Usage Separation

| Use Case | Data Source | Why |
|----------|-------------|-----|
| **Price Charts** | Original (`data/raw/`) | Trading signals must use actual traded prices (SMI in CHF) |
| **Bollinger Bands** | Original | Bands calculated on actual traded instrument |
| **Exit Signals** | Original | Based on real price movements |
| **Metrics & Comparison** | USD-normalized (`data/usd_normalized/`) | Fair comparisons across currencies |

## Conversion Strategy: Hub-and-Spoke

All conversions go through USD as an intermediate currency:

```
        EUR ←─────┐
                  │
        CHF ←──── USD (hub) ────→ GBP
                  │
        JPY ←─────┘
```

**Benefits:**
- Only need N pairs (not N×N)
- No compound conversion errors
- Consistent methodology

**Example: CHF → EUR**
```
Step 1: CHF → USD (using USDCHF=X, inverted)
Step 2: USD → EUR (using EURUSD=X, inverted)
Result: CHF → EUR (via USD hub)
```

## Exchange Rate Symbols

### Yahoo Finance Symbol Format

| Conversion | Yahoo Symbol | What It Returns | Action |
|------------|--------------|-----------------|--------|
| **USD → CHF** | `USDCHF=X` | CHF per 1 USD (e.g., 0.88) | Use directly |
| **USD → EUR** | `EURUSD=X` | USD per 1 EUR (e.g., 1.10) | Invert (1/1.10 = 0.91) |
| **USD → GBP** | `GBPUSD=X` | USD per 1 GBP (e.g., 1.27) | Invert (1/1.27 = 0.79) |
| **USD → JPY** | `USDJPY=X` | JPY per 1 USD (e.g., 150) | Use directly |

**Note:** The system automatically handles inversion. You only need to specify the Yahoo Finance symbol in `config/tickers.yaml`.

### Configuration

In `config/tickers.yaml`:

```yaml
currency_pairs:
  USDCHF: "USDCHF=X"    # Direct
  USDEUR: "EURUSD=X"    # Will auto-invert
  USDGBP: "GBPUSD=X"    # Will auto-invert
  USDJPY: "USDJPY=X"    # Direct
```

## Conversion Flow

### Example: Displaying SMI (CHF) in EUR

**Data Flow:**

1. **Chart Display (Original Currency)**
   ```
   Load: data/raw/^SSMI.csv (CHF prices)
   Display: "Swiss Market Index (SMI) (CHF)"
   Prices: 11,850.50 CHF
   ```

2. **Metrics Calculation (USD-normalized)**
   ```
   Load: data/usd_normalized/^SSMI_USD.csv
   This contains: CHF → USD converted prices
   Example: 11,850.50 CHF = 13,466.48 USD (at 1.1363 rate)
   ```

3. **Display in EUR (User Selection)**
   ```
   Convert: USD → EUR
   Get rate: EURUSD=X → 1.0850
   Invert: 1 / 1.0850 = 0.9217
   Result: 13,466.48 USD × 0.9217 = 12,409.84 EUR
   ```

**Final Display:**
- Chart: 11,850.50 CHF (original)
- Metrics: 12,409.84 EUR (converted for comparison)

### Caching Strategy

**Three-level cache:**

```
Request for USD/CHF rates
    ↓
┌─────────────────────────────┐
│ 1. Memory Cache             │ ← Fastest (same session)
│    exchange_rate_cache      │
└─────────────────────────────┘
    ↓ (if not found)
┌─────────────────────────────┐
│ 2. Disk Cache               │ ← Fast (persists)
│    data/currencies/         │
└─────────────────────────────┘
    ↓ (if not found)
┌─────────────────────────────┐
│ 3. Yahoo Finance            │ ← Slow (download)
│    yfinance API             │
└─────────────────────────────┘
    ↓
Save to disk & memory for next time
```

**Cache Behavior:**

| Scenario | Action | Speed |
|----------|--------|-------|
| **Same session, same currency** | Memory cache | Instant |
| **New session, same currency** | Disk cache | <100ms |
| **New currency** | Download from Yahoo | 1-3 seconds |
| **Update (new dates)** | Download only missing dates | <1 second |

## Automatic USD Normalization

When you download or update ticker data, USD normalization happens automatically:

### Initial Download

```python
# You download ^SSMI (CHF ticker)
fetcher.fetch_ohlc_data('^SSMI', '2000-01-01', '2025-12-31')

# Automatically creates:
# 1. data/raw/^SSMI.csv (original CHF data)
# 2. data/usd_normalized/^SSMI_USD.csv (converted to USD)
```

### Daily Updates

```python
# App starts with auto_update_on_startup: true
python app.py

# For each non-USD ticker:
# 1. Downloads new dates (e.g., Dec 31)
# 2. Saves to data/raw/TICKER.csv
# 3. AUTOMATICALLY converts new dates to USD
# 4. Appends to data/usd_normalized/TICKER_USD.csv
```

**You never need to manually trigger USD normalization!**

## Example Use Cases

### Use Case 1: Swiss Investor

**Scenario:** Compare Swiss stocks (CHF) with US stocks (USD)

**Setup:**
```yaml
tickers:
  - symbol: ^SSMI
    currency: CHF
  - symbol: URTH
    currency: USD
```

**Selection:** Currency = CHF

**Result:**
- URTH: 187.00 USD → 164.56 CHF (at 0.88 rate)
- SMI: 11,850 CHF (no conversion)
- Metrics calculated in CHF → Fair comparison ✓

### Use Case 2: Performance Comparison

**Goal:** Which performed better: SMI or DAX?

**Without currency conversion (WRONG):**
```
SMI:  +5.2% (CHF)
DAX:  +8.1% (EUR)
❌ Can't compare - different currencies!
```

**With currency conversion (CORRECT):**
```
Select: Currency = USD
SMI:  +5.2% → +1.8% USD (CHF weakened)
DAX:  +8.1% → +6.5% USD (EUR weakened)
✓ Fair comparison: DAX outperformed by 4.7%
```

### Use Case 3: Relative Strength

**Levy RS Formula:**
```
6M Perf Rel. Bench (%) = (Asset Return / Benchmark Return) - 1

Example in USD:
SMI: +10.5% (in CHF) → +6.0% (in USD, after FX)
URTH: +11.5% (in USD)

Relative: (1.060 / 1.115) - 1 = -4.9%
Result: SMI underperformed by 4.9%
```

**Why currency-independent:**
```
In CHF:
SMI: (1.105 CHF / 1.105 CHF) = 1.000
URTH: (1.115 USD × 0.88) / (1.000 USD × 0.88) = 1.115

Ratio: 1.000 / 1.115 = 0.897 → -10.3%

Different result! Must use same currency.
```

## API Reference

### CurrencyConverter Class

```python
from bollinger_bands.data.currency_converter import CurrencyConverter

# Initialize
converter = CurrencyConverter(
    config,  # Config dict from tickers.yaml
    cache_dir='data/currencies'
)

# Convert single ticker
usd_data = converter.convert_ohlc_data(
    data=chf_data,           # DataFrame with OHLC
    from_currency='CHF',
    to_currency='USD',
    use_cache=True
)

# Convert all tickers via USD hub
converted = converter.convert_ticker_data(
    ticker_data=all_tickers,          # Dict of DataFrames
    ticker_currencies={'SMI': 'CHF'}, # Dict of currencies
    target_currency='EUR',             # Target
    use_cache=True
)

# Get exchange rates
rates = converter.get_exchange_rates(
    from_currency='USD',
    to_currency='CHF',
    start_date='2020-01-01',
    end_date='2025-12-31',
    use_cache=True  # Use cached rates
)
```

### Key Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| `convert_ohlc_data()` | Convert price data | Converted DataFrame |
| `convert_ticker_data()` | Convert multiple tickers | Dict of DataFrames |
| `convert_via_usd()` | Hub-and-spoke conversion | Converted DataFrame |
| `get_exchange_rates()` | Get FX rates | DataFrame with rates |

## Troubleshooting

### Issue: Metrics don't change when switching currencies

**Cause:** Currency cache corrupted or converter not initialized

**Fix:**
```bash
# Clear currency cache
rm -rf data/currencies/

# Restart app
python app.py
```

### Issue: "No data returned for CHF=X"

**Cause:** Wrong Yahoo Finance symbol

**Fix:** Update `config/tickers.yaml`:
```yaml
# ❌ Wrong:
USDCHF: "CHF=X"

# ✅ Correct:
USDCHF: "USDCHF=X"
```

### Issue: USD-normalized data missing

**Cause:** Never created USD versions

**Fix:**
```bash
# One-time: Create USD versions from existing data
python create_usd_versions.py
```

### Issue: Exchange rates outdated

**Cause:** Cache hasn't been updated

**Solution:** Just use the app - it auto-updates missing dates!

## Performance

### First Time (No Cache)
```
Select CHF:
  Download USDCHF rates (2000-2025): 3 seconds
  Convert 15 tickers: 1 second
  Total: ~4 seconds
```

### Subsequent Times (With Cache)
```
Select CHF:
  Load from cache: <0.1 seconds
  Convert 15 tickers: <0.1 seconds
  Total: <0.2 seconds ✨
```

### Daily Update
```
App startup:
  Check for new dates: 1 ticker = 0.5s
  Update exchange rates (1 day): 0.2s per currency
  Total for 15 tickers: ~8 seconds
```

## Best Practices

1. **Always specify currency in config:**
   ```yaml
   - symbol: ^SSMI
     currency: CHF  # ← Don't forget!
   ```

2. **Use cache (default):**
   ```python
   convert_ohlc_data(..., use_cache=True)  # Default
   ```

3. **Don't clear cache unnecessarily:**
   - Cache speeds up currency switching 20x
   - Only clear if corrupted

4. **Let auto-update work:**
   ```yaml
   data_settings:
     auto_update_on_startup: true  # ← Leave enabled
   ```

5. **Check data/usd_normalized/ exists:**
   ```bash
   ls data/usd_normalized/
   # Should have: TICKER_USD.csv for each non-USD ticker
   ```

## Summary

- **Storage:** Dual (original + USD-normalized)
- **Charts:** Use original currency (accurate signals)
- **Metrics:** Use USD-normalized (fair comparisons)
- **Conversion:** Via USD hub (simple, no cross rates)
- **Caching:** 3-level (memory → disk → download)
- **Updates:** Automatic (no manual intervention)

All currency operations are transparent and automatic! 🌍💱
