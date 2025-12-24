import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
from bollinger_bands.data.fetcher import DataFetcher
from bollinger_bands.indicators.moving_average import MovingAverage
from bollinger_bands.indicators.bollinger_bands import BollingerBands
from bollinger_bands.indicators.band_width import BandWidth
from bollinger_bands.visualization.plotter import Plotter
import datetime
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objs as go
import numpy as np


def detect_bullish_engulfing(data):
    """Detect bullish engulfing candlestick pattern"""
    signals = pd.Series(False, index=data.index)
    
    for i in range(1, len(data)):
        prev_open = data['Open'].iloc[i-1]
        prev_close = data['Close'].iloc[i-1]
        curr_open = data['Open'].iloc[i]
        curr_close = data['Close'].iloc[i]
        
        prev_bearish = prev_close < prev_open
        curr_bullish = curr_close > curr_open
        engulfs = curr_open <= prev_close and curr_close >= prev_open
        
        if prev_bearish and curr_bullish and engulfs:
            signals.iloc[i] = True
    
    return signals


def detect_hammer(data):
    """Detect hammer and inverted hammer patterns"""
    signals = pd.Series(False, index=data.index)
    
    for i in range(len(data)):
        open_price = data['Open'].iloc[i]
        close_price = data['Close'].iloc[i]
        high_price = data['High'].iloc[i]
        low_price = data['Low'].iloc[i]
        
        body = abs(close_price - open_price)
        total_range = high_price - low_price
        
        if total_range == 0:
            continue
            
        lower_shadow = min(open_price, close_price) - low_price
        upper_shadow = high_price - max(open_price, close_price)
        
        is_hammer = (lower_shadow > 2 * body) and (upper_shadow < body)
        is_inverted = (upper_shadow > 2 * body) and (lower_shadow < body)
        
        if is_hammer or is_inverted:
            signals.iloc[i] = True
    
    return signals


def detect_morning_star(data):
    """Detect morning star pattern (3-candle reversal)"""
    signals = pd.Series(False, index=data.index)
    
    for i in range(2, len(data)):
        first_open = data['Open'].iloc[i-2]
        first_close = data['Close'].iloc[i-2]
        first_bearish = first_close < first_open
        
        second_open = data['Open'].iloc[i-1]
        second_close = data['Close'].iloc[i-1]
        second_body = abs(second_close - second_open)
        first_body = abs(first_close - first_open)
        second_small = second_body < 0.3 * first_body
        
        third_open = data['Open'].iloc[i]
        third_close = data['Close'].iloc[i]
        third_bullish = third_close > third_open
        
        recovers = third_close > (first_open + first_close) / 2
        
        if first_bearish and second_small and third_bullish and recovers:
            signals.iloc[i] = True
    
    return signals


def detect_price_crossing_down_daily(data, ma_values, smoothing_window=5):
    """
    Detect when price crosses below MA for DAILY data with smoothing.
    Uses a moving average of the price to reduce noise.
    """
    crossing_signal = pd.Series(0, index=data.index, dtype=float)
    
    # Clean data - remove NaN values
    valid_mask = data['Close'].notna() & ma_values.notna()
    clean_data = data[valid_mask].copy()
    clean_ma = ma_values[valid_mask]
    
    if len(clean_data) < smoothing_window * 2:
        return crossing_signal
    
    # Apply smoothing to price to reduce noise
    smoothed_price = clean_data['Close'].rolling(window=smoothing_window, min_periods=1).mean()
    
    # Calculate if smoothed price is below MA
    is_below = smoothed_price < clean_ma
    is_above = smoothed_price >= clean_ma
    
    # Find transitions from above to below
    prev_above = is_above.shift(1).fillna(False)
    transitions = is_below & prev_above
    
    for i in range(len(clean_data)):
        if not transitions.iloc[i]:
            continue
            
        # Check if price was above MA for sufficient time before crossing
        lookback_start = max(0, i - smoothing_window)
        was_above = is_above.iloc[lookback_start:i]
        
        if was_above.sum() < smoothing_window * 0.6:  # At least 60% of days above
            continue
        
        # Check if price stays below MA for sufficient time after crossing
        lookahead_end = min(len(clean_data), i + smoothing_window)
        stays_below = is_below.iloc[i:lookahead_end]
        
        if stays_below.sum() >= smoothing_window * 0.6:  # At least 60% of days below
            crossing_signal.loc[clean_data.index[i]] = 1
    
    return crossing_signal


def detect_price_crossing_down_period(data, ma_values):
    """
    Detect when price crosses below MA for MONTHLY/QUARTERLY data.
    Simple and clean: Open >= MA and Close < MA means crossing occurred during the period.
    """
    crossing_signal = pd.Series(0, index=data.index, dtype=float)
    
    # Clean data - remove NaN values
    valid_mask = data['Open'].notna() & data['Close'].notna() & ma_values.notna()
    clean_data = data[valid_mask].copy()
    clean_ma = ma_values[valid_mask]
    
    if len(clean_data) < 2:
        return crossing_signal
    
    for i in range(len(clean_data)):
        period_open = clean_data['Open'].iloc[i]
        period_close = clean_data['Close'].iloc[i]
        period_ma = clean_ma.iloc[i]
        period_date = clean_data.index[i]
        
        # Check if price crossed down during this period
        # Open was above or at MA, Close is below MA
        if period_open >= period_ma and period_close < period_ma:
            crossing_signal.loc[period_date] = 1
            print(f"  Price crossing detected at {period_date.date()}: Open={period_open:.2f} >= MA={period_ma:.2f}, Close={period_close:.2f} < MA")
    
    return crossing_signal


