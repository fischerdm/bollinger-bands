#!/usr/bin/env python3
"""
Currency Conversion Test Suite

Tests for the currency conversion system including:
1. Exchange rate downloads
2. Currency conversions
3. Cache functionality
4. Switching between currencies

Usage:
    python test_currency_conversion.py
"""

import sys
from pathlib import Path
import pandas as pd
import shutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from bollinger_bands.data.storage_manager import DataStorageManager
from bollinger_bands.data.currency_converter import CurrencyConverter


class CurrencyConversionTests:
    """Test suite for currency conversion."""
    
    def __init__(self):
        self.storage = DataStorageManager('config/tickers.yaml')
        self.converter = CurrencyConverter(
            self.storage.config,
            cache_dir='data/test_currencies'  # Use test directory
        )
        self.test_passed = 0
        self.test_failed = 0
        
    def setup(self):
        """Setup test environment."""
        print("\n" + "="*80)
        print("SETUP: Creating test environment")
        print("="*80)
        
        # Create test cache directory
        test_dir = Path('data/test_currencies')
        if test_dir.exists():
            shutil.rmtree(test_dir)
        test_dir.mkdir(parents=True, exist_ok=True)
        print("✓ Created test cache directory")
        
    def teardown(self):
        """Cleanup test environment."""
        print("\n" + "="*80)
        print("TEARDOWN: Cleaning up")
        print("="*80)
        
        # Remove test cache directory
        test_dir = Path('data/test_currencies')
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print("✓ Removed test cache directory")
        
    def assert_true(self, condition, test_name, message=""):
        """Assert a condition is true."""
        if condition:
            print(f"  ✓ {test_name}")
            self.test_passed += 1
        else:
            print(f"  ✗ {test_name}")
            if message:
                print(f"    {message}")
            self.test_failed += 1
            
    def assert_equal(self, actual, expected, test_name):
        """Assert two values are equal."""
        if actual == expected:
            print(f"  ✓ {test_name}")
            self.test_passed += 1
        else:
            print(f"  ✗ {test_name}")
            print(f"    Expected: {expected}")
            print(f"    Got: {actual}")
            self.test_failed += 1
            
    def assert_not_none(self, value, test_name):
        """Assert value is not None."""
        if value is not None:
            print(f"  ✓ {test_name}")
            self.test_passed += 1
        else:
            print(f"  ✗ {test_name}")
            print(f"    Value is None")
            self.test_failed += 1
    
    # ========================================================================
    # TEST 1: Exchange Rate Download
    # ========================================================================
    
    def test_exchange_rate_download(self):
        """Test downloading exchange rates from Yahoo Finance."""
        print("\n" + "="*80)
        print("TEST 1: Exchange Rate Download")
        print("="*80)
        
        # Test USD to CHF
        print("\n1.1 Download USD/CHF rates")
        try:
            rates = self.converter.get_exchange_rates(
                'USD', 'CHF',
                '2024-01-01', '2024-12-31',
                use_cache=True
            )
            
            self.assert_not_none(rates, "Rates downloaded")
            self.assert_true(len(rates) > 200, "Sufficient data points", 
                           f"Got {len(rates)} rows")
            self.assert_true('Close' in rates.columns, "Has Close column")
            
            # Check rate is reasonable (should be around 0.85-0.95)
            latest_rate = rates['Close'].iloc[-1]
            self.assert_true(0.70 < latest_rate < 1.10, 
                           f"Reasonable rate (~0.88)", 
                           f"Got {latest_rate:.4f}")
            
        except Exception as e:
            print(f"  ✗ Download failed: {e}")
            self.test_failed += 1
        
        # Test USD to EUR (inverted)
        print("\n1.2 Download USD/EUR rates (inverted from EURUSD)")
        try:
            rates = self.converter.get_exchange_rates(
                'USD', 'EUR',
                '2024-01-01', '2024-12-31',
                use_cache=True
            )
            
            self.assert_not_none(rates, "Rates downloaded")
            
            # EUR should be around 0.85-0.95 per USD
            latest_rate = rates['Close'].iloc[-1]
            self.assert_true(0.75 < latest_rate < 1.00,
                           f"Reasonable EUR rate (~0.92)",
                           f"Got {latest_rate:.4f}")
            
        except Exception as e:
            print(f"  ✗ Download failed: {e}")
            self.test_failed += 1
    
    # ========================================================================
    # TEST 2: Cache Functionality
    # ========================================================================
    
    def test_cache_functionality(self):
        """Test that caching works properly."""
        print("\n" + "="*80)
        print("TEST 2: Cache Functionality")
        print("="*80)
        
        # Test disk cache
        print("\n2.1 Disk cache saves and loads")
        
        # First download (creates cache)
        rates1 = self.converter.get_exchange_rates(
            'USD', 'CHF',
            '2024-01-01', '2024-06-30',
            use_cache=True
        )
        
        cache_file = Path('data/test_currencies/USDCHF.csv')
        self.assert_true(cache_file.exists(), "Cache file created")
        
        # Clear memory cache to force disk load
        self.converter.exchange_rate_cache = {}
        
        # Second load (from disk)
        rates2 = self.converter.get_exchange_rates(
            'USD', 'CHF',
            '2024-01-01', '2024-06-30',
            use_cache=True
        )
        
        self.assert_equal(len(rates1), len(rates2), 
                         "Same number of rows from cache")
        self.assert_true(
            (rates1['Close'] - rates2['Close']).abs().max() < 0.0001,
            "Same data from cache"
        )
        
        # Test memory cache
        print("\n2.2 Memory cache (same session)")
        
        # This should use memory cache (instant)
        import time
        start = time.time()
        rates3 = self.converter.get_exchange_rates(
            'USD', 'CHF',
            '2024-01-01', '2024-06-30',
            use_cache=True
        )
        elapsed = time.time() - start
        
        self.assert_true(elapsed < 0.1, 
                        f"Memory cache is fast (<100ms)",
                        f"Took {elapsed*1000:.1f}ms")
    
    # ========================================================================
    # TEST 3: Currency Conversion
    # ========================================================================
    
    def test_currency_conversion(self):
        """Test converting price data between currencies."""
        print("\n" + "="*80)
        print("TEST 3: Currency Conversion")
        print("="*80)
        
        # Create sample price data
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        sample_data = pd.DataFrame({
            'Open': 100.0,
            'High': 105.0,
            'Low': 95.0,
            'Close': 100.0
        }, index=dates)
        
        # Test USD to CHF
        print("\n3.1 Convert USD → CHF")
        try:
            chf_data = self.converter.convert_ohlc_data(
                sample_data.copy(),
                from_currency='USD',
                to_currency='CHF',
                use_cache=True
            )
            
            self.assert_not_none(chf_data, "Conversion succeeded")
            self.assert_equal(len(chf_data), len(sample_data), 
                            "Same number of rows")
            
            # Check converted values (should be ~88 CHF for 100 USD)
            rate = chf_data['Close'].iloc[-1] / sample_data['Close'].iloc[-1]
            self.assert_true(0.70 < rate < 1.10,
                           f"Reasonable conversion rate",
                           f"Got {rate:.4f}")
            
        except Exception as e:
            print(f"  ✗ Conversion failed: {e}")
            self.test_failed += 1
        
        # Test round-trip (USD → CHF → USD)
        print("\n3.2 Round-trip conversion (USD → CHF → USD)")
        try:
            # Convert to CHF
            chf_data = self.converter.convert_ohlc_data(
                sample_data.copy(),
                'USD', 'CHF', use_cache=True
            )
            
            # Convert back to USD
            usd_data = self.converter.convert_ohlc_data(
                chf_data,
                'CHF', 'USD', use_cache=True
            )
            
            # Should get back original values (within rounding)
            diff = (usd_data['Close'] - sample_data['Close']).abs().max()
            self.assert_true(diff < 0.01,
                           "Round-trip preserves values",
                           f"Max diff: {diff:.6f}")
            
        except Exception as e:
            print(f"  ✗ Round-trip failed: {e}")
            self.test_failed += 1
        
        # Test via USD hub (CHF → EUR)
        print("\n3.3 Hub-and-spoke conversion (CHF → EUR via USD)")
        try:
            # Create CHF data
            chf_sample = pd.DataFrame({
                'Open': 88.0,
                'High': 92.0,
                'Low': 84.0,
                'Close': 88.0
            }, index=dates)
            
            # Convert CHF → EUR (via USD)
            eur_data = self.converter.convert_via_usd(
                chf_sample.copy(),
                'CHF', 'EUR', use_cache=True
            )
            
            self.assert_not_none(eur_data, "Hub conversion succeeded")
            
            # CHF → USD → EUR should give reasonable result
            # 88 CHF → ~100 USD → ~92 EUR
            rate = eur_data['Close'].iloc[-1] / chf_sample['Close'].iloc[-1]
            self.assert_true(0.80 < rate < 1.20,
                           f"Reasonable hub conversion rate",
                           f"Got {rate:.4f}")
            
        except Exception as e:
            print(f"  ✗ Hub conversion failed: {e}")
            self.test_failed += 1
    
    # ========================================================================
    # TEST 4: Switching Between Currencies
    # ========================================================================
    
    def test_currency_switching(self):
        """Test switching between currencies multiple times."""
        print("\n" + "="*80)
        print("TEST 4: Switching Between Currencies")
        print("="*80)
        
        # Create sample data
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        usd_data = pd.DataFrame({
            'Open': 100.0,
            'High': 105.0,
            'Low': 95.0,
            'Close': 100.0
        }, index=dates)
        
        print("\n4.1 Rapid currency switching")
        
        conversions = [
            ('USD', 'CHF'),
            ('USD', 'EUR'),
            ('USD', 'CHF'),  # Repeat
            ('USD', 'GBP'),
            ('USD', 'CHF'),  # Repeat again
            ('USD', 'EUR'),  # Repeat
        ]
        
        results = {}
        import time
        
        for from_curr, to_curr in conversions:
            start = time.time()
            try:
                converted = self.converter.convert_ohlc_data(
                    usd_data.copy(),
                    from_curr, to_curr,
                    use_cache=True
                )
                elapsed = time.time() - start
                
                key = f"{from_curr}/{to_curr}"
                if key not in results:
                    results[key] = []
                results[key].append({
                    'data': converted,
                    'time': elapsed
                })
                
                print(f"  {from_curr}→{to_curr}: {elapsed*1000:.0f}ms")
                
            except Exception as e:
                print(f"  ✗ {from_curr}→{to_curr} failed: {e}")
                self.test_failed += 1
        
        # Check that repeated conversions give same results
        print("\n4.2 Consistency check")
        
        for key, conversions_list in results.items():
            if len(conversions_list) > 1:
                first = conversions_list[0]['data']
                for i, conv in enumerate(conversions_list[1:], 1):
                    diff = (first['Close'] - conv['data']['Close']).abs().max()
                    self.assert_true(
                        diff < 0.01,
                        f"{key} attempt #{i+1} matches first",
                        f"Max diff: {diff:.6f}"
                    )
        
        # Check that cache speeds up repeated requests
        print("\n4.3 Cache performance check")
        
        for key, conversions_list in results.items():
            if len(conversions_list) > 1:
                first_time = conversions_list[0]['time']
                second_time = conversions_list[1]['time']
                
                # Second should be much faster (cached)
                speedup = first_time / second_time if second_time > 0 else float('inf')
                self.assert_true(
                    second_time < first_time or second_time < 0.1,
                    f"{key} uses cache (speedup: {speedup:.1f}x)",
                    f"First: {first_time*1000:.0f}ms, Second: {second_time*1000:.0f}ms"
                )
    
    # ========================================================================
    # TEST 5: Edge Cases
    # ========================================================================
    
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        print("\n" + "="*80)
        print("TEST 5: Edge Cases")
        print("="*80)
        
        # Test same currency (no conversion)
        print("\n5.1 Same currency (no conversion needed)")
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        data = pd.DataFrame({'Close': 100.0}, index=dates)
        
        result = self.converter.convert_ohlc_data(
            data.copy(), 'USD', 'USD', use_cache=True
        )
        
        self.assert_true(
            (result['Close'] == data['Close']).all(),
            "Same currency returns unchanged data"
        )
        
        # Test empty data
        print("\n5.2 Empty data")
        empty_data = pd.DataFrame(columns=['Open', 'High', 'Low', 'Close'])
        empty_data.index = pd.DatetimeIndex([])
        
        result = self.converter.convert_ohlc_data(
            empty_data, 'USD', 'CHF', use_cache=True
        )
        
        self.assert_true(len(result) == 0, "Empty data handled correctly")
        
        # Test single day
        print("\n5.3 Single day conversion")
        single_day = pd.DataFrame({
            'Open': 100.0,
            'High': 105.0,
            'Low': 95.0,
            'Close': 100.0
        }, index=[pd.Timestamp('2024-01-01')])
        
        try:
            result = self.converter.convert_ohlc_data(
                single_day, 'USD', 'CHF', use_cache=True
            )
            self.assert_equal(len(result), 1, "Single day works")
        except Exception as e:
            print(f"  ✗ Single day failed: {e}")
            self.test_failed += 1
    
    # ========================================================================
    # RUN ALL TESTS
    # ========================================================================
    
    def run_all(self):
        """Run all tests."""
        print("\n" + "="*80)
        print("CURRENCY CONVERSION TEST SUITE")
        print("="*80)
        
        self.setup()
        
        try:
            self.test_exchange_rate_download()
            self.test_cache_functionality()
            self.test_currency_conversion()
            self.test_currency_switching()
            self.test_edge_cases()
        finally:
            self.teardown()
        
        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Passed: {self.test_passed}")
        print(f"Failed: {self.test_failed}")
        print(f"Total:  {self.test_passed + self.test_failed}")
        
        if self.test_failed == 0:
            print("\n✓ ALL TESTS PASSED! 🎉")
        else:
            print(f"\n✗ {self.test_failed} TESTS FAILED")
        
        print("="*80 + "\n")
        
        return self.test_failed == 0


if __name__ == '__main__':
    tests = CurrencyConversionTests()
    success = tests.run_all()
    sys.exit(0 if success else 1)
