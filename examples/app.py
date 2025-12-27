import dash
from dash import dcc, html, Input, Output, dash_table
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

# Import refactored modules
from bollinger_bands.indicators.signals import detect_reentry_signals
from bollinger_bands.indicators.crossing_detection import (
    detect_price_crossing_down_daily,
    detect_price_crossing_down_period,
    check_ma_conditions_for_period
)
from bollinger_bands.strategies.zones import identify_entry_zones_with_conditions
from bollinger_bands.visualization.formatting import (
    format_quarter_labels_two_levels,
    format_monthly_labels_as_quarters,
    format_daily_labels_simple
)
from bollinger_bands.indicators.relative_strength import get_all_tickers_metrics


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

app = dash.Dash(__name__, external_stylesheets=[
    dbc.themes.LUX,
    "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css"
])
load_figure_template("LUX")

app.layout = dbc.Container([
    html.H1("Stock Chart with Bollinger Bands & Trading Signals", style={'textAlign': 'center'}),
    html.H2(id='ticker-name', style={'textAlign': 'center'}),
    
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Label("Select Ticker:"),
                html.I(className="bi bi-info-circle ms-1", id="info-ticker", style={'cursor': 'pointer', 'color': '#6c757d'}),
            ], style={'display': 'flex', 'alignItems': 'center'}),
            dcc.Dropdown(id='ticker-dropdown', options=[{'label': t, 'value': t} for t in tickers], value='EEM'),
            dbc.Tooltip(
                "Choose which ETF or stock to analyze. Each ticker represents different market sectors or regions.",
                target="info-ticker",
                placement="right"
            ),
        ], width=3),
        dbc.Col([
            html.Div([
                html.Label("Time Period Price Chart:"),
                html.I(className="bi bi-info-circle ms-1", id="info-period", style={'cursor': 'pointer', 'color': '#6c757d'}),
            ], style={'display': 'flex', 'alignItems': 'center'}),
            dcc.RadioItems(id='period-selector', options=[
                {'label': ' Daily', 'value': 'daily'},
                {'label': ' Monthly', 'value': 'monthly'},
                {'label': ' Quarterly', 'value': 'quarterly'}
            ], value='monthly', inline=True, style={'marginTop': '5px'}),
            dbc.Tooltip(
                "How to aggregate price data for the candlestick chart. Daily shows each trading day, "
                "Monthly aggregates by month, Quarterly by quarter. Monthly/Quarterly reduce noise for long-term analysis.",
                target="info-period",
                placement="right"
            ),
        ], width=3),
        dbc.Col([
            html.Div([
                html.Label("Time Period MA & Bollinger Bands:"),
                html.I(className="bi bi-info-circle ms-1", id="info-ma-period", style={'cursor': 'pointer', 'color': '#6c757d'}),
            ], style={'display': 'flex', 'alignItems': 'center'}),
            dcc.RadioItems(id='ma-period-selector', options=[
                {'label': ' 40M/20M', 'value': '40m20m'},
                {'label': ' 20M/10M', 'value': '20m10m'}
            ], value='40m20m', inline=True, style={'marginTop': '5px'}),
            dbc.Tooltip(
                "Moving Average and Bollinger Band calculation periods. 40M/20M uses 840-day (40 months) long MA "
                "and 420-day (20 months) short MA. 20M/10M uses half those periods for faster signals but more noise.",
                target="info-ma-period",
                placement="right"
            ),
        ], width=3),
        dbc.Col([
            html.Div([
                html.Label("Scale:"),
                html.I(className="bi bi-info-circle ms-1", id="info-scale", style={'cursor': 'pointer', 'color': '#6c757d'}),
            ], style={'display': 'flex', 'alignItems': 'center'}),
            dcc.RadioItems(id='scale-selector', options=[
                {'label': ' Linear', 'value': 'linear'},
                {'label': ' Log', 'value': 'log'}
            ], value='linear', inline=True, style={'marginTop': '5px'}),
            dbc.Tooltip(
                "Y-axis scale type. Linear shows equal spacing for equal price changes. "
                "Log (logarithmic) shows equal spacing for equal percentage changes - better for long-term trends.",
                target="info-scale",
                placement="right"
            ),
        ], width=3),
    ], className="mb-3"),
    
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Label("Flat Long MA Threshold (%):"),
                html.I(className="bi bi-info-circle ms-1", id="info-flat-threshold", style={'cursor': 'pointer', 'color': '#6c757d'}),
            ], style={'display': 'flex', 'alignItems': 'center'}),
            dcc.Input(id='flat-threshold-840', type='number', value=0.025, step=0.005, style={'width': '100%'}),
            html.Small("Values below this threshold", style={'color': 'gray'}),
            dbc.Tooltip(
                "The long MA (40M/20M) is considered 'flat' when its rate of change is below this threshold. "
                "Lower values = stricter requirement for MA to be flat. Typical range: 0.01-0.05.",
                target="info-flat-threshold",
                placement="right"
            ),
        ], width=3),
        dbc.Col([
            html.Div([
                html.Label("Decreasing Short MA Threshold (%):"),
                html.I(className="bi bi-info-circle ms-1", id="info-decreasing-threshold", style={'cursor': 'pointer', 'color': '#6c757d'}),
            ], style={'display': 'flex', 'alignItems': 'center'}),
            dcc.Input(id='flat-threshold-420', type='number', value=0, step=0.005, style={'width': '100%'}),
            html.Small("Negative values for decreasing", style={'color': 'gray'}),
            dbc.Tooltip(
                "The short MA (20M/10M) is considered 'decreasing' when its rate of change is below this threshold. "
                "Use 0 to require any decrease, negative values for stronger decreases. Typical range: -0.05 to 0.05.",
                target="info-decreasing-threshold",
                placement="right"
            ),
        ], width=3),
        dbc.Col([
            html.Div([
                html.Label("BB Distance for Re-Entry (%):"),
                html.I(className="bi bi-info-circle ms-1", id="info-bb-distance", style={'cursor': 'pointer', 'color': '#6c757d'}),
            ], style={'display': 'flex', 'alignItems': 'center'}),
            dcc.Input(id='bb-distance-threshold', type='number', value=10, min=0, step=5, style={'width': '100%'}),
            html.Small("Max distance from lower BB", style={'color': 'gray'}),
            dbc.Tooltip(
                "Maximum distance from the lower Bollinger Band for a re-entry signal to be valid. "
                "Signals must occur within this % of the lower BB. Lower values = more restrictive. Typical: 5-15%.",
                target="info-bb-distance",
                placement="right"
            ),
        ], width=3),
    ], className="mb-3"),
    
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Label("Smoothing Window (Daily Exit):"),
                html.I(className="bi bi-info-circle ms-1", id="info-smoothing", style={'cursor': 'pointer', 'color': '#6c757d'}),
            ], style={'display': 'flex', 'alignItems': 'center'}),
            dcc.Input(id='smoothing-window', type='number', value=5, min=1, max=20, step=1, style={'width': '100%'}),
            html.Small("Days for price smoothing", style={'color': 'gray'}),
            dbc.Tooltip(
                "Number of days to smooth the price before detecting crossings in daily view. "
                "Higher values reduce noise but may delay signals. Lower values are more responsive but noisier. Typical: 3-7 days.",
                target="info-smoothing",
                placement="right"
            ),
        ], width=3),
        dbc.Col([
            html.Div([
                html.Label("MA Condition Lookahead (Daily):"),
                html.I(className="bi bi-info-circle ms-1", id="info-lookahead", style={'cursor': 'pointer', 'color': '#6c757d'}),
            ], style={'display': 'flex', 'alignItems': 'center'}),
            dcc.Input(id='daily-lookahead', type='number', value=10, min=0, max=30, step=1, style={'width': '100%'}),
            html.Small("Days to check MA conditions after crossing", style={'color': 'gray'}),
            dbc.Tooltip(
                "Days to look ahead after a crossing to verify MA conditions are met (daily view only). "
                "Set to 0 to disable. Higher values allow catching signals where conditions develop shortly after crossing. Typical: 5-15 days.",
                target="info-lookahead",
                placement="right"
            ),
        ], width=3),
        dbc.Col([
            html.Div([
                html.Label("MA Condition Threshold (All Views):"),
                html.I(className="bi bi-info-circle ms-1", id="info-ma-threshold", style={'cursor': 'pointer', 'color': '#6c757d'}),
            ], style={'display': 'flex', 'alignItems': 'center'}),
            dcc.Input(id='ma-condition-threshold', type='number', value=0.5, min=0, max=1, step=0.05, style={'width': '100%'}),
            html.Small("Min % with MA conditions (0=off, 0.5=50%)", style={'color': 'gray'}),
            dbc.Tooltip(
                "Minimum percentage of days that must have MA conditions met within the period/lookahead window. "
                "0 = disabled, 0.5 = 50% of days, 1 = 100% of days. Lower values are more permissive. Typical: 0.4-0.7.",
                target="info-ma-threshold",
                placement="right"
            ),
        ], width=3),
    ], className="mb-3"),
    
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Label("Re-Entry Signals:"),
                html.I(className="bi bi-info-circle ms-1", id="info-reentry", style={'cursor': 'pointer', 'color': '#6c757d'}),
            ], style={'display': 'flex', 'alignItems': 'center'}),
            dcc.Checklist(id='signal-checklist', options=[
                {'label': ' Bullish Engulfing', 'value': 'engulfing'},
                {'label': ' Hammer/Inverted Hammer', 'value': 'hammer'},
                {'label': ' Morning Star', 'value': 'morning_star'}
            ], value=['engulfing', 'hammer', 'morning_star'], inline=True, style={'marginTop': '5px'}),
            dbc.Tooltip(
                "Candlestick patterns that signal potential re-entry points when price is below MA and near lower Bollinger Band. "
                "Bullish Engulfing: green candle engulfs previous red. Hammer: long lower wick. Morning Star: 3-candle reversal pattern.",
                target="info-reentry",
                placement="right"
            ),
        ], width=6),
        dbc.Col([
            html.Div([
                html.Label("Max Re-Entry Signals per Zone:"),
                html.I(className="bi bi-info-circle ms-1", id="info-max-signals", style={'cursor': 'pointer', 'color': '#6c757d'}),
            ], style={'display': 'flex', 'alignItems': 'center'}),
            dcc.Input(id='max-reentry-signals', type='number', value=1, min=1, max=20, step=1, style={'width': '100%'}),
            html.Small("Zone ends after N signals (1=first signal)", style={'color': 'gray'}),
            dbc.Tooltip(
                "Number of re-entry signals to wait for before completing the zone. "
                "1 = zone ends at first signal (default). 3 = wait for 3rd signal. "
                "Higher values mean longer zones but may filter out false signals.",
                target="info-max-signals",
                placement="right"
            ),
        ], width=3),
    ], className="mb-3"),
    
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Label("Display Zones:"),
                html.I(className="bi bi-info-circle ms-1", id="info-zones", style={'cursor': 'pointer', 'color': '#6c757d'}),
            ], style={'display': 'flex', 'alignItems': 'center'}),
            dcc.Checklist(id='zone-display-checklist', options=[
                {'label': ' Below MA (Red)', 'value': 'below_ma'},
                {'label': ' Entry-to-Reentry Complete (Green)', 'value': 'complete_zone'},
                {'label': ' Entry-to-Reentry Incomplete (Orange)', 'value': 'incomplete_zone'}
            ], value=['complete_zone'], inline=True, style={'marginTop': '5px'}),
            dbc.Tooltip(
                "Colored background zones on the chart. Below MA (red): all periods below moving average. "
                "Entry-to-Reentry Complete (green): zones from exit signal to successful re-entry signal. "
                "Entry-to-Reentry Incomplete (orange): zones from exit signal where re-entry hasn't occurred yet.",
                target="info-zones",
                placement="right"
            ),
        ], width=12),
    ], className="mb-4"),

    # Store for target date (hidden)
    dcc.Store(id='target-date-store'),

    # Main chart with bottom margin to separate from content below
    dcc.Graph(id='stock-chart', style={'height': '120vh', 'marginBottom': '5rem'}),
    
    # Relative Strength Section - wrapped in div with extra spacing
    html.Div([
        html.Hr(style={'marginTop': '2rem', 'marginBottom': '3rem'}),
        html.H3("Relative Strength Analysis", style={'textAlign': 'center', 'marginBottom': '2rem'}),
        
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Label("Filter by Metric:", style={'fontWeight': 'bold'}),
                    html.I(className="bi bi-info-circle ms-1", id="info-rs-filter", style={'cursor': 'pointer', 'color': '#6c757d'}),
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '0.5rem'}),
                dcc.Dropdown(
                    id='rs-filter-dropdown',
                    options=[
                        {'label': 'All Tickers', 'value': 'all'},
                        {'label': '6M Performance > 0%', 'value': '6m_positive'},
                        {'label': '12M Performance > 0%', 'value': '12m_positive'},
                        {'label': 'Avg Performance > 0%', 'value': 'avg_positive'},
                        {'label': 'Levy RS > 0%', 'value': 'levy_positive'},
                        {'label': '6M Performance < 0%', 'value': '6m_negative'},
                        {'label': '12M Performance < 0%', 'value': '12m_negative'},
                    ],
                    value='all',
                    style={'width': '100%'}
                ),
                dbc.Tooltip(
                    "Filter the ticker list based on performance metrics. "
                    "Show only tickers that meet the selected criteria.",
                    target="info-rs-filter",
                    placement="right"
                ),
            ], width=6),
        ], className="mb-4"),
        
        html.Div(id='relative-strength-table'),
    ], style={'paddingTop': '3rem'}),
    
], fluid=True, className="p-4")


