"""
Crossing Detection Module

This module handles detection of price crossings below moving averages.
"""

import pandas as pd
import numpy as np


def detect_price_crossing_down_daily(data, ma_values, smoothing_window=5):
    """
    Detect when price crosses below MA for DAILY data with smoothing.
    Uses a moving average of the price to reduce noise.
    """
    crossing_signal = pd.Series(0, index=data.index, dtype=float)
    
    # Clean data - remove NaN values
    valid_mask = data['Close'].notna() & ma_values.notna()
    clean_data = data[valid_mask].copy()
    clean_ma = ma_values[valid_mask]
    
    if len(clean_data) < smoothing_window * 2:
        return crossing_signal
    
    # Apply smoothing to price to reduce noise
    smoothed_price = clean_data['Close'].rolling(window=smoothing_window, min_periods=1).mean()
    
    # Calculate if smoothed price is below MA
    is_below = smoothed_price < clean_ma
    is_above = smoothed_price >= clean_ma
    
    # Find transitions from above to below
    prev_above = is_above.shift(1).fillna(False)
    transitions = is_below & prev_above
    
    for i in range(len(clean_data)):
        if not transitions.iloc[i]:
            continue
            
        # Check if price was above MA for sufficient time before crossing
        lookback_start = max(0, i - smoothing_window)
        was_above = is_above.iloc[lookback_start:i]
        
        if was_above.sum() < smoothing_window * 0.6:  # At least 60% of days above
            continue
        
        # Check if price stays below MA for sufficient time after crossing
        lookahead_end = min(len(clean_data), i + smoothing_window)
        stays_below = is_below.iloc[i:lookahead_end]
        
        if stays_below.sum() >= smoothing_window * 0.6:  # At least 60% of days below
            crossing_signal.loc[clean_data.index[i]] = 1
    
    return crossing_signal


def detect_price_crossing_down_period(data, ma_values):
    """
    Detect when price crosses below MA for MONTHLY/QUARTERLY data.
    Simple and clean: Open >= MA and Close < MA means crossing occurred during the period.
    """
    crossing_signal = pd.Series(0, index=data.index, dtype=float)
    
    # Clean data - remove NaN values
    valid_mask = data['Open'].notna() & data['Close'].notna() & ma_values.notna()
    clean_data = data[valid_mask].copy()
    clean_ma = ma_values[valid_mask]
    
    if len(clean_data) < 2:
        return crossing_signal
    
    for i in range(len(clean_data)):
        period_open = clean_data['Open'].iloc[i]
        period_close = clean_data['Close'].iloc[i]
        period_ma = clean_ma.iloc[i]
        period_date = clean_data.index[i]
        
        # Check if price crossed down during this period
        # Open was above or at MA, Close is below MA
        if period_open >= period_ma and period_close < period_ma:
            crossing_signal.loc[period_date] = 1
            print(f"  Price crossing detected at {period_date.date()}: Open={period_open:.2f} >= MA={period_ma:.2f}, Close={period_close:.2f} < MA")
    
    return crossing_signal


def progressive_confirmation_check(crossing_date, data, display_data, ma_values, 
                                   ma_condition, confirmation_window=20, 
                                   confirmation_threshold=60, max_wait_days=60):
    """
    Progressive confirmation using sliding window after crossing.
    
    After price crosses below MA:
    1. Check daily from crossing date
    2. Use a sliding N-day window (confirmation_window)
    3. Confirm when MA conditions are met for >= X% of the window (confirmation_threshold)
    4. Maximum wait time: max_wait_days trading days
    
    Args:
        crossing_date: Date when crossing occurred (index from display_data)
        data: Daily OHLC data
        display_data: Monthly/Quarterly aggregated data  
        ma_values: Daily MA values
        ma_condition: Boolean series of daily MA conditions
        confirmation_window: Size of sliding window in trading days (default: 20)
        confirmation_threshold: Percentage of window that must have MA conditions (default: 60)
        max_wait_days: Maximum days to wait for confirmation (default: 60)
    
    Returns:
        tuple: (bool, str, date or None, date or None) - 
               (signal_confirmed, reason, actual_crossing_date, confirmation_date)
    """
    # Get the actual date from display_data
    if 'original_date' in display_data.columns:
        crossing_idx = display_data.index.get_loc(crossing_date)
        actual_crossing_date = display_data.loc[crossing_date, 'original_date']
    else:
        actual_crossing_date = crossing_date
    
    # Find daily data starting from crossing
    future_mask = data.index >= actual_crossing_date
    future_data = data[future_mask]
    
    if len(future_data) == 0:
        return False, "No data after crossing", actual_crossing_date, None
    
    # Limit search to max_wait_days
    max_search_date = actual_crossing_date + pd.Timedelta(days=max_wait_days * 1.5)  # Account for weekends
    search_mask = (data.index >= actual_crossing_date) & (data.index <= max_search_date)
    search_data = data[search_mask]
    
    if len(search_data) < confirmation_window:
        return False, f"Insufficient data for confirmation window ({len(search_data)} < {confirmation_window} days)", actual_crossing_date, None
    
    # Convert threshold from percentage to decimal
    threshold_decimal = confirmation_threshold / 100.0
    
    # Check each day as potential confirmation point (starting from confirmation_window days after crossing)
    for i in range(confirmation_window - 1, len(search_data)):
        check_date = search_data.index[i]
        
        # Get the sliding window ending at check_date
        window_start_idx = i - confirmation_window + 1
        window_dates = search_data.index[window_start_idx:i + 1]
        
        # Check MA conditions in this window
        window_conditions = ma_condition[window_dates]
        days_with_conditions = window_conditions.sum()
        condition_pct = days_with_conditions / confirmation_window
        
        # Check if price is still below MA at check_date
        if check_date in ma_values.index and check_date in data.index:
            price_at_check = data.loc[check_date, 'Close']
            ma_at_check = ma_values.loc[check_date]
            price_below_ma = price_at_check < ma_at_check
        else:
            continue
        
        # Both conditions must be met
        if condition_pct >= threshold_decimal and price_below_ma:
            days_to_confirm = (check_date - actual_crossing_date).days
            print(f"  ✓ Exit signal CONFIRMED for crossing at {actual_crossing_date.date()}:")
            print(f"    - Confirmed on: {check_date.date()} ({days_to_confirm} days after crossing)")
            print(f"    - MA conditions in window: {condition_pct:.1%} ({days_with_conditions}/{confirmation_window} days)")
            print(f"    - Price at confirmation: {price_at_check:.2f} < MA {ma_at_check:.2f}")
            return True, "Confirmed", actual_crossing_date, check_date
    
    # If we get here, confirmation failed
    print(f"  ✗ Exit signal REJECTED for crossing at {actual_crossing_date.date()}:")
    print(f"    - MA conditions not sustained within {max_wait_days} days")
    return False, f"Not confirmed within {max_wait_days} days", actual_crossing_date, None