def check_ma_conditions_for_period(period_end_date, period_start_date, daily_data, ma_condition, threshold=0.5):
    """
    Check if MA conditions (flat long + decreasing short) are met for a given period.
    
    Args:
        period_end_date: The end date of the period (monthly/quarterly candle close date)
        period_start_date: The start date of the period (monthly/quarterly candle open date)
        daily_data: Daily OHLC data
        ma_condition: Boolean series of daily MA conditions
        threshold: Minimum % of days that must have conditions met (0.5 = 50%)
    
    Returns:
        tuple: (bool, float, int, int) - (conditions_met, actual_percentage, days_with_condition, total_days)
    """
    # Find daily data between period start and end
    mask = (daily_data.index >= period_start_date) & (daily_data.index <= period_end_date)
    
    if mask.sum() == 0:
        return False, 0.0, 0, 0
    
    # Check what % of trading days had MA conditions met
    days_in_period = mask.sum()
    days_with_conditions = ma_condition[mask].sum()
    condition_pct = days_with_conditions / days_in_period
    
    return condition_pct >= threshold, condition_pct, days_with_conditions, days_in_period


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


def format_quarter_labels_two_levels(dates):
    """
    Format dates with quarters on top line and years on bottom line.
    Year is shown at Q4 to indicate end of year.
    
    Example output:
    Q1     Q2     Q3    Q4        Q1     Q2     Q3    Q4
                           2021                           2022
    """
    labels = []
    prev_year = None
    
    for i, date in enumerate(dates):
        quarter = (date.month - 1) // 3 + 1
        year = date.year
        
        # Show year only at Q4 (end of year) to avoid overlap with next year's Q1
        # Exception: if it's the first label and not Q4, show year
        is_first = prev_year is None
        is_q4 = quarter == 4
        year_changed = year != prev_year if prev_year is not None else False
        
        if is_first and not is_q4:
            # First label but not Q4 - show year to orient user
            labels.append(f"Q{quarter}<br><b>{year}</b>")
        elif is_q4:
            # Q4 - always show year as it marks end of year
            labels.append(f"Q{quarter}<br><b>{year}</b>")
        else:
            # Regular quarter - no year
            labels.append(f"Q{quarter}<br> ")  # Space keeps alignment
        
        prev_year = year
    
    return labels


