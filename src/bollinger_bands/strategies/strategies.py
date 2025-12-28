"""
Trading Strategy State Machine

This module implements strategy logic that filters and combines
detected patterns based on market state.
"""

import pandas as pd


class TradingStateMachine:
    """
    State machine for managing trading zones based on market state.
    
    States:
    - IN_MARKET: Currently holding position
    - OUT_OF_MARKET: Not holding position, looking for entry
    
    Transitions:
    - OUT → IN: When entering market (start of trading)
    - IN → OUT: When exit signal triggered (price crosses below MA)
    - OUT → IN: When re-entry signal triggered (candlestick pattern or MA crossing)
    """
    
    def __init__(self, initial_state='IN_MARKET'):
        self.state = initial_state
        self.current_zone_start = None
        self.active_zones = []
    
    def process_exit_signal(self, exit_date):
        """
        Process an exit signal (price crossing below MA).
        
        Args:
            exit_date: Date of the exit signal
            
        Returns:
            bool: True if exit signal is valid (we're in market), False otherwise
        """
        if self.state == 'IN_MARKET':
            # Valid exit - we're in the market
            self.state = 'OUT_OF_MARKET'
            self.current_zone_start = exit_date
            print(f"  Exit signal at {exit_date.date()}: IN_MARKET → OUT_OF_MARKET")
            return True
        else:
            # Invalid exit - we're already out
            print(f"  Exit signal at {exit_date.date()}: IGNORED (already OUT_OF_MARKET)")
            return False
    
    def process_reentry_signal(self, reentry_date, signal_type='candlestick'):
        """
        Process a re-entry signal.
        
        Args:
            reentry_date: Date of the re-entry signal
            signal_type: Type of signal ('candlestick' or 'ma_crossing')
            
        Returns:
            dict or None: Completed zone if signal is valid, None otherwise
        """
        if self.state == 'OUT_OF_MARKET' and self.current_zone_start is not None:
            # Valid re-entry - we're out and have an active zone
            zone = {
                'start': self.current_zone_start,
                'end': reentry_date,
                'type': 'green' if signal_type == 'candlestick' else 'orange',
                'completed': True,
                'exit_signal': self.current_zone_start,
                'reentry_signals': [reentry_date]
            }
            
            self.state = 'IN_MARKET'
            self.current_zone_start = None
            print(f"  Re-entry signal at {reentry_date.date()}: OUT_OF_MARKET → IN_MARKET (zone completed)")
            
            return zone
        else:
            # Invalid re-entry - we're already in market or no active zone
            print(f"  Re-entry signal at {reentry_date.date()}: IGNORED (state={self.state})")
            return None
    
    def finalize(self, last_date):
        """
        Finalize any incomplete zones at the end of data.
        
        Args:
            last_date: Last date in the dataset
            
        Returns:
            dict or None: Incomplete zone if one exists, None otherwise
        """
        if self.state == 'OUT_OF_MARKET' and self.current_zone_start is not None:
            zone = {
                'start': self.current_zone_start,
                'end': last_date,
                'type': 'orange',
                'completed': False,
                'exit_signal': self.current_zone_start,
                'reentry_signals': []
            }
            print(f"  Incomplete zone: {self.current_zone_start.date()} → {last_date.date()}")
            return zone
        return None


def apply_green_strategy(all_green_patterns, all_orange_patterns, data):
    """
    Apply green-only strategy (candlestick signals only).
    
    Strategy rules:
    1. Start IN_MARKET
    2. Exit signals only valid when IN_MARKET
    3. Re-entry only at candlestick signals
    4. Process chronologically
    
    Args:
        all_green_patterns: List of detected green patterns (exit → candlestick signal)
        all_orange_patterns: List of detected orange patterns (exit → MA crossing)
        data: Full daily price data
        
    Returns:
        list: Filtered zones following strategy rules
    """
    print(f"\n=== APPLYING GREEN STRATEGY ===")
    print(f"Input: {len(all_green_patterns)} green patterns, {len(all_orange_patterns)} orange patterns")
    
    # Initialize state machine (start IN_MARKET)
    state_machine = TradingStateMachine(initial_state='IN_MARKET')
    
    # Collect all events with their dates
    events = []
    
    # Add all exit signals
    for pattern in all_green_patterns:
        events.append({
            'date': pattern['exit_signal'],
            'type': 'exit',
            'pattern': pattern
        })
    
    for pattern in all_orange_patterns:
        events.append({
            'date': pattern['exit_signal'],
            'type': 'exit',
            'pattern': pattern
        })
    
    # Add all candlestick signals (re-entry for green patterns)
    for pattern in all_green_patterns:
        for signal_date in pattern['signals']:
            events.append({
                'date': signal_date,
                'type': 'reentry_candlestick',
                'pattern': pattern
            })
    
    # Sort events chronologically
    events.sort(key=lambda e: e['date'])
    
    # Remove duplicate exit signals at same date
    unique_events = []
    seen_exits = set()
    for event in events:
        if event['type'] == 'exit':
            if event['date'] not in seen_exits:
                unique_events.append(event)
                seen_exits.add(event['date'])
        else:
            unique_events.append(event)
    
    print(f"\nProcessing {len(unique_events)} chronological events:")
    
    # Process events chronologically
    valid_zones = []
    
    for event in unique_events:
        if event['type'] == 'exit':
            # Try to process exit signal
            is_valid = state_machine.process_exit_signal(event['date'])
            
        elif event['type'] == 'reentry_candlestick':
            # Try to process re-entry signal
            zone = state_machine.process_reentry_signal(event['date'], signal_type='candlestick')
            if zone:
                valid_zones.append(zone)
    
    # Finalize any incomplete zone
    incomplete_zone = state_machine.finalize(data.index[-1])
    if incomplete_zone:
        valid_zones.append(incomplete_zone)
    
    print(f"\nStrategy output: {len(valid_zones)} valid zones")
    
    return valid_zones


