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


def detect_price_crossing_down(data, ma_values):
    """Detect when price crosses below MA"""
    crossing_signal = pd.Series(0, index=data.index, dtype=float)
    
    is_below = data['Close'] < ma_values
    segment_id = (is_below != is_below.shift(1)).cumsum()
    segment_id = segment_id.fillna(0)
    
    segments_df = pd.DataFrame({'is_below': is_below, 'segment': segment_id})
    
    for name, group in segments_df.groupby('segment'):
        if len(group) < 2:
            continue
        if group['is_below'].mean() > 0.5:
            crossing_signal.loc[group.index[0]] = 1
    
    return crossing_signal


def identify_entry_zones_with_conditions(data, display_data, ma_values, reentry_signals, price_crossing, combined_ma_condition):
    """
    Identify zones from entry to FIRST re-entry signal.
    
    Entry starts when:
    - Price is below MA
    - Both MA conditions are true (flat long + decreasing short)
    - We are at or after a price crossing point (happened within last N periods)
    
    Entry ends when:
    - FIRST re-entry signal occurs (completed = True), OR
    - Price crosses back above MA (completed = False)
    """
    zones = []
    is_below = data['Close'] < ma_values
    
    # Get all crossing dates
    crossing_dates = display_data.index[price_crossing == 1].tolist()
    
    in_zone = False
    zone_start = None
    last_crossing_date = None
    
    for i in range(len(data)):
        current_date = data.index[i]
        
        # Update last_crossing_date if we passed a crossing
        for cross_date in crossing_dates:
            if cross_date <= current_date and (last_crossing_date is None or cross_date > last_crossing_date):
                last_crossing_date = cross_date
        
        # Entry condition: 
        # 1. We've had a crossing in the past
        # 2. Price is below MA
        # 3. Both MA conditions are true
        # 4. We're not already in a zone
        has_recent_crossing = last_crossing_date is not None
        
        if has_recent_crossing and is_below.iloc[i] and combined_ma_condition.iloc[i] and not in_zone:
            in_zone = True
            zone_start = current_date
        
        # Exit condition 1: Crossed back above MA (incomplete zone)
        if in_zone and not is_below.iloc[i]:
            if zone_start is not None:
                zones.append({'start': zone_start, 'end': data.index[i-1] if i > 0 else current_date, 'completed': False})
            in_zone = False
            zone_start = None
            last_crossing_date = None  # Reset for next cycle
        
        # Exit condition 2: FIRST re-entry signal (completed zone)
        if in_zone and reentry_signals.iloc[i]:
            zones.append({'start': zone_start, 'end': current_date, 'completed': True})
            in_zone = False
            zone_start = None
            last_crossing_date = None  # Reset for next cycle
    
    # Handle case where we're still in a zone at the end
    if in_zone and zone_start is not None:
        zones.append({'start': zone_start, 'end': data.index[-1], 'completed': False})
    
    return zones


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
     Input('zone-display-checklist', 'value')]
)
def update_chart(selected_ticker, period, ma_period, scale, flat_threshold_840, flat_threshold_420, enabled_signals, bb_distance_threshold, display_zones):
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
        
        print(f"Thresholds: flat_long={flat_threshold_840}, decreasing_short={flat_threshold_420}")
        
        # MA/BB windows
        if ma_period == '20m10m':
            long_window, short_window, period_label = 420, 210, "20M/10M"
        else:
            long_window, short_window, period_label = 840, 420, "40M/20M"
        
        # Resample price data
        if period == 'quarterly':
            display_data = data.resample('QE').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
            display_label = "Quarterly"
        elif period == 'monthly':
            display_data = data.resample('ME').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
            display_label = "Monthly"
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
        
        # Exit conditions
        ma_long_display = MovingAverage(window=40)
        ma_long_display_values = ma_long_display.calculate(display_data)
        price_crossing = detect_price_crossing_down(display_data, ma_long_display_values)
        
        print(f"Price crossings detected: {price_crossing.sum()}")
        if price_crossing.sum() > 0:
            crossing_dates = display_data.index[price_crossing == 1]
            print(f"Crossing dates: {crossing_dates[:5].tolist() if len(crossing_dates) > 5 else crossing_dates.tolist()}")
        
        flat_long = ma_long_change < flat_threshold_840
        decreasing_short = ma_short_change < flat_threshold_420
        combined_ma_condition = flat_long & decreasing_short
        
        print(f"Days with flat long MA: {flat_long.sum()}")
        print(f"Days with decreasing short MA: {decreasing_short.sum()}")
        print(f"Days with both conditions: {combined_ma_condition.sum()}")
        
        entry_zones = identify_entry_zones_with_conditions(data, display_data, ma_long_values, reentry_signals, price_crossing, combined_ma_condition)
        
        # Plot
        plotter = Plotter()
        fig = plotter.plot_candlestick(display_data, name=selected_ticker)
        
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
        
        # Price crossings - these are just crossings, we'll filter them for display later
        for cross_date in display_data.index[price_crossing == 1]:
            # Only show crossing line if BOTH MA conditions are met at that time
            # Find the corresponding daily data point
            daily_mask = (data.index >= cross_date) & (data.index < cross_date + pd.Timedelta(days=30))
            if daily_mask.any():
                # Check if MA conditions are met during this period
                if combined_ma_condition[daily_mask].any():
                    fig_with_bandwidth.add_vline(x=cross_date, line_width=2, line_dash="solid", line_color="darkgrey", opacity=0.7, row=3, col=1)
        
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
        
        # Annotations - use actual dates instead of x=0
        annotation_x_date = data.index[int(len(data) * 0.02)]  # 2% from start
        
        fig_with_bandwidth.add_annotation(
            text=f"Flat {long_name}: < {flat_threshold_840}%", 
            xref="x3", yref="y3", 
            x=annotation_x_date, y=flat_threshold_840, 
            xanchor="left", showarrow=False, 
            bgcolor="rgba(255,255,255,0.9)", 
            bordercolor="red", borderwidth=1, 
            font=dict(size=10, color="red")
        )
        fig_with_bandwidth.add_annotation(
            text=f"Decreasing {short_name}: < {flat_threshold_420}%", 
            xref="x3", yref="y3", 
            x=annotation_x_date, y=flat_threshold_420, 
            xanchor="left", showarrow=False, 
            bgcolor="rgba(255,255,255,0.9)", 
            bordercolor="green", borderwidth=1, 
            font=dict(size=10, color="green")
        )
        
        # Layout
        fig_with_bandwidth.update_layout(height=1200, showlegend=True, hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, bgcolor="rgba(255,255,255,0.8)", bordercolor="lightgray", borderwidth=1),
            xaxis=dict(rangeselector=dict(buttons=[dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"), dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all", label="All")], y=1.15, yanchor="top")))
        
        fig_with_bandwidth.update_xaxes(row=1, col=1, rangeslider_visible=False)
        fig_with_bandwidth.update_xaxes(row=2, col=1, rangeslider_visible=False)
        fig_with_bandwidth.update_xaxes(title_text="Date", row=3, col=1, rangeslider_visible=True)
        
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