def check_ma_conditions_for_next_period(crossing_date, data, display_data, ma_values, 
                                        ma_condition, threshold=0.5, period='monthly'):
    """
    DEPRECATED: Use progressive_confirmation_check instead.
    
    Two-part lookahead for monthly/quarterly crossings.
    Kept for backward compatibility.
    """
    # Find the next period after crossing
    crossing_idx = display_data.index.get_loc(crossing_date)
    
    if crossing_idx >= len(display_data) - 1:
        return False, "No next period available"
    
    next_period_date = display_data.index[crossing_idx + 1]
    
    # Get the date range for the next complete period
    if 'original_date' in display_data.columns:
        next_period_end = display_data.loc[next_period_date, 'original_date']
    else:
        next_period_end = next_period_date
    
    # Calculate start of next period
    if period == 'quarterly':
        # Start of next quarter
        next_period_start = pd.Timestamp(next_period_end.year, 
                                        ((next_period_end.month - 1) // 3) * 3 + 1, 1)
    else:  # monthly
        # Start of next month
        next_period_start = pd.Timestamp(next_period_end.year, next_period_end.month, 1)
    
    # Part 1: Check MA conditions throughout ALL of period P+1
    next_period_mask = (data.index >= next_period_start) & (data.index <= next_period_end)
    
    if next_period_mask.sum() == 0:
        return False, f"No daily data in next period ({next_period_start} to {next_period_end})"
    
    days_in_next_period = next_period_mask.sum()
    days_with_conditions = ma_condition[next_period_mask].sum()
    condition_pct = days_with_conditions / days_in_next_period
    
    ma_conditions_met = condition_pct >= threshold
    
    # Part 2: Check if price is still below MA at end of period P+1
    # Find the last available daily price at or before next_period_end
    price_mask = (data.index <= next_period_end)
    if price_mask.sum() == 0:
        return False, "No price data at end of next period"
    
    last_price_date = data.index[price_mask][-1]
    last_price = data.loc[last_price_date, 'Close']
    last_ma = ma_values.loc[last_price_date]
    
    price_below_ma = last_price < last_ma
    
    # Both conditions must be TRUE
    if ma_conditions_met and price_below_ma:
        print(f"  ✓ Exit signal CONFIRMED for crossing at {crossing_date.date()}:")
        print(f"    - MA conditions in next period: {condition_pct:.1%} ({days_with_conditions}/{days_in_next_period} days)")
        print(f"    - Price at end of next period: {last_price:.2f} < MA {last_ma:.2f}")
        return True, "Confirmed"
    else:
        reasons = []
        if not ma_conditions_met:
            reasons.append(f"MA conditions only {condition_pct:.1%} in next period (need {threshold:.1%})")
        if not price_below_ma:
            reasons.append(f"Price {last_price:.2f} not below MA {last_ma:.2f} at period end")
        print(f"  ✗ Exit signal REJECTED for crossing at {crossing_date.date()}: {'; '.join(reasons)}")
        return False, '; '.join(reasons)


def check_ma_conditions_for_period(period_end_date, period_start_date, daily_data, ma_condition, threshold=0.5):
    """
    Check if MA conditions (flat long + decreasing short) are met for a given period.
    
    Args:
        period_end_date: The end date of the period (monthly/quarterly candle close date)
        period_start_date: The start date of the period (monthly/quarterly candle open date)
        daily_data: Daily OHLC data
        ma_condition: Boolean series of daily MA conditions
        threshold: Minimum % of days that must have conditions met (0.5 = 50%)
    
    Returns:
        tuple: (bool, float, int, int) - (conditions_met, actual_percentage, days_with_condition, total_days)
    """
    # Find daily data between period start and end
    mask = (daily_data.index >= period_start_date) & (daily_data.index <= period_end_date)
    
    if mask.sum() == 0:
        return False, 0.0, 0, 0
    
    # Check what % of trading days had MA conditions met
    days_in_period = mask.sum()
    days_with_conditions = ma_condition[mask].sum()
    condition_pct = days_with_conditions / days_in_period
    
    return condition_pct >= threshold, condition_pct, days_with_conditions, days_in_period

