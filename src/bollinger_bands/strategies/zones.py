"""
Zone Identification Module

This module handles identification of trading zones (entry to re-entry).
"""

import pandas as pd
from bollinger_bands.indicators.crossing_detection import check_ma_conditions_for_period


def identify_entry_zones_with_conditions(data, display_data, ma_values, reentry_signals, price_crossing, combined_ma_condition, ma_condition_threshold=0.5, period='daily', max_reentry_signals=1, allow_reentry_at_ma=False):
    """
    Two-phase zone identification:
    
    PHASE 1: Detect all patterns (no strategy applied)
    - For each exit signal, find:
      * Green zone: Exit → First Nth candlestick signal (not used by previous zones)
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
    used_signals = set()  # Track signals already assigned to zones (NEW)
    
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
            print(f"  Exit {exit_signal.date()}: Zone never became active (MA conditions never met)")
            continue  # Exit signal never became active
        
        print(f"  Exit {exit_signal.date()}: Zone active from {zone_active_date.date()}")
        
        # Find GREEN pattern: First Nth candlestick signal after THIS exit signal
        # IMPORTANT: Counter starts at 0 for each zone
        # IMPORTANT: Skip signals already used by previous zones
        collected_signals = []
        green_end = None
        for i in range(len(data)):
            if data.index[i] <= exit_signal:  # Must be AFTER the exit signal
                continue
            
            current_date = data.index[i]
            
            # Only collect signals that:
            # 1. Happen after zone became active
            # 2. Are actual reentry signals
            # 3. Haven't been used by previous zones (NEW)
            if current_date >= zone_active_date and reentry_signals.iloc[i]:
                if current_date not in used_signals:  # NEW: Skip if already used
                    collected_signals.append(current_date)
                    if len(collected_signals) >= max_reentry_signals:
                        green_end = current_date
                        # Mark these signals as consumed (NEW)
                        used_signals.update(collected_signals)
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
        else:
            if collected_signals:
                print(f"  Green pattern incomplete: {exit_signal.date()} found {len(collected_signals)}/{max_reentry_signals} signals (not enough)")
            else:
                print(f"  Green pattern: No valid signals found (all used by previous zones)")
        
        # Find ORANGE pattern: First MA crossing up
        # For monthly/quarterly: use period-end data (display_data)
        # For daily: use daily data
        orange_end = None
        
        if period in ['monthly', 'quarterly']:
            # Use display_data (aggregated periods) for MA crossing detection
            # Find the period where close is above MA
            for i in range(len(display_data)):
                period_date = display_data.index[i]
                
                if period_date <= exit_signal:
                    continue
                
                # Get MA value at this period's end date
                if 'original_date' in display_data.columns:
                    actual_date = display_data.loc[period_date, 'original_date']
                else:
                    actual_date = period_date
                
                # Find MA value at this date
                ma_at_date = ma_values.reindex([actual_date], method='nearest').iloc[0]
                period_close = display_data.loc[period_date, 'Close']
                
                # If close is above MA, we've crossed back
                if period_close >= ma_at_date:
                    orange_end = actual_date
                    print(f"    Found MA crossing: period {period_date.date()}, close {period_close:.2f} >= MA {ma_at_date:.2f}, zone ends {orange_end.date()}")
                    break
        else:
            # Daily: look at daily data
            for i in range(len(data)):
                if data.index[i] <= exit_signal:
                    continue
                
                current_date = data.index[i]
                
                # Check if price is above MA
                if data['Close'].iloc[i] >= ma_values.iloc[i]:
                    orange_end = current_date
                    print(f"    Found MA crossing: price above MA at {current_date.date()}, zone ends {orange_end.date()}")
                    break
        
        if orange_end:
            # Always create orange pattern (strategy will decide which to use)
            all_orange_patterns.append({
                'exit_signal': exit_signal,
                'start': exit_signal,
                'signals': [],
                'end': orange_end,
                'type': 'orange'
            })
            print(f"  Orange pattern: {exit_signal.date()} → {orange_end.date()}")
    
    print(f"\nPatterns detected: {len(all_green_patterns)} green, {len(all_orange_patterns)} orange")
    print(f"Total signals used: {len(used_signals)}")
    
    if all_green_patterns:
        print("\nGREEN PATTERNS:")
        for i, p in enumerate(all_green_patterns, 1):
            print(f"  {i}. Exit {p['exit_signal'].date()} → End {p['end'].date()}")
    
    if all_orange_patterns:
        print("\nORANGE PATTERNS:")
        for i, p in enumerate(all_orange_patterns, 1):
            print(f"  {i}. Exit {p['exit_signal'].date()} → End {p['end'].date()}")
    
    # Apply strategy: Choose which zones to use
    print(f"\n=== STRATEGY APPLICATION (Strategy: {'Orange' if allow_reentry_at_ma else 'Green'}) ===")
    
    zones = []
    
    if allow_reentry_at_ma:
        # Orange strategy: Use whichever completes FIRST (green or orange)
        # For each exit signal, check if we have both patterns
        all_exits = set()
        for p in all_green_patterns:
            all_exits.add(p['exit_signal'])
        for p in all_orange_patterns:
            all_exits.add(p['exit_signal'])
        
        for exit_signal in sorted(all_exits):
            # Find green pattern for this exit (if exists)
            green_pattern = None
            for p in all_green_patterns:
                if p['exit_signal'] == exit_signal:
                    green_pattern = p
                    break
            
            # Find orange pattern for this exit (if exists)
            orange_pattern = None
            for p in all_orange_patterns:
                if p['exit_signal'] == exit_signal:
                    orange_pattern = p
                    break
            
            # Decide which to use: whichever ends FIRST
            if green_pattern and orange_pattern:
                if green_pattern['end'] <= orange_pattern['end']:
                    # Green completes first (got N signals before MA crossing)
                    zones.append({
                        'exit_signal': green_pattern['exit_signal'],
                        'start': green_pattern['start'],
                        'end': green_pattern['end'],
                        'type': 'green',
                        'reentry_signals': green_pattern['signals']
                    })
                    print(f"  Exit {exit_signal.date()}: GREEN wins (ends {green_pattern['end'].date()} vs orange {orange_pattern['end'].date()})")
                else:
                    # Orange completes first (MA crossing before N signals)
                    zones.append({
                        'exit_signal': orange_pattern['exit_signal'],
                        'start': orange_pattern['start'],
                        'end': orange_pattern['end'],
                        'type': 'orange',
                        'reentry_signals': []
                    })
                    print(f"  Exit {exit_signal.date()}: ORANGE wins (ends {orange_pattern['end'].date()} vs green {green_pattern['end'].date()})")
            elif green_pattern:
                # Only green exists
                zones.append({
                    'exit_signal': green_pattern['exit_signal'],
                    'start': green_pattern['start'],
                    'end': green_pattern['end'],
                    'type': 'green',
                    'reentry_signals': green_pattern['signals']
                })
                print(f"  Exit {exit_signal.date()}: GREEN only")
            elif orange_pattern:
                # Only orange exists
                zones.append({
                    'exit_signal': orange_pattern['exit_signal'],
                    'start': orange_pattern['start'],
                    'end': orange_pattern['end'],
                    'type': 'orange',
                    'reentry_signals': []
                })
                print(f"  Exit {exit_signal.date()}: ORANGE only")
    else:
        # Green strategy: Only use green zones (must have N candlestick signals)
        for pattern in all_green_patterns:
            zones.append({
                'exit_signal': pattern['exit_signal'],
                'start': pattern['start'],
                'end': pattern['end'],
                'type': 'green',
                'reentry_signals': pattern['signals']
            })
    
    # Sort by start date
    zones.sort(key=lambda z: z['start'])
    
    # Separate for display
    green_zones = [z for z in zones if z['type'] == 'green']
    orange_zones = [z for z in zones if z['type'] == 'orange']
    
    print(f"\nFinal zones: {len(green_zones)} green, {len(orange_zones)} orange")
    
    if green_zones:
        print(f"\nGREEN ZONES:")
        for i, z in enumerate(green_zones[:10], 1):
            sigs = ', '.join([s.strftime('%Y-%m-%d') for s in z['reentry_signals']])
            print(f"{i}. {z['exit_signal'].strftime('%Y-%m-%d')} → {z['end'].strftime('%Y-%m-%d')} | Signals: {sigs}")
    
    if orange_zones:
        print(f"\nORANGE ZONES:")
        for i, z in enumerate(orange_zones[:10], 1):
            print(f"{i}. {z['exit_signal'].strftime('%Y-%m-%d')} → {z['end'].strftime('%Y-%m-%d')}")
    
    return zones