@app.callback(
    Output('target-date-store', 'data'),
    Input('stock-chart', 'relayoutData'),
    prevent_initial_call=True
)
def update_target_date(relayout_data):
    """Extract the rightmost visible date from chart interactions (slider, zoom, pan)"""
    if relayout_data is None:
        return None
    
    # Debug: print what we're receiving
    print(f"DEBUG relayoutData keys: {relayout_data.keys()}")
    
    # Check for range changes from slider or zoom/pan
    # These are the different ways the range can be updated:
    
    # Method 1: Direct xaxis.range update (from slider)
    if 'xaxis.range[1]' in relayout_data:
        target_date = relayout_data['xaxis.range[1]']
        print(f"DEBUG: Range from xaxis.range[1]: {target_date}")
        return target_date
    
    # Method 2: xaxis.range as array (from zoom/pan)
    if 'xaxis.range' in relayout_data and len(relayout_data['xaxis.range']) > 1:
        target_date = relayout_data['xaxis.range'][1]
        print(f"DEBUG: Range from xaxis.range: {target_date}")
        return target_date
    
    # Method 3: Check for xaxis3.range (bottom subplot with rangeslider)
    if 'xaxis3.range[1]' in relayout_data:
        target_date = relayout_data['xaxis3.range[1]']
        print(f"DEBUG: Range from xaxis3.range[1]: {target_date}")
        return target_date
    
    if 'xaxis3.range' in relayout_data and len(relayout_data['xaxis3.range']) > 1:
        target_date = relayout_data['xaxis3.range'][1]
        print(f"DEBUG: Range from xaxis3.range: {target_date}")
        return target_date
    
    # Method 4: Check for autosize or other layout changes
    if 'autosize' in relayout_data or 'width' in relayout_data or 'height' in relayout_data:
        # Layout resize - don't update date
        return None
    
    print(f"DEBUG: No range found in relayoutData")
    return None