def format_monthly_labels_as_quarters(dates):
    """
    Format monthly dates showing quarters (Q1-Q4) and year at Q4 or year change.
    Shows quarter label only in the MIDDLE month of each quarter (Feb, May, Aug, Nov).
    
    Example output:
         Q1                Q2                Q3                Q4
    2021                                                        2021
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
            
            # Show year at November (Q4) or first label
            is_first = prev_year is None
            is_november = month == 11
            
            if is_first:
                labels.append(f"{quarter_label}<br><b>{year}</b>")
            elif is_november:
                labels.append(f"{quarter_label}<br><b>{year}</b>")
            else:
                labels.append(f"{quarter_label}<br> ")
        else:
            # Not a middle month - no label
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


# Tickers configuration
tickers = ['EEM', 'URTH', 'GDX', 'GDXJ', 'LTAM.L', 'IBB', 'XBI', 'IOGP.L', 'WENS.AS']
tickers_dict = {
    'EEM': 'Emerging Markets (EEM)',
    'URTH': 'Global Markets (URTH)',
    'GDX': 'Basic Materials (GDX)',
    'GDXJ': 'Basic Materials (GDXJ)',
    'LTAM.L': 'Latin America (LTAM.L)',
    'IBB': 'Healthcare (IBB)',
    'XBI': 'Healthcare (XBI)',
    'IOGP.L': 'iShares Oil & Gas Exploration & Production UCITS ETF USD (Acc)',
    'WENS.AS': 'iShares MSCI World Energy Sector UCITS ETF USD Inc'
}

ticker_data = {}
fetcher = DataFetcher()
start_date = '2015-01-01'
now = datetime.datetime.now()
end_date = now.strftime('%Y-%m-%d')

print("Fetching data...")
for ticker in tickers:
    print(ticker)
    data = fetcher.fetch_ohlc_data(ticker, start_date, end_date)
    data.attrs['ticker'] = ticker
    ticker_data[ticker] = data
print("Data loaded!")

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])
load_figure_template("LUX")

app.layout = dbc.Container([
    html.H1("Stock Chart with Bollinger Bands & Trading Signals", style={'textAlign': 'center'}),
    html.H2(id='ticker-name', style={'textAlign': 'center'}),
    
    dbc.Row([
        dbc.Col([
            html.Label("Select Ticker:"),
            dcc.Dropdown(id='ticker-dropdown', options=[{'label': t, 'value': t} for t in tickers], value='EEM')
        ], width=3),
        dbc.Col([
            html.Label("Time Period Price Chart:"),
            dcc.RadioItems(id='period-selector', options=[
                {'label': ' Daily', 'value': 'daily'},
                {'label': ' Monthly', 'value': 'monthly'},
                {'label': ' Quarterly', 'value': 'quarterly'}
            ], value='monthly', inline=True, style={'marginTop': '5px'})
        ], width=3),
        dbc.Col([
            html.Label("Time Period MA & Bollinger Bands:"),
            dcc.RadioItems(id='ma-period-selector', options=[
                {'label': ' 40M/20M', 'value': '40m20m'},
                {'label': ' 20M/10M', 'value': '20m10m'}
            ], value='40m20m', inline=True, style={'marginTop': '5px'})
        ], width=3),
        dbc.Col([
            html.Label("Scale:"),
            dcc.RadioItems(id='scale-selector', options=[
                {'label': ' Linear', 'value': 'linear'},
                {'label': ' Log', 'value': 'log'}
            ], value='linear', inline=True, style={'marginTop': '5px'})
        ], width=3),
    ], className="mb-3"),
    
    dbc.Row([
        dbc.Col([
            html.Label("Flat Long MA Threshold (%):"),
            dcc.Input(id='flat-threshold-840', type='number', value=0.025, step=0.005, style={'width': '100%'}),
            html.Small("Values below this threshold", style={'color': 'gray'})
        ], width=3),
        dbc.Col([
            html.Label("Decreasing Short MA Threshold (%):"),
            dcc.Input(id='flat-threshold-420', type='number', value=0, step=0.005, style={'width': '100%'}),
            html.Small("Negative values for decreasing", style={'color': 'gray'})
        ], width=3),
        dbc.Col([
            html.Label("BB Distance for Re-Entry (%):"),
            dcc.Input(id='bb-distance-threshold', type='number', value=10, min=0, step=5, style={'width': '100%'}),
            html.Small("Max distance from lower BB", style={'color': 'gray'})
        ], width=3),
    ], className="mb-3"),
    
    dbc.Row([
        dbc.Col([
            html.Label("Smoothing Window (Daily Exit):"),
            dcc.Input(id='smoothing-window', type='number', value=5, min=1, max=20, step=1, style={'width': '100%'}),
            html.Small("Days for price smoothing", style={'color': 'gray'})
        ], width=3),
        dbc.Col([
            html.Label("MA Condition Lookahead (Daily):"),
            dcc.Input(id='daily-lookahead', type='number', value=10, min=0, max=30, step=1, style={'width': '100%'}),
            html.Small("Days to check MA conditions after crossing", style={'color': 'gray'})
        ], width=3),
        dbc.Col([
            html.Label("MA Condition Threshold (All Views):"),
            dcc.Input(id='ma-condition-threshold', type='number', value=0.5, min=0, max=1, step=0.05, style={'width': '100%'}),
            html.Small("Min % with MA conditions (0=off, 0.5=50%)", style={'color': 'gray'})
        ], width=3),
    ], className="mb-3"),
    
    dbc.Row([
        dbc.Col([
            html.Label("Re-Entry Signals:"),
            dcc.Checklist(id='signal-checklist', options=[
                {'label': ' Bullish Engulfing', 'value': 'engulfing'},
                {'label': ' Hammer/Inverted Hammer', 'value': 'hammer'},
                {'label': ' Morning Star', 'value': 'morning_star'}
            ], value=['engulfing', 'hammer', 'morning_star'], inline=True, style={'marginTop': '5px'})
        ], width=6),
    ], className="mb-3"),
    
    dbc.Row([
        dbc.Col([
            html.Label("Display Zones:"),
            dcc.Checklist(id='zone-display-checklist', options=[
                {'label': ' Below MA (Red)', 'value': 'below_ma'},
                {'label': ' Entry-to-Reentry Complete (Green)', 'value': 'complete_zone'},
                {'label': ' Entry-to-Reentry Incomplete (Orange)', 'value': 'incomplete_zone'}
            ], value=['complete_zone'], inline=True, style={'marginTop': '5px'})
        ], width=12),
    ], className="mb-4"),

    dcc.Graph(id='stock-chart', style={'height': '120vh'})
], fluid=True, className="p-4")


@app.callback(
    [Output('stock-chart', 'figure'), Output('ticker-name', 'children')],
    [Input('ticker-dropdown', 'value'), Input('period-selector', 'value'),
     Input('ma-period-selector', 'value'), Input('scale-selector', 'value'),
     Input('flat-threshold-840', 'value'), Input('flat-threshold-420', 'value'),
     Input('signal-checklist', 'value'), Input('bb-distance-threshold', 'value'),
     Input('zone-display-checklist', 'value'), Input('smoothing-window', 'value'),
     Input('ma-condition-threshold', 'value'), Input('daily-lookahead', 'value')]
)
def update_chart(selected_ticker, period, ma_period, scale, flat_threshold_840, flat_threshold_420, enabled_signals, bb_distance_threshold, display_zones, smoothing_window, ma_condition_threshold, daily_lookahead):
    try:
        data = ticker_data[selected_ticker]
        if 'ticker' not in data.attrs:
            data.attrs['ticker'] = selected_ticker
        
        # CRITICAL: Clean the data at the very beginning
        data = data.dropna()
        data = data[data.index.notnull()]
        data = data[data.index >= '2000-01-01']
        
        print(f"=== RAW DATA AFTER CLEANING ===")
        print(f"Data shape: {data.shape}")
        print(f"Data range: {data.index[0]} to {data.index[-1]}")
        print(f"Data min year: {data.index.min().year}")
        print(f"Data max year: {data.index.max().year}")
        
        # Defaults - Fix: Don't override 0 values
        if flat_threshold_840 is None:
            flat_threshold_840 = 0.025
        if flat_threshold_420 is None:
            flat_threshold_420 = 0
        enabled_signals = enabled_signals or []
        bb_distance_threshold = bb_distance_threshold or 10
        display_zones = display_zones or ['complete_zone']
        scale = scale or 'linear'
        ma_period = ma_period or '40m20m'
        smoothing_window = smoothing_window or 5
        ma_condition_threshold = ma_condition_threshold if ma_condition_threshold is not None else 0.5
        daily_lookahead = daily_lookahead if daily_lookahead is not None else 10
        
        print(f"Thresholds: flat_long={flat_threshold_840}, decreasing_short={flat_threshold_420}, smoothing_window={smoothing_window}, ma_condition_threshold={ma_condition_threshold}, daily_lookahead={daily_lookahead}")
        
        # MA/BB windows
        if ma_period == '20m10m':
            long_window, short_window, period_label = 420, 210, "20M/10M"
        else:
            long_window, short_window, period_label = 840, 420, "40M/20M"
        
        # Resample price data
        if period == 'quarterly':
            display_data = data.resample('QE').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
            display_label = "Quarterly"
            # Store original period end dates before offsetting
            display_data['original_date'] = display_data.index
            # Offset the index to center candles in the middle of each quarter (~45 days back)
            display_data.index = display_data.index - pd.Timedelta(days=45)
        elif period == 'monthly':
            display_data = data.resample('ME').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
            display_label = "Monthly"
            # Store original period end dates before offsetting
            display_data['original_date'] = display_data.index
            # Offset the index to center candles in the middle of each month (~15 days back)
            display_data.index = display_data.index - pd.Timedelta(days=15)
        else:
            display_data = data[['Open','High','Low','Close']].copy()
            display_label = "Daily"
        
        # CRITICAL FIX 1: Remove any rows with NaN or invalid dates
        display_data = display_data.dropna()
        display_data = display_data[display_data.index.notnull()]
        
        # CRITICAL FIX 2: Ensure display_data doesn't extend beyond actual data
        display_data = display_data[display_data.index <= data.index[-1]]
        
        # CRITICAL FIX 3: Remove any data before 2000 (shouldn't exist but just in case)
        display_data = display_data[display_data.index >= '2000-01-01']
        
        print(f"=== DATA CLEANING ===")
        print(f"Original data range: {data.index[0]} to {data.index[-1]}")
        print(f"Display data range after cleaning: {display_data.index[0]} to {display_data.index[-1]}")
        print(f"Display data shape: {display_data.shape}")
        print(f"Display data has NaN: {display_data.isnull().any().any()}")
        print(f"Display data min date year: {display_data.index.min().year}")
        print(f"Display data max date year: {display_data.index.max().year}")
        
        # Calculate indicators on daily data
        ma_long = MovingAverage(window=long_window)
        ma_long_values = ma_long.calculate(data)
        ma_long_change = ma_long.calculate_change(data)
        
        ma_short = MovingAverage(window=short_window)
        ma_short_values = ma_short.calculate(data)
        ma_short_change = ma_short.calculate_change(data)
        
        bb_long = BollingerBands(window=long_window, num_std=2)
        bb_long_values = bb_long.calculate(data)
        
        bb_short = BollingerBands(window=short_window, num_std=2)
        bb_short_values = bb_short.calculate(data)
        
        bw = BandWidth(window=long_window)
        bandwidth_long = bw.calculate(bb_long_values)
        
        # Filter to display range
        start, end = display_data.index[0], display_data.index[-1]
        
        print(f"=== MA/BB FILTERING ===")
        print(f"Display data range: {start} to {end}")
        print(f"MA long values range: {ma_long_values.index[0]} to {ma_long_values.index[-1]}")
        print(f"BB long upper range: {bb_long_values['upper'].index[0]} to {bb_long_values['upper'].index[-1]}")
        
        ma_long_filt = ma_long_values[(ma_long_values.index >= start) & (ma_long_values.index <= end)]
        
        print(f"MA long filtered count: {len(ma_long_filt)} (from {len(ma_long_values)})")
        if len(ma_long_filt) > 0:
            print(f"MA long filtered range: {ma_long_filt.index[0]} to {ma_long_filt.index[-1]}")
            print(f"MA long filtered min year: {ma_long_filt.index.min().year}")
            print(f"MA long filtered max year: {ma_long_filt.index.max().year}")
        
        bb_long_filt = {
            'upper': bb_long_values['upper'][(bb_long_values['upper'].index >= start) & (bb_long_values['upper'].index <= end)],
            'middle': bb_long_values['middle'][(bb_long_values['middle'].index >= start) & (bb_long_values['middle'].index <= end)],
            'lower': bb_long_values['lower'][(bb_long_values['lower'].index >= start) & (bb_long_values['lower'].index <= end)]
        }
        
        bb_short_filt = {
            'upper': bb_short_values['upper'][(bb_short_values['upper'].index >= start) & (bb_short_values['upper'].index <= end)],
            'middle': bb_short_values['middle'][(bb_short_values['middle'].index >= start) & (bb_short_values['middle'].index <= end)],
            'lower': bb_short_values['lower'][(bb_short_values['lower'].index >= start) & (bb_short_values['lower'].index <= end)]
        }
        
        # Signals
        bullish_engulfing = detect_bullish_engulfing(data) if 'engulfing' in enabled_signals else pd.Series(False, index=data.index)
        hammer = detect_hammer(data) if 'hammer' in enabled_signals else pd.Series(False, index=data.index)
        morning_star = detect_morning_star(data) if 'morning_star' in enabled_signals else pd.Series(False, index=data.index)
        
        any_reentry_signal = bullish_engulfing | hammer | morning_star
        is_below_ma = data['Close'] < ma_long_values
        bb_width = bb_long_values['upper'] - bb_long_values['lower']
        distance_pct = ((data['Close'] - bb_long_values['lower']) / bb_width) * 100
        near_lower_bb = distance_pct <= bb_distance_threshold
        reentry_signals = any_reentry_signal & is_below_ma & near_lower_bb
        
        # Calculate MA conditions FIRST (needed for crossing detection)
        flat_long = ma_long_change < flat_threshold_840
        decreasing_short = ma_short_change < flat_threshold_420
        combined_ma_condition = flat_long & decreasing_short
        
        print(f"Days with flat long MA: {flat_long.sum()}")
        print(f"Days with decreasing short MA: {decreasing_short.sum()}")
        print(f"Days with both conditions: {combined_ma_condition.sum()}")
        
        # Exit conditions - IMPROVED CROSSING DETECTION
        # For monthly/quarterly, we need to compare against the daily MA at the period dates
        # NOT calculate a new MA on the aggregated data (which would have too few points)
        
        print(f"=== EXIT SIGNAL DETECTION ({period} view) ===")
        print(f"Display data shape: {display_data.shape}")
        
        # Get MA values at the display_data dates from the daily MA
        # Use original_date if available (for offset monthly/quarterly), otherwise use index
        if period in ['monthly', 'quarterly'] and 'original_date' in display_data.columns:
            period_end_dates = display_data['original_date']
        else:
            period_end_dates = display_data.index
            
        ma_at_period_dates = ma_long_values.reindex(period_end_dates, method='nearest')
        ma_at_period_dates.index = display_data.index  # Use offset index for plotting
        
        print(f"MA values at period dates: {len(ma_at_period_dates)} values")
        print(f"MA values NaN count: {ma_at_period_dates.isna().sum()}")
        
        # Detect price crossings (simple Open/Close check)
        if period == 'daily':
            price_crossing = detect_price_crossing_down_daily(display_data, ma_long_values, smoothing_window=smoothing_window)
            
            # Apply MA condition threshold if lookahead > 0
            if daily_lookahead > 0 and price_crossing.sum() > 0:
                crossing_dates = display_data.index[price_crossing == 1]
                valid_crossings = pd.Series(0, index=display_data.index, dtype=float)
                
                print(f"Checking MA conditions for {len(crossing_dates)} daily crossings (lookahead={daily_lookahead} days, threshold={ma_condition_threshold:.0%}):")
                for cross_date in crossing_dates:
                    # Check MA conditions from crossing date forward for lookahead days
                    lookahead_end = cross_date + pd.Timedelta(days=daily_lookahead)
                    
                    conditions_met, pct, days_met, total_days = check_ma_conditions_for_period(
                        lookahead_end, cross_date, data, combined_ma_condition, 
                        threshold=ma_condition_threshold
                    )
                    
                    if total_days > 0:
                        print(f"  {cross_date.date()} (checked {cross_date.date()} to {lookahead_end.date()}): MA conditions {days_met}/{total_days} days ({pct:.1%}) - {'✓ VALID' if conditions_met else '✗ REJECTED'}")
                        if conditions_met:
                            valid_crossings.loc[cross_date] = 1
                    else:
                        # Not enough data ahead, accept the crossing
                        valid_crossings.loc[cross_date] = 1
                
                price_crossing = valid_crossings
                print(f"Valid exit signals after MA condition check: {price_crossing.sum()}")
        else:
            price_crossing = detect_price_crossing_down_period(display_data, ma_at_period_dates)
        
        print(f"Total price crossings detected: {price_crossing.sum()}")
        
        # For monthly/quarterly: filter crossings by MA conditions threshold
        if period in ['monthly', 'quarterly'] and price_crossing.sum() > 0:
            crossing_dates = display_data.index[price_crossing == 1]
            valid_crossings = pd.Series(0, index=display_data.index, dtype=float)
            
            print(f"Checking MA conditions for {len(crossing_dates)} crossings (threshold={ma_condition_threshold:.0%}):")
            for cross_date in crossing_dates:
                # Get the original (non-offset) period end date
                if 'original_date' in display_data.columns:
                    original_cross_date = display_data.loc[cross_date, 'original_date']
                else:
                    original_cross_date = cross_date
                
                # Get the period start date using the original date
                if period == 'quarterly':
                    period_start = pd.Timestamp(original_cross_date.year, ((original_cross_date.month - 1) // 3) * 3 + 1, 1)
                else:  # monthly
                    period_start = pd.Timestamp(original_cross_date.year, original_cross_date.month, 1)
                
                # Find the actual crossing date in daily data (when price crossed below MA)
                # Look for the day within the period where crossing occurred
                period_mask = (data.index >= period_start) & (data.index <= original_cross_date)
                period_data = data[period_mask]
                
                # Find the day when price actually crossed below MA
                is_below = period_data['Close'] < ma_long_values[period_mask]
                is_above = period_data['Close'] >= ma_long_values[period_mask]
                
                # Find transition from above to below
                crossing_day = None
                for i in range(1, len(is_below)):
                    if is_above.iloc[i-1] and is_below.iloc[i]:
                        crossing_day = period_data.index[i]
                        break
                
                # If we found the crossing day, check MA conditions from that day forward
                if crossing_day is not None:
                    # Check MA conditions from crossing day to end of period
                    conditions_met, pct, days_met, total_days = check_ma_conditions_for_period(
                        original_cross_date, crossing_day, data, combined_ma_condition, 
                        threshold=ma_condition_threshold
                    )
                    print(f"  {original_cross_date.date()} (crossing on {crossing_day.date()}, checked {crossing_day.date()} to {original_cross_date.date()}): MA conditions {days_met}/{total_days} days ({pct:.1%}) - {'✓ VALID' if conditions_met else '✗ REJECTED'}")
                else:
                    # Fallback: check the entire period if we can't find exact crossing day
                    conditions_met, pct, days_met, total_days = check_ma_conditions_for_period(
                        original_cross_date, period_start, data, combined_ma_condition, 
                        threshold=ma_condition_threshold
                    )
                    print(f"  {original_cross_date.date()} (period: {period_start.date()} to {original_cross_date.date()}, no exact crossing day found): MA conditions {days_met}/{total_days} days ({pct:.1%}) - {'✓ VALID' if conditions_met else '✗ REJECTED'}")
                
                if conditions_met:
                    valid_crossings.loc[cross_date] = 1
            
            price_crossing = valid_crossings
            print(f"Valid exit signals after MA condition check: {price_crossing.sum()}")
        
        print(f"Price crossings detected: {price_crossing.sum()}")
        if price_crossing.sum() > 0:
            crossing_dates = display_data.index[price_crossing == 1]
            print(f"Crossing dates ({len(crossing_dates)}): {crossing_dates.tolist()}")
            # Show MA condition status at crossing points
            for cross_date in crossing_dates[:5]:  # Show first 5
                daily_idx = data.index.get_indexer([cross_date], method='nearest')[0]
                if 0 <= daily_idx < len(combined_ma_condition):
                    print(f"  {cross_date}: MA condition = {combined_ma_condition.iloc[daily_idx]}")
        else:
            print("No crossings detected - checking why:")
            print(f"  Display data Open range: {display_data['Open'].min():.2f} to {display_data['Open'].max():.2f}")
            print(f"  Display data Close range: {display_data['Close'].min():.2f} to {display_data['Close'].max():.2f}")
            print(f"  MA values range: {ma_at_period_dates.min():.2f} to {ma_at_period_dates.max():.2f}")
            print(f"  Periods where Close < MA: {(display_data['Close'] < ma_at_period_dates).sum()}")
            print(f"  Periods where Open >= MA and Close < MA: {((display_data['Open'] >= ma_at_period_dates) & (display_data['Close'] < ma_at_period_dates)).sum()}")
        
        entry_zones = identify_entry_zones_with_conditions(
            data, 
            display_data, 
            ma_long_values, 
            reentry_signals, 
            price_crossing, 
            combined_ma_condition,
            ma_condition_threshold=ma_condition_threshold,
            period=period
        )
        
        print(f"=== ENTRY ZONES ({period} view) ===")
        print(f"Number of entry zones identified: {len(entry_zones)}")
        if len(entry_zones) > 0:
            for i, zone in enumerate(entry_zones[:5]):  # Show first 5
                zone_length = (zone['end'] - zone['start']).days
                print(f"  Zone {i+1}: {zone['start'].date()} to {zone['end'].date()} ({zone_length} days), completed={zone['completed']}")
        else:
            print("No entry zones - checking conditions:")
            print(f"  Total days in data: {len(data)}")
            print(f"  Days with price below MA: {(data['Close'] < ma_long_values).sum()}")
            print(f"  Days with MA conditions met: {combined_ma_condition.sum()}")
            print(f"  Days with reentry signals: {reentry_signals.sum()}")
            print(f"  Price crossings detected: {price_crossing.sum()}")
            
            # Check if there are any periods where all conditions align
            below_ma = data['Close'] < ma_long_values
            both_conditions = below_ma & combined_ma_condition
            print(f"  Days with BOTH below MA AND MA conditions: {both_conditions.sum()}")
            
            if price_crossing.sum() > 0:
                print("  Crossings exist but no zones - checking why:")
                for cross_date in display_data.index[price_crossing == 1][:3]:
                    print(f"    Crossing at {cross_date.date()}:")
                    # Find data after crossing
                    mask = (data.index > cross_date) & (data.index < cross_date + pd.Timedelta(days=90))
                    if mask.any():
                        days_after = mask.sum()
                        below_after = below_ma[mask].sum()
                        conditions_after = combined_ma_condition[mask].sum()
                        both_after = both_conditions[mask].sum()
                        reentry_after = reentry_signals[mask].sum()
                        print(f"      Days after crossing (90d window): {days_after}")
                        print(f"      Days below MA: {below_after}")
                        print(f"      Days with MA conditions: {conditions_after}")
                        print(f"      Days with BOTH: {both_after}")
                        print(f"      Reentry signals: {reentry_after}")
        
        # Plot
        plotter = Plotter()
        fig = plotter.plot_candlestick(display_data, name=selected_ticker)
        
        # Customize hover for quarterly/monthly to show period labels
        if period in ['quarterly', 'monthly']:
            # Create hover text showing the period
            hover_text = []
            for date in display_data.index:
                if period == 'quarterly':
                    quarter = (date.month - 1) // 3 + 1
                    hover_text.append(f"Q{quarter} {date.year}")
                else:  # monthly
                    hover_text.append(date.strftime('%B %Y'))
            
            # Update the candlestick trace
            for trace in fig.data:
                if trace.type == 'candlestick':
                    trace.text = hover_text
                    trace.hovertext = hover_text
                    break
        
        print(f"=== PLOTTING ===")
        print(f"After candlestick - fig has {len(fig.data)} traces")
        if len(fig.data) > 0:
            print(f"Candlestick x type: {type(fig.data[0].x)}")
            print(f"Candlestick x[0]: {fig.data[0].x[0]}, x[-1]: {fig.data[0].x[-1]}")
        
        plotter.add_moving_average(ma_long_filt)
        
        print(f"After MA - plotter.fig has {len(plotter.fig.data)} traces")
        if len(plotter.fig.data) > 1:
            print(f"MA x type: {type(plotter.fig.data[1].x)}")
            print(f"MA x[0]: {plotter.fig.data[1].x[0]}, x[-1]: {plotter.fig.data[1].x[-1]}")
        
        plotter.add_bollinger_bands(bb_long_filt, name_prefix=f'BB {period_label.split("/")[0]}', dashed=False)
        
        print(f"After BB long - plotter.fig has {len(plotter.fig.data)} traces")
        if len(plotter.fig.data) > 2:
            print(f"BB upper x[0]: {plotter.fig.data[2].x[0]}, x[-1]: {plotter.fig.data[2].x[-1]}")
        
        plotter.add_bollinger_bands(bb_short_filt, name_prefix=f'BB {period_label.split("/")[1]}', dashed=True)
        
        print(f"After all plots - plotter.fig has {len(plotter.fig.data)} traces")
        
        ticker_name = tickers_dict.get(selected_ticker, selected_ticker)
        long_name, short_name = period_label.split('/')
        
        # Subplots
        fig_with_bandwidth = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.6,0.2,0.2],
            subplot_titles=(f"{ticker_name} ({display_label} Candles, {period_label} MA/BB)", f"Band Width ({long_name} BB)", "Exit Signals: MA Change & Price Crossing"),
            specs=[[{"secondary_y":False}],[{"secondary_y":False}],[{"secondary_y":False}]])
        
        for trace in plotter.fig.data:
            fig_with_bandwidth.add_trace(trace, row=1, col=1)
        
        # Zones
        y_min = max(0, bb_long_filt['lower'].min() * 0.9) if len(bb_long_filt['lower']) > 0 else 0
        
        print(f"Number of entry zones: {len(entry_zones)}")
        print(f"Display zones selected: {display_zones}")
        print(f"Y min for fill: {y_min}")
        
        for zone in entry_zones:
            zone_data = data.loc[zone['start']:zone['end']]
            print(f"Zone from {zone['start']} to {zone['end']}, completed: {zone['completed']}, length: {len(zone_data)}")
            
            if zone['completed'] and 'complete_zone' in display_zones:
                fig_with_bandwidth.add_trace(go.Scatter(x=zone_data.index, y=[y_min]*len(zone_data), mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'), row=1, col=1)
                fig_with_bandwidth.add_trace(go.Scatter(x=zone_data.index, y=zone_data['Close'], mode='lines', fill='tonexty', fillcolor='rgba(100,200,100,0.3)', line=dict(width=0), name='Complete Zone', showlegend=False, hoverinfo='skip'), row=1, col=1)
            elif not zone['completed'] and 'incomplete_zone' in display_zones:
                fig_with_bandwidth.add_trace(go.Scatter(x=zone_data.index, y=[y_min]*len(zone_data), mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'), row=1, col=1)
                fig_with_bandwidth.add_trace(go.Scatter(x=zone_data.index, y=zone_data['Close'], mode='lines', fill='tonexty', fillcolor='rgba(255,200,100,0.3)', line=dict(width=0), name='Incomplete Zone', showlegend=False, hoverinfo='skip'), row=1, col=1)
        
        if 'below_ma' in display_zones:
            is_below = data['Close'] < ma_long_values
            segment_id = (is_below != is_below.shift(1)).cumsum().fillna(0)
            segments_df = pd.DataFrame({'Close': data['Close'], 'is_below': is_below, 'segment': segment_id})
            for name, group in segments_df.groupby('segment'):
                if len(group) >= 2 and group['is_below'].mean() > 0.5:
                    fig_with_bandwidth.add_trace(go.Scatter(x=group.index, y=[y_min]*len(group), mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'), row=1, col=1)
                    fig_with_bandwidth.add_trace(go.Scatter(x=group.index, y=group['Close'], mode='lines', fill='tonexty', fillcolor='rgba(255,0,0,0.2)', line=dict(width=0), showlegend=False, hoverinfo='skip'), row=1, col=1)
        
        # Re-entry signals
        reentry_dates = data.index[reentry_signals]
        reentry_prices = data.loc[reentry_signals, 'Low'] * 0.98
        if len(reentry_dates) > 0:
            print(f"Re-entry signals: {len(reentry_dates)} dates from {reentry_dates[0]} to {reentry_dates[-1]}")
            fig_with_bandwidth.add_trace(go.Scatter(x=reentry_dates, y=reentry_prices, mode='markers',
                marker=dict(symbol='triangle-up', size=12, color='green', line=dict(color='darkgreen', width=1)),
                name='Re-Entry Signal'), row=1, col=1)
        
        # BandWidth
        print(f"BandWidth: {len(bandwidth_long)} points from {data.index[0]} to {data.index[-1]}")
        fig_with_bandwidth.add_trace(go.Scatter(x=data.index, y=bandwidth_long, name='BandWidth', line=dict(color='darkblue', width=2)), row=2, col=1)
        fig_with_bandwidth.add_hline(y=bandwidth_long.mean(), line_dash="dash", line_color="gray", opacity=0.5, row=2, col=1)
        
        # MA changes
        print(f"MA changes: {len(ma_long_change)} points from {data.index[0]} to {data.index[-1]}")
        fig_with_bandwidth.add_trace(go.Scatter(x=data.index, y=ma_long_change, name=f'MA {long_name} Change', line=dict(color='red', width=2)), row=3, col=1)
        fig_with_bandwidth.add_trace(go.Scatter(x=data.index, y=ma_short_change, name=f'MA {short_name} Change', line=dict(color='green', width=2)), row=3, col=1)
        
        # Price crossings - show all validated exit signals
        # These have already been filtered by MA conditions (with lookahead for daily)
        # so we don't need to check MA conditions again
        for cross_date in display_data.index[price_crossing == 1]:
            fig_with_bandwidth.add_vline(x=cross_date, line_width=2, line_dash="solid", 
                                        line_color="darkgrey", opacity=0.7, row=3, col=1)
        
        # MA condition shading
        combined_segment_id = (combined_ma_condition != combined_ma_condition.shift(1)).cumsum()
        combined_df = pd.DataFrame({'combined': combined_ma_condition, 'segment': combined_segment_id, 'date': data.index})
        for name, group in combined_df.groupby('segment'):
            if len(group) > 0 and group['combined'].iloc[0]:
                fig_with_bandwidth.add_vrect(x0=group['date'].iloc[0], x1=group['date'].iloc[-1], fillcolor="rgba(200,200,200,0.3)", layer="below", line_width=0, row=3, col=1)
        
        # Zero line
        fig_with_bandwidth.add_hline(y=0, line_dash="solid", line_color="black", opacity=1, line_width=2, row=3, col=1)
        
        # Threshold lines
        fig_with_bandwidth.add_hline(y=flat_threshold_840, line_dash="dash", line_color="red", opacity=0.5, row=3, col=1)
        fig_with_bandwidth.add_hline(y=flat_threshold_420, line_dash="dash", line_color="green", opacity=0.5, row=3, col=1)
        
        # IMPROVED ANNOTATIONS - positioned below the title of bottom chart
        # Use paper coordinates to position relative to the subplot
        # The bottom subplot starts at approximately y=0 and goes to y=0.23 (based on row_heights [0.6, 0.2, 0.2])
        
        annotation_x_date = data.index[int(len(data) * 0.02)]  # 2% from start
        
        fig_with_bandwidth.add_annotation(
            text=f"Flat {long_name}: < {flat_threshold_840}%", 
            xref="x3", yref="paper",  # Use paper coordinates for y
            x=annotation_x_date, y=0.22,  # Position at top of bottom subplot (just below title)
            xanchor="left", yanchor="top",
            showarrow=False, 
            bgcolor="rgba(255,255,255,0.9)", 
            bordercolor="red", borderwidth=1, 
            font=dict(size=10, color="red")
        )
        fig_with_bandwidth.add_annotation(
            text=f"Decreasing {short_name}: < {flat_threshold_420}%", 
            xref="x3", yref="paper",  # Use paper coordinates for y
            x=annotation_x_date, y=0.19,  # Position slightly lower
            xanchor="left", yanchor="top",
            showarrow=False, 
            bgcolor="rgba(255,255,255,0.9)", 
            bordercolor="green", borderwidth=1, 
            font=dict(size=10, color="green")
        )
        
        # Layout with improved legend spacing
        fig_with_bandwidth.update_layout(
            height=1200, 
            showlegend=True, 
            hovermode='closest',  # Use 'closest' instead of 'x unified' to avoid date confusion from BB traces
            legend=dict(
                orientation="h", 
                yanchor="bottom", 
                y=1.05,  # Increased from 1.02 to add more space
                xanchor="left", 
                x=0, 
                bgcolor="rgba(255,255,255,0.8)", 
                bordercolor="lightgray", 
                borderwidth=1
            ),
            xaxis=dict(
                rangeselector=dict(
                    buttons=[
                        dict(count=1, label="1m", step="month", stepmode="backward"),
                        dict(count=6, label="6m", step="month", stepmode="backward"), 
                        dict(count=1, label="1y", step="year", stepmode="backward"),
                        dict(step="all", label="All")
                    ], 
                    y=1.18,  # Adjusted to accommodate legend
                    yanchor="top"
                )
            )
        )
        
        # Custom x-axis formatting for period views
        if period == 'quarterly':
            tick_vals = display_data.index.tolist()
            tick_text = format_quarter_labels_two_levels(display_data.index)
            
            fig_with_bandwidth.update_xaxes(
                tickmode='array',
                tickvals=tick_vals,
                ticktext=tick_text,
                tickangle=0,
                row=1, col=1
            )
        elif period == 'monthly':
            tick_vals = display_data.index.tolist()
            tick_text = format_monthly_labels_as_quarters(display_data.index)
            
            fig_with_bandwidth.update_xaxes(
                tickmode='array',
                tickvals=tick_vals,
                ticktext=tick_text,
                tickangle=0,
                row=1, col=1
            )
        # For daily, use Plotly's automatic date formatting (much faster)
        
        fig_with_bandwidth.update_xaxes(row=1, col=1, rangeslider_visible=False, showticklabels=True)
        fig_with_bandwidth.update_xaxes(row=2, col=1, rangeslider_visible=False, showticklabels=True)
        fig_with_bandwidth.update_xaxes(title_text="Date", row=3, col=1, rangeslider_visible=False, showticklabels=True)
        
        y_type = 'log' if scale == 'log' else 'linear'
        fig_with_bandwidth.update_yaxes(title_text="Price", type=y_type, autorange=True, row=1, col=1)
        fig_with_bandwidth.update_yaxes(title_text="Band Width", row=2, col=1)
        fig_with_bandwidth.update_yaxes(title_text="MA Change (%)", row=3, col=1)
        
        return fig_with_bandwidth, ticker_name
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        plotter = Plotter()
        fig = plotter.plot_candlestick(ticker_data[selected_ticker], name=selected_ticker)
        return fig, f"Error: {selected_ticker}"

if __name__ == '__main__':
    app.run(debug=False, port=8050)