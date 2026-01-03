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


def check_ma_conditions_for_next_period(crossing_date, data, display_data, ma_values, 
                                        ma_condition, threshold=0.5, period='monthly'):
    """
    NEW Two-part lookahead for monthly/quarterly crossings.
    
    When crossing detected in period P:
    1. Check MA conditions throughout ALL of period P+1 (next complete month/quarter)
    2. Verify price is still below MA at end of period P+1
    3. Both conditions must be met to confirm the exit signal
    
    Args:
        crossing_date: Date when crossing occurred (index from display_data)
        data: Daily OHLC data
        display_data: Monthly/Quarterly aggregated data
        ma_values: Daily MA values
        ma_condition: Boolean series of daily MA conditions
        threshold: Minimum % of days in P+1 that must have conditions met
        period: 'monthly' or 'quarterly'
    
    Returns:
        tuple: (bool, str) - (signal_confirmed, reason)
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