@app.callback(
    Output('relative-strength-table', 'children'),
    [Input('ticker-dropdown', 'value'),
     Input('rs-filter-dropdown', 'value'),
     Input('target-date-store', 'data')]
)
def update_relative_strength_table(selected_ticker, filter_value, target_date):
    """Update the relative strength comparison table"""
    
    # Convert target_date string to pandas Timestamp if provided
    target_date_ts = None
    if target_date:
        try:
            target_date_ts = pd.Timestamp(target_date)
        except:
            target_date_ts = None
    
    # Get metrics for all tickers
    metrics_df = get_all_tickers_metrics(ticker_data, target_date=target_date_ts)
    
    # Apply filter
    if filter_value == '6m_positive':
        metrics_df = metrics_df[metrics_df['6M Performance (%)'] > 0]
    elif filter_value == '12m_positive':
        metrics_df = metrics_df[metrics_df['12M Performance (%)'] > 0]
    elif filter_value == 'avg_positive':
        metrics_df = metrics_df[metrics_df['Avg Performance (%)'] > 0]
    elif filter_value == 'levy_positive':
        metrics_df = metrics_df[metrics_df['Levy RS (%)'] > 0]
    elif filter_value == '6m_negative':
        metrics_df = metrics_df[metrics_df['6M Performance (%)'] < 0]
    elif filter_value == '12m_negative':
        metrics_df = metrics_df[metrics_df['12M Performance (%)'] < 0]
    
    # Sort by average performance (descending)
    metrics_df = metrics_df.sort_values('Avg Performance (%)', ascending=False)
    
    # Add ticker names
    metrics_df['Ticker Name'] = metrics_df['ticker'].map(tickers_dict)
    metrics_df = metrics_df[['ticker', 'Ticker Name', '6M Performance (%)', 
                              '12M Performance (%)', 'Avg Performance (%)', 'Levy RS (%)']]
    
    # Create conditional styling based on selected ticker
    style_data_conditional = [
        {
            'if': {'row_index': i},
            'backgroundColor': 'rgba(173, 216, 230, 0.3)'  # Light blue for selected ticker
        }
        for i, ticker in enumerate(metrics_df['ticker']) if ticker == selected_ticker
    ]
    
    # Add color coding for positive/negative values
    for col in ['6M Performance (%)', '12M Performance (%)', 'Avg Performance (%)', 'Levy RS (%)']:
        style_data_conditional.extend([
            {
                'if': {
                    'filter_query': f'{{{col}}} > 0',
                    'column_id': col
                },
                'color': 'green'
            },
            {
                'if': {
                    'filter_query': f'{{{col}}} < 0',
                    'column_id': col
                },
                'color': 'red'
            }
        ])
    
    # Create the DataTable
    table = dash_table.DataTable(
        data=metrics_df.to_dict('records'),
        columns=[
            {'name': 'Ticker', 'id': 'ticker'},
            {'name': 'Name', 'id': 'Ticker Name'},
            {'name': '6M Perf (%)', 'id': '6M Performance (%)', 'type': 'numeric', 'format': {'specifier': '.2f'}},
            {'name': '12M Perf (%)', 'id': '12M Performance (%)', 'type': 'numeric', 'format': {'specifier': '.2f'}},
            {'name': 'Avg Perf (%)', 'id': 'Avg Performance (%)', 'type': 'numeric', 'format': {'specifier': '.2f'}},
            {'name': 'Levy RS (%)', 'id': 'Levy RS (%)', 'type': 'numeric', 'format': {'specifier': '.2f'}},
        ],
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'fontFamily': 'Arial, sans-serif'
        },
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold',
            'textAlign': 'center'
        },
        style_data_conditional=style_data_conditional,
        style_table={'overflowX': 'auto'},
        sort_action='native',
        filter_action='native',
    )
    
    date_info = ""
    if target_date_ts:
        date_info = f" (as of {target_date_ts.strftime('%Y-%m-%d')})"
    
    return html.Div([
        html.H5(f"Relative Strength Metrics{date_info}", style={'marginBottom': '1rem'}),
        table
    ])


