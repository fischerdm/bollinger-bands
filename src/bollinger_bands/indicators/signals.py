"""
Trading Signals Module

This module contains all candlestick pattern detection and signal generation logic.
"""

import pandas as pd
import numpy as np


def detect_bullish_engulfing(data):
    """Detect bullish engulfing candlestick pattern"""
    signals = pd.Series(False, index=data.index)
    
    for i in range(1, len(data)):
        prev_open = data['Open'].iloc[i-1]
        prev_close = data['Close'].iloc[i-1]
        curr_open = data['Open'].iloc[i]
        curr_close = data['Close'].iloc[i]
        
        prev_bearish = prev_close < prev_open
        curr_bullish = curr_close > curr_open
        engulfs = curr_open <= prev_close and curr_close >= prev_open
        
        if prev_bearish and curr_bullish and engulfs:
            signals.iloc[i] = True
    
    return signals


def detect_hammer(data):
    """Detect hammer and inverted hammer patterns"""
    signals = pd.Series(False, index=data.index)
    
    for i in range(len(data)):
        open_price = data['Open'].iloc[i]
        close_price = data['Close'].iloc[i]
        high_price = data['High'].iloc[i]
        low_price = data['Low'].iloc[i]
        
        body = abs(close_price - open_price)
        total_range = high_price - low_price
        
        if total_range == 0:
            continue
            
        lower_shadow = min(open_price, close_price) - low_price
        upper_shadow = high_price - max(open_price, close_price)
        
        is_hammer = (lower_shadow > 2 * body) and (upper_shadow < body)
        is_inverted = (upper_shadow > 2 * body) and (lower_shadow < body)
        
        if is_hammer or is_inverted:
            signals.iloc[i] = True
    
    return signals


def detect_morning_star(data):
    """Detect morning star pattern (3-candle reversal)"""
    signals = pd.Series(False, index=data.index)
    
    for i in range(2, len(data)):
        first_open = data['Open'].iloc[i-2]
        first_close = data['Close'].iloc[i-2]
        first_bearish = first_close < first_open
        
        second_open = data['Open'].iloc[i-1]
        second_close = data['Close'].iloc[i-1]
        second_body = abs(second_close - second_open)
        first_body = abs(first_close - first_open)
        second_small = second_body < 0.3 * first_body
        
        third_open = data['Open'].iloc[i]
        third_close = data['Close'].iloc[i]
        third_bullish = third_close > third_open
        
        recovers = third_close > (first_open + first_close) / 2
        
        if first_bearish and second_small and third_bullish and recovers:
            signals.iloc[i] = True
    
    return signals


def detect_reentry_signals(data, ma_values, bb_values, enabled_signals, bb_distance_threshold=10):
    """
    Detect re-entry signals combining candlestick patterns with MA and BB conditions.
    
    Args:
        data: OHLC DataFrame
        ma_values: Moving average values
        bb_values: Dictionary with 'upper', 'middle', 'lower' Bollinger Bands
        enabled_signals: List of enabled signal types ['engulfing', 'hammer', 'morning_star']
        bb_distance_threshold: Maximum distance from lower BB (%)
        
    Returns:
        Series of boolean values indicating re-entry signals
    """
    # Detect patterns based on enabled signals
    bullish_engulfing = detect_bullish_engulfing(data) if 'engulfing' in enabled_signals else pd.Series(False, index=data.index)
    hammer = detect_hammer(data) if 'hammer' in enabled_signals else pd.Series(False, index=data.index)
    morning_star = detect_morning_star(data) if 'morning_star' in enabled_signals else pd.Series(False, index=data.index)
    
    # Combine pattern signals
    any_reentry_signal = bullish_engulfing | hammer | morning_star
    
    # Check conditions
    is_below_ma = data['Close'] < ma_values
    bb_width = bb_values['upper'] - bb_values['lower']
    distance_pct = ((data['Close'] - bb_values['lower']) / bb_width) * 100
    near_lower_bb = distance_pct <= bb_distance_threshold
    
    # Final signal: pattern + below MA + near lower BB
    reentry_signals = any_reentry_signal & is_below_ma & near_lower_bb
    
    return reentry_signals
