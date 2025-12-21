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
        
        # Previous candle is bearish (red)
        prev_bearish = prev_close < prev_open
        # Current candle is bullish (green)
        curr_bullish = curr_close > curr_open
        # Current candle engulfs previous
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
            
        # Hammer: small body at top, long lower shadow
        lower_shadow = min(open_price, close_price) - low_price
        upper_shadow = high_price - max(open_price, close_price)
        
        is_hammer = (lower_shadow > 2 * body) and (upper_shadow < body)
        
        # Inverted hammer: small body at bottom, long upper shadow
        is_inverted = (upper_shadow > 2 * body) and (lower_shadow < body)
        
        if is_hammer or is_inverted:
            signals.iloc[i] = True
    
    return signals


def detect_morning_star(data):
    """Detect morning star pattern (3-candle reversal)"""
    signals = pd.Series(False, index=data.index)
    
    for i in range(2, len(data)):
        # First candle: bearish
        first_open = data['Open'].iloc[i-2]
        first_close = data['Close'].iloc[i-2]
        first_bearish = first_close < first_open
        
        # Second candle: small body (star)
        second_open = data['Open'].iloc[i-1]
        second_close = data['Close'].iloc[i-1]
        second_body = abs(second_close - second_open)
        first_body = abs(first_close - first_open)
        second_small = second_body < 0.3 * first_body
        
        # Third candle: bullish
        third_open = data['Open'].iloc[i]
        third_close = data['Close'].iloc[i]
        third_bullish = third_close > third_open
        
        # Third closes above midpoint of first
        recovers = third_close > (first_open + first_close) / 2
        
        if first_bearish and second_small and third_bullish and recovers:
            signals.iloc[i] = True
    
    return signals


def detect_price_crossing_down(data, ma_values):
    """Detect when price crosses below MA (50% rule for segment)"""
    crossing_signal = pd.Series(0, index=data.index, dtype=float)
    
    is_below = data['Close'] < ma_values
    segment_id = (is_below != is_below.shift(1)).cumsum()
    segment_id = segment_id.fillna(0)
    
    segments_df = pd.DataFrame({
        'is_below': is_below, 
        'segment': segment_id
    })
    
    for name, group in segments_df.groupby('segment'):
        if len(group) < 2:
            continue
        
        # Mark start of segments where price is below MA (crossing down)
        if group['is_below'].mean() > 0.5:
            crossing_signal.loc[group.index[0]] = 1
    
    return crossing_signal


def detect_decreasing_prices(data, window=20):
    """Detect periods of decreasing prices using 50% rule over a rolling window"""
    price_change = data['Close'].pct_change()
    is_decreasing = price_change < 0
    
    # Apply 50% rule over rolling window
    rolling_decreasing = is_decreasing.rolling(window=window, min_periods=1).mean()
    decreasing_signal = (rolling_decreasing > 0.5).astype(float)
    
    return decreasing_signal


def identify_entry_zones_with_conditions(data, display_data, ma_values, reentry_signals, price_crossing, combined_ma_condition):
    """
    Identify zones from entry (when ALL exit conditions are met) to first re-entry signal.
    Entry conditions:
    1. Price crosses below MA (from price_crossing on display_data)
    2. Both MA conditions are true (combined_ma_condition on daily data)
    
    Resets when price crosses back above MA.
    """
    zones = []
    is_below = data['Close'] < ma_values
    
    # Map price crossing dates to daily data
    crossing_dates = set(display_data.index[price_crossing == 1])
    
    in_zone = False
    zone_start = None
    waiting_for_ma_condition = False
    
    for i in range(len(data)):
        current_date = data.index[i]
        
        # Check if we have a price crossing at this date (or most recent period)
        # Find the most recent crossing in display_data
        recent_crossing = False
        for cross_date in crossing_dates:
            if cross_date <= current_date:
                # Check if this crossing is recent (within the display period)
                if i > 0:
                    prev_date = data.index[i-1]
                    if cross_date > prev_date or cross_date == current_date:
                        recent_crossing = True
                        break
        
        # Check if ALL entry conditions are met
        if recent_crossing and combined_ma_condition.iloc[i] and not in_zone:
            # Start a new zone
            in_zone = True
            zone_start = current_date
        
        # Check if we crossed back above MA (reset)
        if i > 0 and is_below.iloc[i-1] and not is_below.iloc[i]:
            # Crossed above - end zone without completion
            if in_zone and zone_start is not None:
                zones.append({
                    'start': zone_start,
                    'end': data.index[i-1],
                    'completed': False
                })
            in_zone = False
            zone_start = None
        
        # Check if we have a re-entry signal while in zone
        if in_zone and reentry_signals.iloc[i]:
            # Complete the zone
            zones.append({
                'start': zone_start,
                'end': current_date,
                'completed': True
            })
            in_zone = False
            zone_start = None
    
    # Handle case where we're still in a zone at the end
    if in_zone and zone_start is not None:
        zones.append({
            'start': zone_start,
            'end': data.index[-1],
            'completed': False
        })
    
    return zones