@app.callback(
    [Output('stock-chart', 'figure'), Output('ticker-name', 'children')],
    [Input('ticker-dropdown', 'value'), Input('period-selector', 'value'),
     Input('ma-period-selector', 'value'), Input('scale-selector', 'value'),
     Input('flat-threshold-840', 'value'), Input('flat-threshold-420', 'value'),
     Input('signal-checklist', 'value'), Input('bb-distance-threshold', 'value'),
     Input('zone-display-checklist', 'value'), Input('smoothing-window', 'value'),
     Input('ma-condition-threshold', 'value'), Input('daily-lookahead', 'value'),
     Input('max-reentry-signals', 'value')]
)
def update_chart(selected_ticker, period, ma_period, scale, flat_threshold_840, flat_threshold_420, 
                enabled_signals, bb_distance_threshold, display_zones, smoothing_window, 
                ma_condition_threshold, daily_lookahead, max_reentry_signals):
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
        
        # Defaults
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
        max_reentry_signals = max_reentry_signals if max_reentry_signals is not None else 1
        
        # MA/BB windows
        if ma_period == '20m10m':
            long_window, short_window, period_label = 420, 210, "20M/10M"
        else:
            long_window, short_window, period_label = 840, 420, "40M/20M"
        
        # Resample price data
        if period == 'quarterly':
            display_data = data.resample('QE').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
            display_label = "Quarterly"
            display_data['original_date'] = display_data.index
            display_data.index = display_data.index - pd.Timedelta(days=45)
        elif period == 'monthly':
            display_data = data.resample('ME').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
            display_label = "Monthly"
            display_data['original_date'] = display_data.index
            display_data.index = display_data.index - pd.Timedelta(days=15)
        else:
            display_data = data[['Open','High','Low','Close']].copy()
            display_label = "Daily"
        
        # Clean display data
        display_data = display_data.dropna()
        display_data = display_data[display_data.index.notnull()]
        display_data = display_data[display_data.index <= data.index[-1]]
        display_data = display_data[display_data.index >= '2000-01-01']
        
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
        
        ma_long_filt = ma_long_values[(ma_long_values.index >= start) & (ma_long_values.index <= end)]
        
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
        
        # Detect re-entry signals using refactored module
        reentry_signals = detect_reentry_signals(
            data, ma_long_values, bb_long_values, 
            enabled_signals, bb_distance_threshold
        )
        
        # Calculate MA conditions
        flat_long = ma_long_change < flat_threshold_840
        decreasing_short = ma_short_change < flat_threshold_420
        combined_ma_condition = flat_long & decreasing_short
        
        # Exit conditions - detect price crossings
        if period in ['monthly', 'quarterly'] and 'original_date' in display_data.columns:
            period_end_dates = display_data['original_date']
        else:
            period_end_dates = display_data.index
            
        ma_at_period_dates = ma_long_values.reindex(period_end_dates, method='nearest')
        ma_at_period_dates.index = display_data.index
        
        if period == 'daily':
            price_crossing = detect_price_crossing_down_daily(
                display_data, ma_long_values, smoothing_window=smoothing_window
            )
            
            # Apply MA condition threshold if lookahead > 0
            if daily_lookahead > 0 and price_crossing.sum() > 0:
                crossing_dates = display_data.index[price_crossing == 1]
                valid_crossings = pd.Series(0, index=display_data.index, dtype=float)
                
                for cross_date in crossing_dates:
                    lookahead_end = cross_date + pd.Timedelta(days=daily_lookahead)
                    
                    conditions_met, pct, days_met, total_days = check_ma_conditions_for_period(
                        lookahead_end, cross_date, data, combined_ma_condition, 
                        threshold=ma_condition_threshold
                    )
                    
                    if total_days > 0 and conditions_met:
                        valid_crossings.loc[cross_date] = 1
                    elif total_days == 0:
                        valid_crossings.loc[cross_date] = 1
                
                price_crossing = valid_crossings
        else:
            # Debug MA alignment for monthly/quarterly
            print(f"\n=== MA ALIGNMENT DEBUG ({period}) ===")
            print(f"display_data index (first 5): {display_data.index[:5].tolist()}")
            print(f"display_data Open (first 5): {display_data['Open'][:5].tolist()}")
            print(f"display_data Close (first 5): {display_data['Close'][:5].tolist()}")
            if 'original_date' in display_data.columns:
                print(f"original_date (first 5): {display_data['original_date'][:5].tolist()}")
                print(f"period_end_dates (first 5): {period_end_dates[:5].tolist()}")
            print(f"ma_at_period_dates index (first 5): {ma_at_period_dates.index[:5].tolist()}")
            print(f"ma_at_period_dates values (first 5): {ma_at_period_dates[:5].tolist()}")
            
            # Check if indices match
            indices_match = (display_data.index == ma_at_period_dates.index).all()
            print(f"\nIndices match: {indices_match}")
            
            # Check sample comparisons
            print(f"\nSample comparisons (first 10 periods):")
            for i in range(min(10, len(display_data))):
                d_open = display_data['Open'].iloc[i]
                d_close = display_data['Close'].iloc[i]
                ma_val = ma_at_period_dates.iloc[i]
                crosses = (d_open >= ma_val and d_close < ma_val)
                period_date = display_data.index[i]
                print(f"  {period_date.date()}: Open={d_open:.2f}, Close={d_close:.2f}, MA={ma_val:.2f}, Crosses={crosses}")
            
            # Count how many periods meet the crossing condition
            crossing_count = ((display_data['Open'] >= ma_at_period_dates) & (display_data['Close'] < ma_at_period_dates)).sum()
            print(f"\nTotal periods with Open >= MA and Close < MA: {crossing_count}")
            
            price_crossing = detect_price_crossing_down_period(display_data, ma_at_period_dates)
        
        # For monthly/quarterly: filter crossings by MA conditions
        if period in ['monthly', 'quarterly'] and price_crossing.sum() > 0:
            crossing_dates = display_data.index[price_crossing == 1]
            valid_crossings = pd.Series(0, index=display_data.index, dtype=float)
            
            print(f"\n=== FILTERING CROSSINGS BY MA CONDITIONS ===")
            print(f"Found {len(crossing_dates)} initial crossings, checking MA conditions (threshold={ma_condition_threshold:.0%}):")
            
            for cross_date in crossing_dates:
                if 'original_date' in display_data.columns:
                    original_cross_date = display_data.loc[cross_date, 'original_date']
                else:
                    original_cross_date = cross_date
                
                if period == 'quarterly':
                    period_start = pd.Timestamp(original_cross_date.year, ((original_cross_date.month - 1) // 3) * 3 + 1, 1)
                else:
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
                    status = '✓ ACCEPTED' if conditions_met else '✗ REJECTED'
                    print(f"  {original_cross_date.date()} (crossing on {crossing_day.date()}, checked {crossing_day.date()} to {original_cross_date.date()}): "
                          f"MA conditions {days_met}/{total_days} days ({pct:.1%}) - {status}")
                else:
                    # Fallback: check the entire period if we can't find exact crossing day
                    conditions_met, pct, days_met, total_days = check_ma_conditions_for_period(
                        original_cross_date, period_start, data, combined_ma_condition, 
                        threshold=ma_condition_threshold
                    )
                    status = '✓ ACCEPTED' if conditions_met else '✗ REJECTED'
                    print(f"  {original_cross_date.date()} (period: {period_start.date()} to {original_cross_date.date()}, no exact crossing day found): "
                          f"MA conditions {days_met}/{total_days} days ({pct:.1%}) - {status}")
                
                if conditions_met:
                    valid_crossings.loc[cross_date] = 1
            
            print(f"Crossings after MA filter: {valid_crossings.sum()} (rejected {len(crossing_dates) - valid_crossings.sum()})")
            price_crossing = valid_crossings
        
        # Identify entry zones
        print(f"\n=== ZONE DETECTION DEBUG ({selected_ticker}, {period}) ===")
        print(f"Price crossings: {price_crossing.sum()}")
        if price_crossing.sum() > 0:
            crossing_dates = display_data.index[price_crossing == 1]
            print(f"Crossing dates: {[d.date() for d in crossing_dates[:5]]}")
        
        print(f"Re-entry signals: {reentry_signals.sum()}")
        if reentry_signals.sum() > 0:
            reentry_dates = data.index[reentry_signals]
            print(f"Re-entry dates: {[d.date() for d in reentry_dates[:5]]}")
        
        print(f"Days below MA: {(data['Close'] < ma_long_values).sum()}")
        print(f"Days with MA conditions: {combined_ma_condition.sum()}")
        
        entry_zones = identify_entry_zones_with_conditions(
            data, display_data, ma_long_values, reentry_signals, 
            price_crossing, combined_ma_condition,
            ma_condition_threshold=ma_condition_threshold, period=period,
            max_reentry_signals=max_reentry_signals
        )
        
        print(f"DEBUG: Total entry zones found: {len(entry_zones)}")
        if len(entry_zones) > 0:
            for i, zone in enumerate(entry_zones[:3]):
                print(f"  Zone {i+1}: {zone['start'].date()} to {zone['end'].date()}, completed={zone['completed']}")
        else:
            print(f"  NO ZONES FOUND - investigating why...")
            if price_crossing.sum() == 0:
                print(f"    Reason: No price crossings detected")
            elif reentry_signals.sum() == 0:
                print(f"    Reason: No re-entry signals detected")
            elif (data['Close'] < ma_long_values).sum() == 0:
                print(f"    Reason: Price never below MA")
            elif combined_ma_condition.sum() == 0:
                print(f"    Reason: MA conditions never met")
        
        # Plot
        plotter = Plotter()
        fig = plotter.plot_candlestick(display_data, name=selected_ticker)
        
        plotter.add_moving_average(ma_long_filt)
        plotter.add_bollinger_bands(bb_long_filt, name_prefix=f'BB {period_label.split("/")[0]}', dashed=False)
        plotter.add_bollinger_bands(bb_short_filt, name_prefix=f'BB {period_label.split("/")[1]}', dashed=True)
        
        ticker_name = tickers_dict.get(selected_ticker, selected_ticker)
        long_name, short_name = period_label.split('/')
        
        # Create subplots
        fig_with_bandwidth = make_subplots(
            rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.1, 
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=(
                f"{ticker_name} ({display_label} Candles, {period_label} MA/BB)", 
                f"Band Width ({long_name} BB)", 
                "Exit Signals: MA Change & Price Crossing"
            ),
            specs=[[{"secondary_y": False}], [{"secondary_y": False}], [{"secondary_y": False}]]
        )
        
        for trace in plotter.fig.data:
            fig_with_bandwidth.add_trace(trace, row=1, col=1)
        
        # Add zones
        y_min = max(0, bb_long_filt['lower'].min() * 0.9) if len(bb_long_filt['lower']) > 0 else 0
        
        for zone in entry_zones:
            zone_data = data.loc[zone['start']:zone['end']]
            
            if zone['completed'] and 'complete_zone' in display_zones:
                fig_with_bandwidth.add_trace(
                    go.Scatter(x=zone_data.index, y=[y_min]*len(zone_data), mode='lines', 
                              line=dict(width=0), showlegend=False, hoverinfo='skip'), 
                    row=1, col=1
                )
                fig_with_bandwidth.add_trace(
                    go.Scatter(x=zone_data.index, y=zone_data['Close'], mode='lines', 
                              fill='tonexty', fillcolor='rgba(100,200,100,0.3)', 
                              line=dict(width=0), name='Complete Zone', showlegend=False, 
                              hoverinfo='skip'), 
                    row=1, col=1
                )
            elif not zone['completed'] and 'incomplete_zone' in display_zones:
                fig_with_bandwidth.add_trace(
                    go.Scatter(x=zone_data.index, y=[y_min]*len(zone_data), mode='lines', 
                              line=dict(width=0), showlegend=False, hoverinfo='skip'), 
                    row=1, col=1
                )
                fig_with_bandwidth.add_trace(
                    go.Scatter(x=zone_data.index, y=zone_data['Close'], mode='lines', 
                              fill='tonexty', fillcolor='rgba(255,200,100,0.3)', 
                              line=dict(width=0), name='Incomplete Zone', showlegend=False, 
                              hoverinfo='skip'), 
                    row=1, col=1
                )
        
        if 'below_ma' in display_zones:
            is_below = data['Close'] < ma_long_values
            segment_id = (is_below != is_below.shift(1)).cumsum().fillna(0)
            segments_df = pd.DataFrame({'Close': data['Close'], 'is_below': is_below, 'segment': segment_id})
            for name, group in segments_df.groupby('segment'):
                if len(group) >= 2 and group['is_below'].mean() > 0.5:
                    fig_with_bandwidth.add_trace(
                        go.Scatter(x=group.index, y=[y_min]*len(group), mode='lines', 
                                  line=dict(width=0), showlegend=False, hoverinfo='skip'), 
                        row=1, col=1
                    )
                    fig_with_bandwidth.add_trace(
                        go.Scatter(x=group.index, y=group['Close'], mode='lines', 
                                  fill='tonexty', fillcolor='rgba(255,0,0,0.2)', 
                                  line=dict(width=0), showlegend=False, hoverinfo='skip'), 
                        row=1, col=1
                    )
        
        # Re-entry signals
        reentry_dates = data.index[reentry_signals]
        reentry_prices = data.loc[reentry_signals, 'Low'] * 0.98
        if len(reentry_dates) > 0:
            fig_with_bandwidth.add_trace(
                go.Scatter(x=reentry_dates, y=reentry_prices, mode='markers',
                          marker=dict(symbol='triangle-up', size=12, color='green', 
                                     line=dict(color='darkgreen', width=1)),
                          name='Re-Entry Signal'), 
                row=1, col=1
            )
        
        # BandWidth
        fig_with_bandwidth.add_trace(
            go.Scatter(x=data.index, y=bandwidth_long, name='BandWidth', 
                      line=dict(color='darkblue', width=2)), 
            row=2, col=1
        )
        fig_with_bandwidth.add_hline(
            y=bandwidth_long.mean(), line_dash="dash", line_color="gray", 
            opacity=0.5, row=2, col=1
        )
        
        # MA changes
        fig_with_bandwidth.add_trace(
            go.Scatter(x=data.index, y=ma_long_change, name=f'MA {long_name} Change', 
                      line=dict(color='red', width=2)), 
            row=3, col=1
        )
        fig_with_bandwidth.add_trace(
            go.Scatter(x=data.index, y=ma_short_change, name=f'MA {short_name} Change', 
                      line=dict(color='green', width=2)), 
            row=3, col=1
        )
        
        # Price crossings
        for cross_date in display_data.index[price_crossing == 1]:
            fig_with_bandwidth.add_vline(
                x=cross_date, line_width=2, line_dash="solid", 
                line_color="darkgrey", opacity=0.7, row=3, col=1
            )
        
        # MA condition shading
        combined_segment_id = (combined_ma_condition != combined_ma_condition.shift(1)).cumsum()
        combined_df = pd.DataFrame({
            'combined': combined_ma_condition, 
            'segment': combined_segment_id, 
            'date': data.index
        })
        for name, group in combined_df.groupby('segment'):
            if len(group) > 0 and group['combined'].iloc[0]:
                fig_with_bandwidth.add_vrect(
                    x0=group['date'].iloc[0], x1=group['date'].iloc[-1], 
                    fillcolor="rgba(200,200,200,0.3)", layer="below", 
                    line_width=0, row=3, col=1
                )
        
        # Zero line and thresholds
        fig_with_bandwidth.add_hline(y=0, line_dash="solid", line_color="black", 
                                     opacity=1, line_width=2, row=3, col=1)
        fig_with_bandwidth.add_hline(y=flat_threshold_840, line_dash="dash", 
                                     line_color="red", opacity=0.5, row=3, col=1)
        fig_with_bandwidth.add_hline(y=flat_threshold_420, line_dash="dash", 
                                     line_color="green", opacity=0.5, row=3, col=1)
        
        # Annotations
        annotation_x_date = data.index[int(len(data) * 0.02)]
        
        fig_with_bandwidth.add_annotation(
            text=f"Flat {long_name}: < {flat_threshold_840}%", 
            xref="x3", yref="paper",
            x=annotation_x_date, y=0.22,
            xanchor="left", yanchor="top",
            showarrow=False, 
            bgcolor="rgba(255,255,255,0.9)", 
            bordercolor="red", borderwidth=1, 
            font=dict(size=10, color="red")
        )
        fig_with_bandwidth.add_annotation(
            text=f"Decreasing {short_name}: < {flat_threshold_420}%", 
            xref="x3", yref="paper",
            x=annotation_x_date, y=0.19,
            xanchor="left", yanchor="top",
            showarrow=False, 
            bgcolor="rgba(255,255,255,0.9)", 
            bordercolor="green", borderwidth=1, 
            font=dict(size=10, color="green")
        )
        
        # Layout
        fig_with_bandwidth.update_layout(
            height=1200, 
            showlegend=True, 
            hovermode='closest',
            legend=dict(
                orientation="h", 
                yanchor="bottom", 
                y=1.05,
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
                    y=1.18,
                    yanchor="top"
                )
            )
        )
        
        # Custom x-axis formatting
        if period == 'quarterly':
            tick_vals = display_data.index.tolist()
            tick_text = format_quarter_labels_two_levels(display_data.index)
            fig_with_bandwidth.update_xaxes(
                tickmode='array', tickvals=tick_vals, ticktext=tick_text, 
                tickangle=0, row=1, col=1
            )
        elif period == 'monthly':
            tick_vals = display_data.index.tolist()
            tick_text = format_monthly_labels_as_quarters(display_data.index)
            fig_with_bandwidth.update_xaxes(
                tickmode='array', tickvals=tick_vals, ticktext=tick_text, 
                tickangle=0, row=1, col=1
            )
        
        fig_with_bandwidth.update_xaxes(row=1, col=1, rangeslider_visible=False, showticklabels=True)
        fig_with_bandwidth.update_xaxes(row=2, col=1, rangeslider_visible=False, showticklabels=True)
        fig_with_bandwidth.update_xaxes(title_text="Date", row=3, col=1, rangeslider_visible=True, showticklabels=True)
        
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