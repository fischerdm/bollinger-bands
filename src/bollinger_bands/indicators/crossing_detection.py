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