def identify_entry_to_reentry_zones(data, ma_values, reentry_signals):
    """
    Identify zones from entry (price crosses below MA) to first re-entry signal.
    Resets when price crosses back above MA.
    """
    zones = []
    is_below = data['Close'] < ma_values
    
    in_zone = False
    zone_start = None
    
    for i in range(len(data)):
        # Check if we just crossed below MA (entering below zone)
        if i > 0 and not is_below.iloc[i-1] and is_below.iloc[i]:
            # Crossed below - start a new zone
            in_zone = True
            zone_start = data.index[i]
        
        # Check if we crossed back above MA (reset)
        if i > 0 and is_below.iloc[i-1] and not is_below.iloc[i]:
            # Crossed above - end zone without completion
            if in_zone and zone_start is not None:
                # Zone ended by crossing back up
                zones.append({
                    'start': zone_start,
                    'end': data.index[i-1],
                    'completed': False
                })
            in_zone = False
            zone_start = None
        
        # Check if we have a re-entry signal while in zone
        if in_zone and reentry_signals.iloc[i]:
            # Complete the zone
            zones.append({
                'start': zone_start,
                'end': data.index[i],
                'completed': True
            })
            in_zone = False
            zone_start = None
    
    # Handle case where we're still in a zone at the end
    if in_zone and zone_start is not None:
        zones.append({
            'start': zone_start,
            'end': data.index[-1],
            'completed': False
        })
    
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

# Set up the app with a theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])
load_figure_template("LUX")