def apply_orange_strategy(all_green_patterns, all_orange_patterns, data):
    """
    Apply orange strategy (MA crossings + candlestick signals).
    
    Strategy rules:
    1. Start IN_MARKET
    2. Exit signals only valid when IN_MARKET
    3. Re-entry at EITHER candlestick signal OR MA crossing (whichever comes first)
    4. Process chronologically
    
    Args:
        all_green_patterns: List of detected green patterns (exit → candlestick signal)
        all_orange_patterns: List of detected orange patterns (exit → MA crossing)
        data: Full daily price data
        
    Returns:
        list: Filtered zones following strategy rules
    """
    print(f"\n=== APPLYING ORANGE STRATEGY ===")
    print(f"Input: {len(all_green_patterns)} green patterns, {len(all_orange_patterns)} orange patterns")
    
    # Initialize state machine (start IN_MARKET)
    state_machine = TradingStateMachine(initial_state='IN_MARKET')
    
    # Collect all events with their dates
    events = []
    
    # Add all exit signals
    for pattern in all_green_patterns:
        events.append({
            'date': pattern['exit_signal'],
            'type': 'exit',
            'pattern': pattern
        })
    
    for pattern in all_orange_patterns:
        events.append({
            'date': pattern['exit_signal'],
            'type': 'exit',
            'pattern': pattern
        })
    
    # Add all candlestick signals (re-entry for green patterns)
    for pattern in all_green_patterns:
        for signal_date in pattern['signals']:
            events.append({
                'date': signal_date,
                'type': 'reentry_candlestick',
                'pattern': pattern
            })
    
    # Add all MA crossings (re-entry for orange patterns)
    for pattern in all_orange_patterns:
        events.append({
            'date': pattern['end'],
            'type': 'reentry_ma_crossing',
            'pattern': pattern
        })
    
    # Sort events chronologically
    events.sort(key=lambda e: e['date'])
    
    # Remove duplicate exit signals and re-entry signals at same date
    unique_events = []
    seen_exits = set()
    seen_reentries = set()
    
    for event in events:
        if event['type'] == 'exit':
            if event['date'] not in seen_exits:
                unique_events.append(event)
                seen_exits.add(event['date'])
        elif event['type'] in ['reentry_candlestick', 'reentry_ma_crossing']:
            if event['date'] not in seen_reentries:
                unique_events.append(event)
                seen_reentries.add(event['date'])
        else:
            unique_events.append(event)
    
    print(f"\nProcessing {len(unique_events)} chronological events:")
    
    # Process events chronologically
    valid_zones = []
    
    for event in unique_events:
        if event['type'] == 'exit':
            # Try to process exit signal
            is_valid = state_machine.process_exit_signal(event['date'])
            
        elif event['type'] == 'reentry_candlestick':
            # Try to process re-entry signal (candlestick)
            zone = state_machine.process_reentry_signal(event['date'], signal_type='candlestick')
            if zone:
                valid_zones.append(zone)
                
        elif event['type'] == 'reentry_ma_crossing':
            # Try to process re-entry signal (MA crossing)
            zone = state_machine.process_reentry_signal(event['date'], signal_type='ma_crossing')
            if zone:
                valid_zones.append(zone)
    
    # Finalize any incomplete zone
    incomplete_zone = state_machine.finalize(data.index[-1])
    if incomplete_zone:
        valid_zones.append(incomplete_zone)
    
    print(f"\nStrategy output: {len(valid_zones)} valid zones")
    
    return valid_zones
