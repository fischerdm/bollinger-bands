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


def calculate_levy_relative_strength(data, benchmark_data=None, months=6):
    """
    Calculate Levy's Relative Strength indicator.
    
    If benchmark_data is provided:
        Levy's RS = Asset Performance - Benchmark Performance (excess return)
    If benchmark_data is None:
        Levy's RS = Asset Performance (absolute return)
    
    Args:
        data: DataFrame with OHLC data for the asset
        benchmark_data: Optional DataFrame with OHLC data for benchmark
        months: Lookback period in months (default 6)
        
    Returns:
        Float representing Levy's relative strength as a percentage
    """
    lookback_days = months * 21
    
    if len(data) < lookback_days:
        return np.nan
    
    # Calculate asset performance
    current_price = data['Close'].iloc[-1]
    past_price = data['Close'].iloc[-lookback_days]
    
    if past_price == 0:
        return np.nan
    
    asset_performance = ((current_price / past_price) - 1) * 100
    
    # If no benchmark, return absolute performance
    if benchmark_data is None:
        return asset_performance
    
    # Calculate benchmark performance
    if len(benchmark_data) < lookback_days:
        return np.nan
    
    bench_current = benchmark_data['Close'].iloc[-1]
    bench_past = benchmark_data['Close'].iloc[-lookback_days]
    
    if bench_past == 0:
        return np.nan
    
    bench_performance = ((bench_current / bench_past) - 1) * 100
    
    # Return relative strength (excess return vs benchmark)
    levy_rs = asset_performance - bench_performance
    
    return levy_rs


def calculate_all_metrics(data, benchmark_data=None):
    """
    Calculate all relative strength metrics for a ticker.
    
    Args:
        data: DataFrame with OHLC data
        benchmark_data: Optional DataFrame with benchmark OHLC data
        
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
    
    levy_rs = calculate_levy_relative_strength(data, benchmark_data, months=6)
    
    return {
        '6M_perf': perf_6m,
        '12M_perf': perf_12m,
        'avg_perf': avg_perf,
        'levy_rs': levy_rs
    }


def calculate_metrics_at_date(data, target_date, benchmark_data=None):
    """
    Calculate relative strength metrics as of a specific date.
    
    Args:
        data: DataFrame with OHLC data
        target_date: Date to calculate metrics at
        benchmark_data: Optional DataFrame with benchmark OHLC data
        
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
    
    # Filter benchmark data if provided
    benchmark_subset = None
    if benchmark_data is not None:
        benchmark_subset = benchmark_data[benchmark_data.index <= target_date]
        if len(benchmark_subset) == 0:
            benchmark_subset = None
    
    return calculate_all_metrics(data_subset, benchmark_subset)


def get_all_tickers_metrics(ticker_data, reference_ticker='URTH', target_date=None):
    """
    Calculate metrics for all tickers.
    
    Args:
        ticker_data: Dictionary mapping ticker symbols to DataFrames
        reference_ticker: Ticker symbol to use as benchmark (default: 'URTH')
        target_date: Optional date to calculate metrics at (default: latest)
        
    Returns:
        DataFrame with metrics for all tickers
    """
    results = []
    
    # Get benchmark data
    benchmark_data = ticker_data.get(reference_ticker)
    
    # Warn if benchmark not available
    if benchmark_data is None and reference_ticker is not None:
        print(f"Warning: Benchmark ticker '{reference_ticker}' not found in data. Using absolute performance for Levy RS.")
    
    for ticker, data in ticker_data.items():
        # Don't compare benchmark to itself (would be 0)
        current_benchmark = None if ticker == reference_ticker else benchmark_data
        
        if target_date is not None:
            metrics = calculate_metrics_at_date(data, target_date, current_benchmark)
        else:
            metrics = calculate_all_metrics(data, current_benchmark)
        
        results.append({
            'ticker': ticker,
            '6M Performance (%)': metrics['6M_perf'],
            '12M Performance (%)': metrics['12M_perf'],
            'Avg Performance (%)': metrics['avg_perf'],
            'Levy RS (%)': metrics['levy_rs']
        })
    
    df = pd.DataFrame(results)
    return df
