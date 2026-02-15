"""
Formatting Module

This module handles formatting of chart labels for different time periods.
"""


def format_quarter_labels_two_levels(dates, show_all=True):
    """
    Format dates with quarters on top line and years on bottom line.
    Year is shown between Q4 and Q1 (at year boundary) consistent with daily view.
    
    Args:
        dates: DatetimeIndex of dates to format
        show_all: If True, show all quarters (Q1-Q4). If False, show only Q1 and Q3.
    
    Returns:
        tuple: (tick_vals, tick_text) where both lists have matching length
    
    Example output (show_all=True):
    Q3    Q4         Q1     Q2     Q3    Q4         Q1     Q2     Q3
                2021                           2022
    
    Example output (show_all=False):
    Q3                Q1            Q3                Q1            Q3
                2021                           2022
    """
    tick_vals = []
    tick_text = []
    prev_year = None
    
    for i, date in enumerate(dates):
        quarter = (date.month - 1) // 3 + 1
        year = date.year
        
        # Skip Q2 and Q4 if show_all is False
        if not show_all and quarter in (2, 4):
            continue
        
        is_first = prev_year is None
        is_q1 = quarter == 1
        year_changed = year != prev_year if prev_year is not None else False
        
        tick_vals.append(date)
        
        if is_first:
            # First label - show quarter with year below
            tick_text.append(f"Q{quarter}<br><b>{year}</b>")
        elif year_changed and is_q1:
            # Year changed at Q1 - show year below Q1
            tick_text.append(f"Q{quarter}<br><b>{year}</b>")
        else:
            # Regular quarter - no year
            tick_text.append(f"Q{quarter}<br> ")
        
        prev_year = year
    
    return tick_vals, tick_text


def format_monthly_labels_as_quarters(dates, show_all=True):
    """
    Format monthly dates showing quarters (Q1-Q4) and year between Q4 and Q1.
    Shows quarter label only in the MIDDLE month of each quarter (Feb, May, Aug, Nov).
    Year shown at January (between Q4 and Q1) consistent with daily view.
    
    Args:
        dates: DatetimeIndex of dates to format
        show_all: If True, show all middle months (Feb, May, Aug, Nov) plus Jan.
                  If False, show only Jan (year), Feb (Q1), and Aug (Q3).
    
    Returns:
        tuple: (tick_vals, tick_text) where both lists have matching length
    
    Example output (show_all=True):
         Q2                Q3                Q4              Q1         Q2
                                                  2021                     2022
    
    Example output (show_all=False):
                           Q3                                Q1         
                                                  2021                     2022
    """
    tick_vals = []
    tick_text = []
    prev_year = None
    
    # Middle months to display
    if show_all:
        middle_months = {2: 'Q1', 5: 'Q2', 8: 'Q3', 11: 'Q4'}
    else:
        middle_months = {2: 'Q1', 8: 'Q3'}  # Only Feb (Q1) and Aug (Q3)
    
    for i, date in enumerate(dates):
        quarter = (date.month - 1) // 3 + 1
        year = date.year
        month = date.month
        
        if month in middle_months:
            # This is a middle month - show the quarter
            quarter_label = middle_months[month]
            
            is_first = prev_year is None
            
            tick_vals.append(date)
            
            if is_first:
                # First label - show year
                tick_text.append(f"{quarter_label}<br><b>{year}</b>")
            else:
                tick_text.append(f"{quarter_label}<br> ")
        elif month == 1:
            # January - show year at year boundary (between Q4 and Q1)
            year_changed = year != prev_year if prev_year is not None else False
            
            tick_vals.append(date)
            
            if year_changed or prev_year is None:
                tick_text.append(f"<br><b>{year}</b>")
            else:
                tick_text.append(" <br> ")
        else:
            # Not a middle month and not January
            # Skip entirely if show_all is False, otherwise add empty label
            if show_all:
                tick_vals.append(date)
                tick_text.append(" <br> ")
            else:
                continue
        
        prev_year = year
    
    return tick_vals, tick_text


def format_daily_labels_simple(dates, max_labels=40):
    """
    Format daily dates with quarters on top line and years on bottom line.
    Simple and fast - shows Q labels at quarter starts.
    """
    labels = []
    prev_year = None
    prev_quarter = None
    
    for i, date in enumerate(dates):
        year = date.year
        quarter = (date.month - 1) // 3 + 1
        
        # Only show label if it's a new quarter or first/last point
        is_first = i == 0
        is_last = i == len(dates) - 1
        quarter_changed = quarter != prev_quarter if prev_quarter is not None else True
        
        if is_first or is_last or quarter_changed:
            # Show year if it's first label, last label, or year changed
            year_changed = year != prev_year if prev_year is not None else False
            is_q4 = quarter == 4
            
            if is_first or year_changed or (is_q4 and is_last):
                labels.append(f"Q{quarter}<br><b>{year}</b>")
            else:
                labels.append(f"Q{quarter}<br> ")
        else:
            # No label for this date
            labels.append(" <br> ")
        
        prev_year = year
        prev_quarter = quarter
    
    return labels