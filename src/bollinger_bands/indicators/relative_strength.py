"""
Relative Strength Calculations Module

This module handles all relative strength related calculations including:
- 6-month and 12-month performance
- Levy's relative strength indicator
"""

import pandas as pd
import numpy as np

from bollinger_bands import data


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


def calculate_levy_rs_original(data, months=6):
    """
    Calculate original Levy's Relative Strength indicator.
    
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


def calculate_levy_relative_strength(data, benchmark_data=None, months=6):
    """
    Calculate Levy's Relative Strength indicator.
    
    If benchmark_data is provided:
        Levy's RS = Asset Performance / Benchmark Performance (ratio-based)
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
    
    # Return relative strength as ratio
    # Convert percentages to multipliers, divide, then back to percentage
    asset_multiplier = 1 + (asset_performance / 100)
    bench_multiplier = 1 + (bench_performance / 100)
    
    if bench_multiplier == 0:
        return np.nan
    
    # relative_ratio = (asset_multiplier / bench_multiplier - 1) * 100
    relative_ratio = asset_multiplier / bench_multiplier
    
    # print(f"DEBUG: {data.attrs.get('ticker', 'unknown')}: asset={asset_performance:.2f}%, bench={bench_performance:.2f}%, ratio={relative_ratio:.4f}")

    return relative_ratio


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
    
    # Original Levy RS (Price / MA - 1)
    levy_rs_original = calculate_levy_rs_original(data, months=6)
    
    # Relative performance vs benchmark (6M return difference)
    levy_rs_relative = calculate_levy_relative_strength(data, benchmark_data, months=6)
    
    return {
        '6M_perf': perf_6m,
        '12M_perf': perf_12m,
        'avg_perf': avg_perf,
        'levy_rs_original': levy_rs_original,  # Price/MA formula
        'levy_rs_relative': levy_rs_relative   # Return vs benchmark
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
            'levy_rs_original': np.nan,
            'levy_rs_relative': np.nan
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
        print(f"Warning: Benchmark ticker '{reference_ticker}' not found in data. Relative metrics will be N/A.")
    
    for ticker, data in ticker_data.items():
        if target_date is not None:
            # For original Levy RS: never use benchmark (always Price/MA)
            metrics = calculate_metrics_at_date(data, target_date, benchmark_data=None)
            
            # For relative metrics: use benchmark only if ticker != benchmark
            if ticker != reference_ticker and benchmark_data is not None:
                benchmark_subset = benchmark_data[benchmark_data.index <= target_date]
                if len(benchmark_subset) > 0:
                    metrics_rel = calculate_metrics_at_date(data, target_date, benchmark_data=benchmark_subset)
                    levy_rs_relative = metrics_rel['levy_rs_relative']
                else:
                    levy_rs_relative = np.nan
            else:
                levy_rs_relative = 0.0 if ticker == reference_ticker else np.nan
        else:
            # For original Levy RS: never use benchmark (always Price/MA)
            metrics = calculate_all_metrics(data, benchmark_data=None)
            
            # For relative metrics: use benchmark only if ticker != benchmark
            if ticker != reference_ticker and benchmark_data is not None:
                metrics_rel = calculate_all_metrics(data, benchmark_data=benchmark_data)
                levy_rs_relative = metrics_rel['levy_rs_relative']
            else:
                levy_rs_relative = 0.0 if ticker == reference_ticker else np.nan
        
        results.append({
            'ticker': ticker,
            '6M Performance (%)': metrics['6M_perf'],
            '12M Performance (%)': metrics['12M_perf'],
            'Avg Performance (%)': metrics['avg_perf'],
            'Levy RS (%)': metrics['levy_rs_original'],  # Original Price/MA formula
            '6M Perf Rel. Bench': levy_rs_relative    # Relative to benchmark
        })
    
    df = pd.DataFrame(results)
    return df
