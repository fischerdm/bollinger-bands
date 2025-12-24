"""
Zone Identification Module

This module handles identification of trading zones (entry to re-entry).
"""

import pandas as pd
from bollinger_bands.indicators.crossing_detection import check_ma_conditions_for_period


def identify_entry_zones_with_conditions(data, display_data, ma_values, reentry_signals, price_crossing, combined_ma_condition, ma_condition_threshold=0.5, period='daily'):
    """
    Identify zones from entry to FIRST re-entry signal.
    
    Entry starts when:
    - Price is below MA
    - MA conditions are met (checked per day for daily, per period for monthly/quarterly)
    - We are at or after a price crossing point
    
    Entry ends when:
    - FIRST re-entry signal occurs (completed = True), OR
    - Price crosses back above MA (completed = False)
    """
    zones = []
    is_below = data['Close'] < ma_values
    
    # Get all crossing dates
    crossing_dates = display_data.index[price_crossing == 1].tolist()
    
    print(f"=== ZONE IDENTIFICATION ({period}) ===")
    print(f"Valid crossing dates: {len(crossing_dates)}")
    
    in_zone = False
    zone_start = None
    last_crossing_date = None
    
    for i in range(len(data)):
        current_date = data.index[i]
        
        # Update last_crossing_date if we passed a crossing
        for cross_date in crossing_dates:
            if cross_date <= current_date and (last_crossing_date is None or cross_date > last_crossing_date):
                last_crossing_date = cross_date
        
        # Check MA conditions based on period type
        if period in ['monthly', 'quarterly']:
            # For aggregated views, determine which period this date belongs to
            if period == 'quarterly':
                # Find the quarter end date for current_date
                quarter = (current_date.month - 1) // 3 + 1
                if quarter == 4:
                    period_end = pd.Timestamp(current_date.year, 12, 31)
                else:
                    period_end = pd.Timestamp(current_date.year, quarter * 3, 1) + pd.offsets.MonthEnd(0)
                period_start = pd.Timestamp(current_date.year, ((current_date.month - 1) // 3) * 3 + 1, 1)
            else:  # monthly
                period_start = pd.Timestamp(current_date.year, current_date.month, 1)
                period_end = period_start + pd.offsets.MonthEnd(0)
            
            # Check MA conditions for this period
            conditions_met, _, _, _ = check_ma_conditions_for_period(
                period_end, period_start, data, combined_ma_condition, 
                threshold=ma_condition_threshold
            )
        else:
            # For daily view, check MA conditions on this specific day
            conditions_met = combined_ma_condition.iloc[i]
        
        # Entry condition
        has_recent_crossing = last_crossing_date is not None
        
        if has_recent_crossing and is_below.iloc[i] and conditions_met and not in_zone:
            in_zone = True
            zone_start = current_date
            print(f"  Zone STARTED at {current_date.date()}")
        
        # Exit condition 1: Crossed back above MA (incomplete zone)
        if in_zone and not is_below.iloc[i]:
            if zone_start is not None:
                zones.append({'start': zone_start, 'end': data.index[i-1] if i > 0 else current_date, 'completed': False})
                print(f"  Zone ENDED (incomplete) at {data.index[i-1].date() if i > 0 else current_date.date()}")
            in_zone = False
            zone_start = None
            last_crossing_date = None
        
        # Exit condition 2: FIRST re-entry signal (completed zone)
        if in_zone and reentry_signals.iloc[i]:
            zones.append({'start': zone_start, 'end': current_date, 'completed': True})
            print(f"  Zone COMPLETED at {current_date.date()} (re-entry signal)")
            in_zone = False
            zone_start = None
            last_crossing_date = None
    
    # Handle case where we're still in a zone at the end
    if in_zone and zone_start is not None:
        zones.append({'start': zone_start, 'end': data.index[-1], 'completed': False})
        print(f"  Zone still OPEN at end: {data.index[-1].date()}")
    
    print(f"Total zones identified: {len(zones)}")
    return zones
