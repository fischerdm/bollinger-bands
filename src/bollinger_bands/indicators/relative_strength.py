"""
Relative Strength Calculations Module

This module handles all relative strength related calculations including:
- 6-month and 12-month performance
- Levy's relative strength indicator
"""

import pandas as pd
import numpy as np


def calculate_performance(data, months):
    """
    Calculate performance over a specified number of months.
    
    Args:
        data: DataFrame with OHLC data
        months: Number of months to look back
        
    Returns:
        Float representing the percentage performance
    """
    if len(data) < 2:
        return np.nan
    
    # Calculate trading days (approximately 21 trading days per month)
    lookback_days = months * 21
    
    if len(data) < lookback_days:
        return np.nan
    
    current_price = data['Close'].iloc[-1]
    past_price = data['Close'].iloc[-lookback_days]
    
    if past_price == 0:
        return np.nan
    
    performance = ((current_price - past_price) / past_price) * 100
    return performance


def calculate_levy_relative_strength(data, months=6):
    """
    Calculate Levy's Relative Strength indicator.
    
    Levy's RS = (Current Price / n-period Moving Average) - 1
    
    Args:
        data: DataFrame with OHLC data
        months: Period for the moving average (default 6 months)
        
    Returns:
        Float representing Levy's relative strength as a percentage
    """
    if len(data) < 2:
        return np.nan
    
    # Calculate trading days
    period_days = months * 21
    
    if len(data) < period_days:
        return np.nan
    
    current_price = data['Close'].iloc[-1]
    ma = data['Close'].iloc[-period_days:].mean()
    
    if ma == 0:
        return np.nan
    
    levy_rs = ((current_price / ma) - 1) * 100
    return levy_rs


def calculate_all_metrics(data):
    """
    Calculate all relative strength metrics for a ticker.
    
    Args:
        data: DataFrame with OHLC data
        
    Returns:
        Dictionary with all metrics
    """
    perf_6m = calculate_performance(data, 6)
    perf_12m = calculate_performance(data, 12)
    
    # Average of 6M and 12M performance
    if not np.isnan(perf_6m) and not np.isnan(perf_12m):
        avg_perf = (perf_6m + perf_12m) / 2
    else:
        avg_perf = np.nan
    
    levy_rs = calculate_levy_relative_strength(data, 6)
    
    return {
        '6M_perf': perf_6m,
        '12M_perf': perf_12m,
        'avg_perf': avg_perf,
        'levy_rs': levy_rs
    }


def calculate_metrics_at_date(data, target_date):
    """
    Calculate relative strength metrics as of a specific date.
    
    Args:
        data: DataFrame with OHLC data
        target_date: Date to calculate metrics at
        
    Returns:
        Dictionary with all metrics
    """
    # Filter data up to target date
    data_subset = data[data.index <= target_date]
    
    if len(data_subset) == 0:
        return {
            '6M_perf': np.nan,
            '12M_perf': np.nan,
            'avg_perf': np.nan,
            'levy_rs': np.nan
        }
    
    return calculate_all_metrics(data_subset)


def get_all_tickers_metrics(ticker_data, target_date=None):
    """
    Calculate metrics for all tickers.
    
    Args:
        ticker_data: Dictionary mapping ticker symbols to DataFrames
        target_date: Optional date to calculate metrics at (default: latest)
        
    Returns:
        DataFrame with metrics for all tickers
    """
    results = []
    
    for ticker, data in ticker_data.items():
        if target_date is not None:
            metrics = calculate_metrics_at_date(data, target_date)
        else:
            metrics = calculate_all_metrics(data)
        
        results.append({
            'ticker': ticker,
            '6M Performance (%)': metrics['6M_perf'],
            '12M Performance (%)': metrics['12M_perf'],
            'Avg Performance (%)': metrics['avg_perf'],
            'Levy RS (%)': metrics['levy_rs']
        })
    
    df = pd.DataFrame(results)
    return df