app.layout = dbc.Container([
    html.H1("Stock Chart with Bollinger Bands & Trading Signals", style={'textAlign': 'center'}),
    html.H2(id='ticker-name', style={'textAlign': 'center'}),
    
    dbc.Row([
        dbc.Col([
            html.Label("Select Ticker:"),
            dcc.Dropdown(
                id='ticker-dropdown',
                options=[{'label': ticker, 'value': ticker} for ticker in tickers],
                value='EEM',
            )
        ], width=3),
        dbc.Col([
            html.Label("Time Period:"),
            dcc.RadioItems(
                id='period-selector',
                options=[
                    {'label': ' Monthly (40M/20M)', 'value': 'monthly'},
                    {'label': ' Quarterly (40Q/20Q)', 'value': 'quarterly'}
                ],
                value='monthly',
                inline=True,
                style={'marginTop': '5px'}
            )
        ], width=3),
        dbc.Col([
            html.Label("Flat Long MA Threshold (%):"),
            dcc.Input(
                id='flat-threshold-840',
                type='number',
                value=0.025,
                step=0.005,
                style={'width': '100%'}
            ),
            html.Small("Values below this threshold", style={'color': 'gray'})
        ], width=3),
        dbc.Col([
            html.Label("Decreasing Short MA Threshold (%):"),
            dcc.Input(
                id='flat-threshold-420',
                type='number',
                value=0,
                step=0.005,
                style={'width': '100%'}
            ),
            html.Small("Negative values for decreasing", style={'color': 'gray'})
        ], width=3),
    ], className="mb-3"),
    
    dbc.Row([
        dbc.Col([
            html.Label("Re-Entry Signals:"),
            dcc.Checklist(
                id='signal-checklist',
                options=[
                    {'label': ' Bullish Engulfing', 'value': 'engulfing'},
                    {'label': ' Hammer/Inverted Hammer', 'value': 'hammer'},
                    {'label': ' Morning Star', 'value': 'morning_star'}
                ],
                value=['engulfing', 'hammer', 'morning_star'],
                inline=True,
                style={'marginTop': '5px'}
            )
        ], width=6),
        dbc.Col([
            html.Label("BB Distance for Re-Entry (%):"),
            dcc.Input(
                id='bb-distance-threshold',
                type='number',
                value=10,
                min=0,
                step=5,
                style={'width': '100%'}
            ),
            html.Small("Max distance from lower BB (% of BB width)", style={'color': 'gray'})
        ], width=3),
    ], className="mb-3"),
    
    dbc.Row([
        dbc.Col([
            html.Label("Display Zones:"),
            dcc.Checklist(
                id='zone-display-checklist',
                options=[
                    {'label': ' Below MA (Red)', 'value': 'below_ma'},
                    {'label': ' Entry-to-Reentry Complete (Green)', 'value': 'complete_zone'},
                    {'label': ' Entry-to-Reentry Incomplete (Orange)', 'value': 'incomplete_zone'}
                ],
                value=['complete_zone'],  # Only green zone selected by default
                inline=True,
                style={'marginTop': '5px'}
            )
        ], width=12),
    ], className="mb-4"),

    dcc.Graph(id='stock-chart', style={'height': '120vh'})
], fluid=True, className="p-4")


