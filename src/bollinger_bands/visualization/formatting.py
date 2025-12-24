"""
Formatting Module

This module handles formatting of chart labels for different time periods.
"""


def format_quarter_labels_two_levels(dates):
    """
    Format dates with quarters on top line and years on bottom line.
    Year is shown between Q4 and Q1 (at year boundary) consistent with daily view.
    
    Example output:
    Q3    Q4         Q1     Q2     Q3    Q4         Q1     Q2     Q3
                2021                           2022
    """
    labels = []
    prev_year = None
    
    for i, date in enumerate(dates):
        quarter = (date.month - 1) // 3 + 1
        year = date.year
        
        is_first = prev_year is None
        is_q1 = quarter == 1
        year_changed = year != prev_year if prev_year is not None else False
        
        if is_first:
            # First label - show quarter with year below
            labels.append(f"Q{quarter}<br><b>{year}</b>")
        elif year_changed and is_q1:
            # Year changed at Q1 - show year below Q1
            labels.append(f"Q{quarter}<br><b>{year}</b>")
        else:
            # Regular quarter - no year
            labels.append(f"Q{quarter}<br> ")
        
        prev_year = year
    
    return labels


def format_monthly_labels_as_quarters(dates):
    """
    Format monthly dates showing quarters (Q1-Q4) and year between Q4 and Q1.
    Shows quarter label only in the MIDDLE month of each quarter (Feb, May, Aug, Nov).
    Year shown at January (between Q4 and Q1) consistent with daily view.
    
    Example output:
         Q2                Q3                Q4              Q1         Q2
                                                  2021                     2022
    """
    labels = []
    prev_year = None
    
    for i, date in enumerate(dates):
        quarter = (date.month - 1) // 3 + 1
        year = date.year
        month = date.month
        
        # Middle months of each quarter: Feb(2), May(5), Aug(8), Nov(11)
        middle_months = {2: 'Q1', 5: 'Q2', 8: 'Q3', 11: 'Q4'}
        
        if month in middle_months:
            # This is a middle month - show the quarter
            quarter_label = middle_months[month]
            
            is_first = prev_year is None
            
            if is_first:
                # First label - show year
                labels.append(f"{quarter_label}<br><b>{year}</b>")
            else:
                labels.append(f"{quarter_label}<br> ")
        elif month == 1:
            # January - show year at year boundary (between Q4 and Q1)
            year_changed = year != prev_year if prev_year is not None else False
            if year_changed or prev_year is None:
                labels.append(f"<br><b>{year}</b>")
            else:
                labels.append(" <br> ")
        else:
            # Not a middle month and not January - no label
            labels.append(" <br> ")
        
        prev_year = year
    
    return labels


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
