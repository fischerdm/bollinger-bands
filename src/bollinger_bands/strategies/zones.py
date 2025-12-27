"""
Zone Identification Module

This module handles identification of trading zones (entry to re-entry).
"""

import pandas as pd
from bollinger_bands.indicators.crossing_detection import check_ma_conditions_for_period


def identify_entry_zones_with_conditions(data, display_data, ma_values, reentry_signals, price_crossing, combined_ma_condition, ma_condition_threshold=0.5, period='daily', max_reentry_signals=1, reenter_after_orange=False):
    """
    Identify green and orange zones separately from exit signals.
    
    Green zones: From exit signal to Nth re-entry signal
    Orange zones: From exit signal to crossing back above MA (without N signals)
    
    Args:
        max_reentry_signals: Number of signals needed for green zone (default=1)
        reenter_after_orange: If True, crossing MA up after orange zone = re-enter market,
                              requires NEW exit signal for next zone.
                              If False, stay out of market, continue from same exit signal.
    """
    green_zones = []
    orange_zones = []
    is_below = data['Close'] < ma_values
    
    # Get all crossing dates (exit signals)
    crossing_dates = display_data.index[price_crossing == 1].tolist()
    
    print(f"=== ZONE IDENTIFICATION ({period}) ===")
    print(f"Valid exit signals: {len(crossing_dates)}")
    print(f"Re-entry signals for green zone: {max_reentry_signals}")
    print(f"Re-enter market after orange zone: {reenter_after_orange}")
    
    in_zone = False
    zone_start = None
    zone_exit_signal = None
    zone_reentry_signals = []
    processed_crossings = set()
    
    for i in range(len(data)):
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
            else:  # monthly
                period_start = pd.Timestamp(current_date.year, current_date.month, 1)
                period_end = period_start + pd.offsets.MonthEnd(0)
            
            conditions_met, _, _, _ = check_ma_conditions_for_period(
                period_end, period_start, data, combined_ma_condition, 
                threshold=ma_condition_threshold
            )
        else:
            conditions_met = combined_ma_condition.iloc[i]
        
        # Find new unprocessed exit signal
        current_crossing = None
        for cross_date in crossing_dates:
            if cross_date <= current_date and cross_date not in processed_crossings:
                current_crossing = cross_date
                break
        
        # Start new zone from exit signal
        if current_crossing is not None and is_below.iloc[i] and conditions_met and not in_zone:
            in_zone = True
            zone_start = current_crossing  # Start at exit signal, not current date!
            zone_exit_signal = current_crossing
            zone_reentry_signals = []
            processed_crossings.add(current_crossing)
            print(f"  Zone STARTED at {zone_start.date()} (exit signal: {current_crossing.date()})")
        
        # Collect re-entry signals
        if in_zone and reentry_signals.iloc[i]:
            zone_reentry_signals.append(current_date)
            print(f"    Re-entry signal {len(zone_reentry_signals)} at {current_date.date()}")
            
            # Green zone completes at Nth signal
            if len(zone_reentry_signals) >= max_reentry_signals:
                green_zones.append({
                    'exit_signal': zone_exit_signal,
                    'start': zone_start,
                    'reentry_signals': zone_reentry_signals.copy(),
                    'end': current_date,
                    'completed': True
                })
                print(f"  GREEN zone completed at {current_date.date()} ({len(zone_reentry_signals)} signals)")
                in_zone = False
                zone_start = None
                zone_exit_signal = None
                zone_reentry_signals = []
        
        # Zone ends: price crossed back above MA
        if in_zone and not is_below.iloc[i]:
            # Create orange zone (incomplete - not enough signals)
            orange_zones.append({
                'exit_signal': zone_exit_signal,
                'start': zone_start,
                'reentry_signals': zone_reentry_signals.copy(),
                'end': data.index[i-1] if i > 0 else current_date,
                'completed': False
            })
            print(f"  ORANGE zone at {data.index[i-1].date() if i > 0 else current_date.date()} ({len(zone_reentry_signals)} signals)")
            
            # Handle re-entry preference
            if reenter_after_orange:
                # Crossed back up = back in market, need NEW exit signal
                # Keep exit signal in processed_crossings
                print(f"    → Back in market, need new exit signal")
            else:
                # Stay out of market, can continue from same exit signal
                # Remove from processed so it can be reused
                if zone_exit_signal in processed_crossings:
                    processed_crossings.remove(zone_exit_signal)
                print(f"    → Stay out, can reuse exit signal {zone_exit_signal.date()}")
            
            in_zone = False
            zone_start = None
            zone_exit_signal = None
            zone_reentry_signals = []
    
    # Handle open zone at end
    if in_zone:
        if len(zone_reentry_signals) >= max_reentry_signals:
            green_zones.append({
                'exit_signal': zone_exit_signal,
                'start': zone_start,
                'reentry_signals': zone_reentry_signals.copy(),
                'end': data.index[-1],
                'completed': True
            })
            print(f"  GREEN zone still open at end ({len(zone_reentry_signals)} signals)")
        else:
            orange_zones.append({
                'exit_signal': zone_exit_signal,
                'start': zone_start,
                'reentry_signals': zone_reentry_signals.copy(),
                'end': data.index[-1],
                'completed': False
            })
            print(f"  ORANGE zone still open at end ({len(zone_reentry_signals)} signals)")
    
    print(f"\nTotal GREEN zones: {len(green_zones)}")
    print(f"Total ORANGE zones: {len(orange_zones)}")
    
    # Debug output
    print(f"\n=== GREEN ZONES (completed) ===")
    for i, zone in enumerate(green_zones[:5], 1):
        signals_str = ', '.join([s.strftime('%Y-%m-%d') for s in zone['reentry_signals']])
        print(f"Green {i}: Exit={zone['exit_signal'].strftime('%Y-%m-%d')}, "
              f"Start={zone['start'].strftime('%Y-%m-%d')}, "
              f"End={zone['end'].strftime('%Y-%m-%d')}, "
              f"Signals: {signals_str}")
    
    print(f"\n=== ORANGE ZONES (incomplete) ===")
    for i, zone in enumerate(orange_zones[:5], 1):
        signals_str = ', '.join([s.strftime('%Y-%m-%d') for s in zone['reentry_signals']]) if zone['reentry_signals'] else "none"
        print(f"Orange {i}: Exit={zone['exit_signal'].strftime('%Y-%m-%d')}, "
              f"Start={zone['start'].strftime('%Y-%m-%d')}, "
              f"End={zone['end'].strftime('%Y-%m-%d')}, "
              f"Signals: {signals_str}")
    
    # Combine for backward compatibility
    zones = green_zones + orange_zones
    zones.sort(key=lambda z: z['start'])
    
    return zones