@app.callback(
    [Output('stock-chart', 'figure'),
     Output('ticker-name', 'children')],
    [Input('ticker-dropdown', 'value'),
     Input('period-selector', 'value'),
     Input('flat-threshold-840', 'value'),
     Input('flat-threshold-420', 'value'),
     Input('signal-checklist', 'value'),
     Input('bb-distance-threshold', 'value'),
     Input('zone-display-checklist', 'value')]
)
def update_chart(selected_ticker, period, flat_threshold_840, flat_threshold_420, enabled_signals, bb_distance_threshold, display_zones):
    try:
        print(f"Updating chart for {selected_ticker} with period: {period}")
        data = ticker_data[selected_ticker]
        
        if 'ticker' not in data.attrs:
            data.attrs['ticker'] = selected_ticker
        
        # Set default values if None
        if flat_threshold_840 is None:
            flat_threshold_840 = 0.1
        if flat_threshold_420 is None:
            flat_threshold_420 = -0.1
        if enabled_signals is None:
            enabled_signals = []
        if bb_distance_threshold is None:
            bb_distance_threshold = 10
        if display_zones is None:
            display_zones = ['below_ma', 'complete_zone', 'incomplete_zone']
        
        # Determine window sizes - ALWAYS use monthly periods (840/420 days)
        long_window = 840   # 40 months
        short_window = 420  # 20 months
        period_label = "40M/20M"
        
        # Resample price data for display based on selection
        if period == 'quarterly':
            # Display quarterly candles
            display_data = data.resample('QE').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last'
            }).dropna()
            display_label = "Quarterly"
        else:  # monthly
            # Display monthly candles
            display_data = data.resample('ME').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last'
            }).dropna()
            display_label = "Monthly"
        
        # Calculate MA and BB on DAILY data (for smooth lines on chart)
        ma_long = MovingAverage(window=long_window)
        ma_long_values = ma_long.calculate(data)
        ma_long_change = ma_long.calculate_change(data)  # Daily MA change
        
        ma_short = MovingAverage(window=short_window)
        ma_short_values = ma_short.calculate(data)
        ma_short_change = ma_short.calculate_change(data)  # Daily MA change
        
        bb_long = BollingerBands(window=long_window, num_std=2)
        bb_long_values = bb_long.calculate(data)
        
        bb_short = BollingerBands(window=short_window, num_std=2)
        bb_short_values = bb_short.calculate(data)
        
        # Calculate BandWidth on daily data
        bw = BandWidth(window=long_window)
        bandwidth_long = bw.calculate(bb_long_values)
        
        # Detect candlestick patterns on daily data (only if enabled)
        bullish_engulfing = detect_bullish_engulfing(data) if 'engulfing' in enabled_signals else pd.Series(False, index=data.index)
        hammer = detect_hammer(data) if 'hammer' in enabled_signals else pd.Series(False, index=data.index)
        morning_star = detect_morning_star(data) if 'morning_star' in enabled_signals else pd.Series(False, index=data.index)
        
        # Combine all re-entry signals
        any_reentry_signal = bullish_engulfing | hammer | morning_star
        
        # Filter signals: only when price is below long MA AND near lower BB (using daily values)
        is_below_ma = data['Close'] < ma_long_values
        
        # Calculate distance from lower BB as percentage of BB width
        bb_width = bb_long_values['upper'] - bb_long_values['lower']
        distance_from_lower_bb = data['Close'] - bb_long_values['lower']
        distance_pct = (distance_from_lower_bb / bb_width) * 100
        
        # Signal only triggers when within threshold distance from lower BB
        near_lower_bb = distance_pct <= bb_distance_threshold
        
        reentry_signals = any_reentry_signal & is_below_ma & near_lower_bb
        
        # Detect exit conditions:
        # 1. Price crosses below MA on display data (monthly/quarterly)
        ma_long_display = MovingAverage(window=40)
        ma_long_display_values = ma_long_display.calculate(display_data)
        price_crossing = detect_price_crossing_down(display_data, ma_long_display_values)
        
        # 2. Both MA conditions are met (flat long MA and decreasing short MA) on daily data
        flat_long = ma_long_change < flat_threshold_840
        decreasing_short = ma_short_change < flat_threshold_420
        combined_ma_condition = flat_long & decreasing_short
        
        # Create entry zones that start when ALL exit conditions are met
        entry_zones = identify_entry_zones_with_conditions(
            data, 
            display_data,
            ma_long_values, 
            reentry_signals,
            price_crossing,
            combined_ma_condition
        )
        
        # Create plot with monthly/quarterly candles but daily MA/BB
        plotter = Plotter()
        fig = plotter.plot_candlestick(display_data, name=selected_ticker)
        plotter.add_moving_average(ma_long_values)
        plotter.add_bollinger_bands(bb_long_values, name_prefix=f'BB {period_label.split("/")[0]}', dashed=False)
        plotter.add_bollinger_bands(bb_short_values, name_prefix=f'BB {period_label.split("/")[1]}', dashed=True)
        
        ticker_name = tickers_dict.get(selected_ticker, selected_ticker)
        
        # Create subplot figure with 3 rows
        fig_with_bandwidth = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=(f"{ticker_name} ({display_label} Candles, {period_label} MA/BB)", f"Band Width ({period_label} BB)", "Exit Signals: MA Change & Price Crossing"),
            specs=[[{"secondary_y": False}], [{"secondary_y": False}], [{"secondary_y": False}]]
        )
        
        # Copy traces to row 1
        for trace in plotter.fig.data:
            fig_with_bandwidth.add_trace(trace, row=1, col=1)

        # Add entry-to-reentry zones (controlled by checkboxes)
        for zone in entry_zones:
            zone_data = data.loc[zone['start']:zone['end']]
            
            # Check if we should display this zone type
            if zone['completed'] and 'complete_zone' in display_zones:
                color = 'rgba(100, 200, 100, 0.3)'
                fig_with_bandwidth.add_trace(
                    go.Scatter(
                        x=zone_data.index,
                        y=zone_data['Close'],
                        mode='lines',
                        fill='tozeroy',
                        fillcolor=color,
                        line=dict(color='rgba(255, 255, 255, 0)'),
                        name='Entry to Re-Entry (Complete)',
                        showlegend=False,
                        hoverinfo='skip'
                    ),
                    row=1, col=1
                )
            elif not zone['completed'] and 'incomplete_zone' in display_zones:
                color = 'rgba(255, 200, 100, 0.3)'
                fig_with_bandwidth.add_trace(
                    go.Scatter(
                        x=zone_data.index,
                        y=zone_data['Close'],
                        mode='lines',
                        fill='tozeroy',
                        fillcolor=color,
                        line=dict(color='rgba(255, 255, 255, 0)'),
                        name='Entry to Re-Entry (Incomplete)',
                        showlegend=False,
                        hoverinfo='skip'
                    ),
                    row=1, col=1
                )

        # Shade regions where price is below long MA (controlled by checkbox)
        if 'below_ma' in display_zones:
            is_below = data['Close'] < ma_long_values
            segment_id = (is_below != is_below.shift(1)).cumsum()
            segment_id = segment_id.fillna(0)
        
            segments_df = pd.DataFrame({
                'Close': data['Close'], 
                'is_below': is_below, 
                'Date': data.index, 
                'SMA': ma_long_values
            })
            
            start_points = []
            end_points = []

            for name, group in segments_df.groupby(segment_id):
                if len(group) < 2:
                    continue
                
                if group['is_below'].mean() > 0.5:
                    # Add shaded region
                    fig_with_bandwidth.add_trace(
                        go.Scatter(
                            x=group.index,
                            y=group['Close'],
                            mode='lines',
                            fill='tozeroy',
                            fillcolor='rgba(255, 0, 0, 0.2)',
                            line=dict(color='rgba(255, 255, 255, 0)'),
                            name=f'Price below Long MA',
                            showlegend=False
                        ),
                        row=1, col=1
                    )
                    start_points.append({'x': group['Date'].iloc[0], 'y': group['SMA'].iloc[0]})
                    end_points.append({'x': group['Date'].iloc[-1], 'y': group['SMA'].iloc[-1]})
            
            # Add vertical lines for start/end points
            for point in start_points:
                fig_with_bandwidth.add_trace(
                    go.Scatter(
                        x=[point['x'], point['x']],
                        y=[0, point['y']],
                        mode='lines',
                        line=dict(color='darkred', width=1),
                        showlegend=False,
                    ),
                    row=1, col=1
                )

            for point in end_points:
                fig_with_bandwidth.add_trace(
                    go.Scatter(
                        x=[point['x'], point['x']],
                        y=[0, point['y']],
                        mode='lines',
                        line=dict(color='darkred', width=1),
                        showlegend=False,
                    ),
                    row=1, col=1
                )
        
        # Add re-entry signals to main chart
        reentry_dates = data.index[reentry_signals]
        reentry_prices = data.loc[reentry_signals, 'Low'] * 0.98  # Slightly below for visibility
        
        if len(reentry_dates) > 0:
            fig_with_bandwidth.add_trace(
                go.Scatter(
                    x=reentry_dates,
                    y=reentry_prices,
                    mode='markers',
                    marker=dict(
                        symbol='triangle-up',
                        size=12,
                        color='green',
                        line=dict(color='darkgreen', width=1)
                    ),
                    name='Re-Entry Signal',
                    hovertemplate='<b>Re-Entry Signal</b><br>Date: %{x}<br>Price: %{y:.2f}<extra></extra>'
                ),
                row=1, col=1
            )

        # Add BandWidth to row 2 (using daily data)
        fig_with_bandwidth.add_trace(
            go.Scatter(
                x=data.index,
                y=bandwidth_long,
                name='BandWidth',
                line=dict(color='darkblue', width=2)
            ),
            row=2, col=1
        )
        
        mean_bw = bandwidth_long.mean()
        fig_with_bandwidth.add_hline(
            y=mean_bw,
            line_dash="dash",
            line_color="gray",
            opacity=0.5,
            row=2, col=1
        )
        
        # Add MA change to row 3 (using daily data for smooth lines)
        fig_with_bandwidth.add_trace(
            go.Scatter(
                x=data.index,
                y=ma_long_change,
                name=f'MA {period_label.split("/")[0]} Change',
                line=dict(color='red', width=2)
            ),
            row=3, col=1
        )
        fig_with_bandwidth.add_trace(
            go.Scatter(
                x=data.index,
                y=ma_short_change,
                name=f'MA {period_label.split("/")[1]} Change',
                line=dict(color='green', width=2)
            ),
            row=3, col=1
        )
        
        # Add vertical lines for price crossing events (using monthly/quarterly data)
        crossing_dates = display_data.index[price_crossing == 1]
        for crossing_date in crossing_dates:
            fig_with_bandwidth.add_vline(
                x=crossing_date,
                line_width=2,
                line_dash="solid",
                line_color="darkgrey",
                opacity=0.7,
                row=3, col=1
            )

        # Shade backgrounds in subplot 3 for MA conditions (using daily data)
        flat_long = ma_long_change < flat_threshold_840
        decreasing_short = ma_short_change < flat_threshold_420
        combined_exit_condition = flat_long & decreasing_short
        
        # Add shaded regions only when BOTH conditions are met (using daily data)
        combined_segment_id = (combined_exit_condition != combined_exit_condition.shift(1)).cumsum()
        combined_df = pd.DataFrame({'combined': combined_exit_condition, 'segment': combined_segment_id, 'date': data.index})
        for name, group in combined_df.groupby('segment'):
            if len(group) > 0 and group['combined'].iloc[0]:
                fig_with_bandwidth.add_vrect(
                    x0=group['date'].iloc[0],
                    x1=group['date'].iloc[-1],
                    fillcolor="rgba(200, 200, 200, 0.3)",  # Light grey
                    layer="below",
                    line_width=0,
                    row=3, col=1
                )

        # Add zero line in subplot 3 (black)
        fig_with_bandwidth.add_hline(
            y=0,
            line_dash="solid",
            line_color="black",
            opacity=1,
            line_width=2,
            row=3, col=1
        )
        
        # Add threshold lines
        fig_with_bandwidth.add_hline(
            y=flat_threshold_840,
            line_dash="dash",
            line_color="red",
            opacity=0.5,
            annotation_text=f"Flat Long: < {flat_threshold_840}%",
            annotation_position="right",
            row=3, col=1
        )
        fig_with_bandwidth.add_hline(
            y=flat_threshold_420,
            line_dash="dash",
            line_color="green",
            opacity=0.5,
            annotation_text=f"Decreasing Short: < {flat_threshold_420}%",
            annotation_position="right",
            row=3, col=1
        )
        
        # Update layout
        fig_with_bandwidth.update_layout(
            height=1200,
            showlegend=True,
            hovermode='x unified',
            xaxis=dict(
                rangeselector=dict(
                    buttons=list([
                        dict(count=1, label="1m", step="month", stepmode="backward"),
                        dict(count=6, label="6m", step="month", stepmode="backward"),
                        dict(count=1, label="1y", step="year", stepmode="backward"),
                        dict(step="all", label="All")
                    ]),
                    y=1.07,
                    yanchor="top"
                )
            )
        )
        
        # Configure axes
        fig_with_bandwidth.update_xaxes(row=1, col=1, rangeslider_visible=False)
        fig_with_bandwidth.update_xaxes(row=2, col=1, rangeslider_visible=False)
        fig_with_bandwidth.update_xaxes(
            title_text="Date", 
            row=3, col=1,
            rangeslider_visible=True
        )
        
        # Y-axis labels
        fig_with_bandwidth.update_yaxes(title_text="Price", row=1, col=1)
        fig_with_bandwidth.update_yaxes(title_text="Band Width", row=2, col=1)
        fig_with_bandwidth.update_yaxes(title_text="MA Change (%) / Signals", row=3, col=1)
        
        # Fix subplot titles positioning
        annotations = fig_with_bandwidth.layout.annotations
        if len(annotations) > 0:
            annotations[0].update(y=1.02)
        if len(annotations) > 1:
            annotations[1].update(y=0.45)
        if len(annotations) > 2:
            annotations[2].update(y=0.21)

        print(f"Subplot figure: {len(fig_with_bandwidth.data)} traces")
        
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