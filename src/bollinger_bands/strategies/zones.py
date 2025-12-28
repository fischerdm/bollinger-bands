"""
Zone Identification Module

This module handles identification of trading zones (entry to re-entry).
"""

import pandas as pd
from bollinger_bands.indicators.crossing_detection import check_ma_conditions_for_period
from bollinger_bands.strategies.strategies import apply_green_strategy, apply_orange_strategy


def identify_entry_zones_with_conditions(data, display_data, ma_values, reentry_signals, price_crossing, combined_ma_condition, ma_condition_threshold=0.5, period='daily', max_reentry_signals=1, allow_reentry_at_ma=False):
    """
    Two-phase zone identification:
    
    PHASE 1: Detect all patterns (no strategy applied)
    - For each exit signal, find:
      * Green zone: Exit → First Nth candlestick signal
      * Orange zone: Exit → First MA crossing up
    
    PHASE 2: Apply strategy (filter/combine patterns)
    - Strategy decides which zones to use for trading
    
    Args:
        max_reentry_signals: Candlestick signals needed for green zone
        allow_reentry_at_ma: Strategy preference (Phase 2)
    """
    
    # PHASE 1: PATTERN DETECTION
    # Detect all patterns without any strategy logic
    
    crossing_dates = display_data.index[price_crossing == 1].tolist()
    is_below = data['Close'] < ma_values
    
    print(f"=== PHASE 1: PATTERN DETECTION ({period}) ===")
    print(f"Exit signals: {len(crossing_dates)}")
    print(f"Signals for green zone: {max_reentry_signals}")
    
    all_green_patterns = []  # All potential green zones
    all_orange_patterns = []  # All potential orange zones
    
    # For each exit signal, find patterns
    for exit_signal in crossing_dates:
        # Find when zone becomes active (conditions met after exit)
        zone_active_date = None
        for i in range(len(data)):
            if data.index[i] < exit_signal:
                continue
            
            current_date = data.index[i]
            
            # Check MA conditions
            if period in ['monthly', 'quarterly']:
                if period == 'quarterly':
                    quarter = (current_date.month - 1) // 3 + 1
                    if quarter == 4:
                        period_end = pd.Timestamp(current_date.year, 12, 31)
                    else:
                        period_end = pd.Timestamp(current_date.year, quarter * 3, 1) + pd.offsets.MonthEnd(0)
                    period_start = pd.Timestamp(current_date.year, ((current_date.month - 1) // 3) * 3 + 1, 1)
                else:
                    period_start = pd.Timestamp(current_date.year, current_date.month, 1)
                    period_end = period_start + pd.offsets.MonthEnd(0)
                
                conditions_met, _, _, _ = check_ma_conditions_for_period(
                    period_end, period_start, data, combined_ma_condition, 
                    threshold=ma_condition_threshold
                )
            else:
                conditions_met = combined_ma_condition.iloc[i]
            
            if is_below.iloc[i] and conditions_met:
                zone_active_date = current_date
                break
        
        if zone_active_date is None:
            continue  # Exit signal never became active
        
        # Find GREEN pattern: First Nth candlestick signal after zone active
        collected_signals = []
        green_end = None
        for i in range(len(data)):
            if data.index[i] < zone_active_date:
                continue
            
            current_date = data.index[i]
            
            if reentry_signals.iloc[i]:
                collected_signals.append(current_date)
                if len(collected_signals) >= max_reentry_signals:
                    green_end = current_date
                    break
        
        if green_end:
            all_green_patterns.append({
                'exit_signal': exit_signal,
                'start': exit_signal,
                'signals': collected_signals.copy(),
                'end': green_end,
                'type': 'green'
            })
            print(f"  Green pattern: {exit_signal.date()} → {green_end.date()} (signals: {[s.date() for s in collected_signals]})")
        
        # Find ORANGE pattern: First MA crossing up after zone active
        orange_end = None
        for i in range(len(data)):
            if data.index[i] < zone_active_date:
                continue
            
            current_date = data.index[i]
            
            # Check if price crossed back above MA
            if not is_below.iloc[i]:
                orange_end = data.index[i-1] if i > 0 else current_date
                break
        
        if orange_end and (not green_end or orange_end < green_end):
            # Only create orange if it ends before green (or no green exists)
            all_orange_patterns.append({
                'exit_signal': exit_signal,
                'start': exit_signal,
                'signals': [],
                'end': orange_end,
                'type': 'orange'
            })
            print(f"  Orange pattern: {exit_signal.date()} → {orange_end.date()}")
    
    print(f"\nPatterns detected: {len(all_green_patterns)} green, {len(all_orange_patterns)} orange")
    
    # PHASE 2: APPLY STRATEGY
    print(f"\n=== PHASE 2: STRATEGY APPLICATION ===")
    
    if allow_reentry_at_ma:
        # Orange strategy: Accept MA crossings + candlestick signals
        zones = apply_orange_strategy(all_green_patterns, all_orange_patterns, data)
    else:
        # Green strategy: Only candlestick signals
        zones = apply_green_strategy(all_green_patterns, all_orange_patterns, data)
    
    # Sort by start date
    zones.sort(key=lambda z: z['start'])
    
    # Separate for display
    green_zones = [z for z in zones if z['type'] == 'green']
    orange_zones = [z for z in zones if z['type'] == 'orange']
    
    print(f"\nFinal zones: {len(green_zones)} green, {len(orange_zones)} orange")
    
    if green_zones:
        print(f"\n=== GREEN ZONES ===")
        for i, z in enumerate(green_zones[:10], 1):
            sigs = ', '.join([s.strftime('%Y-%m-%d') for s in z['reentry_signals']])
            print(f"{i}. {z['exit_signal'].strftime('%Y-%m-%d')} → {z['end'].strftime('%Y-%m-%d')} | {sigs}")
    
    if orange_zones:
        print(f"\n=== ORANGE ZONES ===")
        for i, z in enumerate(orange_zones[:10], 1):
            print(f"{i}. {z['exit_signal'].strftime('%Y-%m-%d')} → {z['end'].strftime('%Y-%m-%d')}")
    
    return zones
