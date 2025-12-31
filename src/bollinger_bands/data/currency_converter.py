"""
Currency Conversion Module

Handles fetching and caching exchange rate data, and converting
price data from one currency to another.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from pathlib import Path
import os


class CurrencyConverter:
    """
    Manages currency conversion for ticker data.
    
    Fetches exchange rate data from yfinance and caches it locally.
    Converts price data (OHLC) from one currency to another.
    """
    
    def __init__(self, config, cache_dir='data/currencies'):
        """
        Initialize the currency converter.
        
        Args:
            config: Configuration dictionary with currency settings
            cache_dir: Directory to cache exchange rate data
        """
        self.config = config
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Get currency pairs from config
        self.currency_pairs = config.get('currency_settings', {}).get('currency_pairs', {})
        
        # Cache for loaded exchange rates
        self.exchange_rate_cache = {}
    
    def get_exchange_rate_symbol(self, from_currency, to_currency):
        """
        Get the yfinance symbol for a currency pair.
        Automatically handles inversions if direct pair not available.
        
        Args:
            from_currency: Source currency (e.g., 'USD')
            to_currency: Target currency (e.g., 'CHF')
            
        Returns:
            Tuple of (yfinance symbol string, needs_inversion boolean)
        """
        if from_currency == to_currency:
            return None, False  # No conversion needed
        
        # Try direct pair (e.g., USD->CHF uses USDCHF)
        pair_key = f"{from_currency}{to_currency}"
        if pair_key in self.currency_pairs:
            return self.currency_pairs[pair_key], False
        
        # Try inverse pair (e.g., CHF->USD uses USDCHF inverted)
        inverse_key = f"{to_currency}{from_currency}"
        if inverse_key in self.currency_pairs:
            return self.currency_pairs[inverse_key], True  # Will need inversion
        
        # Not found in config
        return None, False
    
    def fetch_exchange_rates(self, from_currency, to_currency, start_date, end_date):
        """
        Fetch exchange rate data from yfinance.
        
        Args:
            from_currency: Source currency
            to_currency: Target currency
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with exchange rates (Close column)
        """
        symbol, needs_inversion_from_config = self.get_exchange_rate_symbol(from_currency, to_currency)
        
        if symbol is None:
            if from_currency == to_currency:
                # Return Series of 1.0 for same currency
                dates = pd.date_range(start_date, end_date, freq='D')
                return pd.DataFrame({'Close': 1.0}, index=dates)
            else:
                raise ValueError(f"No exchange rate pair found for {from_currency} to {to_currency}")
        
        try:
            # Fetch data from yfinance
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date)
            
            if data.empty:
                raise ValueError(f"No data returned for {symbol}")
            
            # Extract close prices
            rates = data[['Close']].copy()
            
            # Invert if necessary
            if needs_inversion_from_config:
                rates['Close'] = 1.0 / rates['Close']
            
            # Remove timezone information to match ticker data
            if rates.index.tz is not None:
                rates.index = rates.index.tz_localize(None)
            
            return rates
            
        except Exception as e:
            print(f"Error fetching exchange rates for {from_currency}/{to_currency}: {e}")
            raise
    
    def get_cached_exchange_rates(self, from_currency, to_currency):
        """
        Load exchange rates from cache.
        
        Args:
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            DataFrame with exchange rates or None if not cached
        """
        cache_key = f"{from_currency}{to_currency}"
        cache_file = self.cache_dir / f"{cache_key}.csv"
        
        if not cache_file.exists():
            return None
        
        try:
            data = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            # Ensure timezone-naive after loading from cache
            if data.index.tz is not None:
                data.index = data.index.tz_localize(None)
            return data
        except Exception as e:
            print(f"Error loading cached rates: {e}")
            return None
    
    def save_exchange_rates(self, from_currency, to_currency, data):
        """
        Save exchange rates to cache.
        
        Args:
            from_currency: Source currency
            to_currency: Target currency
            data: DataFrame with exchange rates
        """
        cache_key = f"{from_currency}{to_currency}"
        cache_file = self.cache_dir / f"{cache_key}.csv"
        
        try:
            data.to_csv(cache_file)
        except Exception as e:
            print(f"Error saving exchange rates to cache: {e}")
    
    def get_exchange_rates(self, from_currency, to_currency, start_date, end_date, use_cache=True):
        """
        Get exchange rates, using cache if available.
        
        Strategy:
        1. Check memory cache (fastest)
        2. Check disk cache (fast, persistent)
        3. Fetch from yfinance (slow, only if cache doesn't cover dates)
        
        Args:
            from_currency: Source currency
            to_currency: Target currency
            start_date: Start date
            end_date: End date
            use_cache: Whether to use cached data
            
        Returns:
            DataFrame with exchange rates
        """
        if from_currency == to_currency:
            # No conversion needed - return 1.0
            dates = pd.date_range(start_date, end_date, freq='D')
            return pd.DataFrame({'Close': 1.0}, index=dates)
        
        # Convert string dates to Timestamps for comparison
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        cache_key = f"{from_currency}{to_currency}"
        
        # STEP 1: Check memory cache first (fastest)
        if cache_key in self.exchange_rate_cache:
            cached_data = self.exchange_rate_cache[cache_key]
            # Check if cache covers the date range
            if cached_data.index.min() <= start_ts and cached_data.index.max() >= end_ts:
                return cached_data.loc[start_date:end_date].copy()
        
        # STEP 2: Check disk cache (fast, persistent between app restarts)
        if use_cache:
            cached_data = self.get_cached_exchange_rates(from_currency, to_currency)
            
            if cached_data is not None:
                # Check if cache fully covers the requested date range
                if cached_data.index.min() <= start_ts and cached_data.index.max() >= end_ts:
                    # Cache covers everything - use it!
                    self.exchange_rate_cache[cache_key] = cached_data
                    return cached_data.loc[start_date:end_date].copy()
                
                # Cache exists but doesn't cover the full range - update it
                if cached_data.index.max() < end_ts:
                    # Check if we're asking for very recent data (today/yesterday)
                    # Markets may not have data yet
                    days_missing = (end_ts - cached_data.index.max()).days
                    
                    if days_missing <= 2:
                        # Only 1-2 days missing - likely just today/yesterday
                        # Use what we have without trying to fetch
                        self.exchange_rate_cache[cache_key] = cached_data
                        return cached_data.loc[start_date:end_date].copy()
                    
                    # Need to fetch missing dates at the end
                    try:
                        new_start = cached_data.index.max() + pd.Timedelta(days=1)
                        print(f"  Updating {from_currency}/{to_currency}: fetching {new_start.strftime('%Y-%m-%d')} to {end_date}")
                        new_data = self.fetch_exchange_rates(from_currency, to_currency, 
                                                            new_start.strftime('%Y-%m-%d'), end_date)
                        # Merge
                        cached_data = pd.concat([cached_data, new_data])
                        cached_data = cached_data[~cached_data.index.duplicated(keep='last')]
                        cached_data = cached_data.sort_index()
                        # Save updated cache
                        self.save_exchange_rates(from_currency, to_currency, cached_data)
                        self.exchange_rate_cache[cache_key] = cached_data
                        return cached_data.loc[start_date:end_date].copy()
                    except Exception as e:
                        # Update failed - use what we have
                        print(f"  Note: Using cached data (update failed: {str(e)[:50]})")
                        self.exchange_rate_cache[cache_key] = cached_data
                        # Return what we can (may be partial)
                        available_start = max(start_ts, cached_data.index.min())
                        available_end = min(end_ts, cached_data.index.max())
                        return cached_data.loc[available_start:available_end].copy()
        
        # STEP 3: No cache available - fetch fresh data
        try:
            print(f"Fetching {from_currency}/{to_currency} from yfinance: {start_date} to {end_date}")
            data = self.fetch_exchange_rates(from_currency, to_currency, start_date, end_date)
            
            # Save to cache for next time
            if use_cache:
                self.save_exchange_rates(from_currency, to_currency, data)
                self.exchange_rate_cache[cache_key] = data
            
            return data.copy()
            
        except Exception as e:
            # Last resort: try disk cache even if we didn't find it earlier
            # (in case it was created by another process)
            if use_cache:
                cached_data = self.get_cached_exchange_rates(from_currency, to_currency)
                if cached_data is not None:
                    print(f"Warning: Fetch failed, using cached data for {from_currency}/{to_currency}")
                    self.exchange_rate_cache[cache_key] = cached_data
                    # Return what we have
                    available_start = max(start_ts, cached_data.index.min())
                    available_end = min(end_ts, cached_data.index.max())
                    return cached_data.loc[available_start:available_end].copy()
            
            # No cache available at all - error
            print(f"Error: Cannot get exchange rates for {from_currency}/{to_currency}: {e}")
            raise
    
    def convert_via_usd(self, data, from_currency, to_currency, use_cache=True):
        """
        Convert currency via USD as intermediate (hub-and-spoke pattern).
        
        This simplifies conversions by always using USD as the bridge currency.
        Only requires USD↔X pairs, not arbitrary X↔Y cross rates.
        
        Example: CHF → EUR
          CHF → USD (invert CHF=X)
          USD → EUR (use EUR=X)
        
        Args:
            data: DataFrame with OHLC data
            from_currency: Source currency (e.g., 'CHF')
            to_currency: Target currency (e.g., 'EUR')
            use_cache: Whether to use cached exchange rates
            
        Returns:
            DataFrame with converted prices
        """
        # Same currency - no conversion
        if from_currency == to_currency:
            return data.copy()
        
        # Step 1: Convert to USD (if not already USD)
        if from_currency != 'USD':
            usd_data = self.convert_ohlc_data(data, from_currency, 'USD', use_cache)
        else:
            usd_data = data
        
        # Step 2: Convert from USD to target (if not USD)
        if to_currency != 'USD':
            final_data = self.convert_ohlc_data(usd_data, 'USD', to_currency, use_cache)
        else:
            final_data = usd_data
        
        return final_data
    
    def convert_ohlc_data(self, data, from_currency, to_currency, use_cache=True):
        """
        Convert OHLC price data from one currency to another.
        
        Args:
            data: DataFrame with OHLC data (must have DatetimeIndex)
            from_currency: Source currency
            to_currency: Target currency
            use_cache: Whether to use cached exchange rates
            
        Returns:
            DataFrame with converted prices
        """
        if from_currency == to_currency:
            # No conversion needed
            return data.copy()
        
        if len(data) == 0:
            return data
        
        # Get exchange rates for the date range
        start_date = data.index.min().strftime('%Y-%m-%d')
        end_date = data.index.max().strftime('%Y-%m-%d')
        
        try:
            rates = self.get_exchange_rates(from_currency, to_currency, 
                                          start_date, end_date, use_cache=use_cache)
        except Exception as e:
            print(f"Warning: Could not get exchange rates for {from_currency}/{to_currency}: {e}")
            print("Returning unconverted data.")
            return data.copy()
        
        # Align rates with data dates (forward fill for weekends/holidays)
        rates_aligned = rates.reindex(data.index, method='ffill')
        
        # Convert OHLC prices
        converted_data = data.copy()
        for col in ['Open', 'High', 'Low', 'Close']:
            if col in converted_data.columns:
                converted_data[col] = converted_data[col] * rates_aligned['Close']
        
        # Store conversion info in attributes
        converted_data.attrs['original_currency'] = from_currency
        converted_data.attrs['converted_to'] = to_currency
        
        return converted_data
    
    def clear_memory_cache(self):
        """Clear the in-memory exchange rate cache."""
        self.exchange_rate_cache = {}
        print("Memory cache cleared")
    
    def clear_all_cache(self):
        """Clear both memory and disk cache."""
        # Clear memory cache
        self.exchange_rate_cache = {}
        
        # Clear disk cache
        import shutil
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            print("All cache (memory and disk) cleared")
        else:
            print("Memory cache cleared (no disk cache found)")
    
    def convert_ticker_data(self, ticker_data, ticker_currencies, target_currency, use_cache=True):
        """
        Convert all ticker data to a target currency using USD as intermediate.
        
        This uses the hub-and-spoke pattern:
        - All conversions go through USD
        - Only need USD↔X pairs, not X↔Y cross rates
        
        Example: Convert CHF ticker to EUR
          CHF → USD → EUR (two steps via USD hub)
        
        Args:
            ticker_data: Dictionary of {ticker: DataFrame}
            ticker_currencies: Dictionary of {ticker: currency}
            target_currency: Target currency code (e.g., 'CHF')
            use_cache: Whether to use cached exchange rates
            
        Returns:
            Dictionary of {ticker: converted DataFrame}
        """
        converted_data = {}
        
        for ticker, data in ticker_data.items():
            # Get the ORIGINAL currency for this ticker from config
            from_currency = ticker_currencies.get(ticker, 'USD')
            
            try:
                print(f"Converting {ticker} ({from_currency} → {target_currency})")
                
                # Use USD as intermediate hub
                converted = self.convert_via_usd(
                    data.copy(),  # Use original data
                    from_currency,  # From original currency
                    target_currency,  # To target currency
                    use_cache
                )
                
                converted.attrs['ticker'] = ticker
                converted.attrs['original_currency'] = from_currency
                converted.attrs['display_currency'] = target_currency
                converted_data[ticker] = converted
                
            except Exception as e:
                print(f"Error converting {ticker} from {from_currency} to {target_currency}: {e}")
                import traceback
                traceback.print_exc()
                # Use original data if conversion fails
                converted_data[ticker] = data.copy()
        
        return converted_data