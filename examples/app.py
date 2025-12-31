"""
app.py - Enhanced with Data Management and Improved Layout
Drop-in replacement for your existing app.py

New improvements:
- Better spacing between charts and sections
- Professional theme (FLATLY - clean and modern)
- Consistent margins and padding
- Responsive layout that works in different browser sizes
"""

import dash
from dash import dcc, html, Input, Output, dash_table, State
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
from bollinger_bands.data.fetcher import DataFetcher
from bollinger_bands.data.storage_manager import DataStorageManager
from bollinger_bands.data.currency_converter import CurrencyConverter
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

# ============================================================================
# DATA MANAGEMENT SETUP
# ============================================================================

# Initialize storage manager and fetcher with caching
storage_manager = DataStorageManager('config/tickers.yaml')
fetcher = DataFetcher(storage_manager)

# Initialize currency converter
currency_converter = CurrencyConverter(
    storage_manager.config,
    cache_dir=storage_manager.config['data_settings'].get('currency_data_directory', 'data/currencies')
)

# Give converter to storage manager for USD normalization
storage_manager.currency_converter = currency_converter

# Load configuration from YAML
config = storage_manager.config
enabled_tickers = storage_manager.get_enabled_tickers()
tickers = [t['symbol'] for t in enabled_tickers]
tickers_dict = {t['symbol']: t['name'] for t in enabled_tickers}
ticker_currencies = storage_manager.get_ticker_currencies()

# Data loading with smart caching
ticker_data = {}
ticker_data_usd = {}
start_date = config['data_settings'].get('default_start_date', '2000-01-01')
now = datetime.datetime.now()
end_date = now.strftime('%Y-%m-%d')

print("="*80)
print("LOADING DATA WITH SMART CACHING (DUAL STORAGE)")
print("="*80)

auto_update = config['data_settings'].get('auto_update_on_startup', True)

if auto_update:
    print("Auto-update enabled: Fetching latest data (only missing dates)...")
    ticker_data = fetcher.update_all_tickers(end_date)
    ticker_data_usd = storage_manager.load_all_ticker_data(prefer_usd=True)
else:
    print("Auto-update disabled: Loading from cache...")
    for ticker in tickers:
        print(f"  {ticker}")
        try:
            data = fetcher.fetch_ohlc_data(ticker, start_date, end_date, use_cache=True)
            data.attrs['ticker'] = ticker
            ticker_data[ticker] = data
        except Exception as e:
            print(f"  ERROR loading {ticker}: {e}")
    ticker_data_usd = storage_manager.load_all_ticker_data(prefer_usd=True)

ticker_data_original = ticker_data

print(f"\n✓ Data loaded for {len(ticker_data)} tickers (original currency)!")
print(f"✓ USD-normalized data: {len(ticker_data_usd)} tickers")
print(f"✓ Currency mapping: {ticker_currencies}")
print("="*80)

# ============================================================================
# DASH APP SETUP - PROFESSIONAL THEME
# ============================================================================

# Using JOURNAL theme - Professional newspaper/publication style
# Clean, traditional, great for financial reports
app = dash.Dash(__name__, external_stylesheets=[
    dbc.themes.JOURNAL,  # Changed to JOURNAL for traditional professional look
    "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css"
])
load_figure_template("journal")  # Match the theme

# ============================================================================
# DATA MANAGEMENT UI COMPONENTS
# ============================================================================

data_management_card = dbc.Card([
    dbc.CardHeader([
        html.H5("📊 Data Management", className="mb-0"),
    ]),
    dbc.CardBody([
        dbc.Row([
            dbc.Col([
                html.Label("Data Status:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                html.Div(id='data-status', style={'fontSize': '14px'})
            ], width=6),
            dbc.Col([
                html.Div([
                    dbc.Button(
                        [html.I(className="bi bi-arrow-clockwise me-2"), "Update Data"],
                        id='update-data-btn',
                        color='primary',
                        size='sm',
                        className='me-2'
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-info-circle me-2"), "Details"],
                        id='view-details-btn',
                        color='secondary',
                        size='sm',
                        outline=True
                    ),
                ], style={'textAlign': 'right'})
            ], width=6),
        ]),
        dbc.Row([
            dbc.Col([
                html.Div(id='update-status', style={'marginTop': '10px', 'fontSize': '14px'})
            ], width=12)
        ])
    ])
], className="mb-3")

data_details_modal = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("📋 Stored Data Details")),
    dbc.ModalBody(id='data-details-content'),
    dbc.ModalFooter(
        dbc.Button("Close", id="close-details-modal", className="ms-auto")
    ),
], id="data-details-modal", size="xl", is_open=False)

# ============================================================================
# APP LAYOUT - IMPROVED SPACING
# ============================================================================

app.layout = dbc.Container([
    # Header with more breathing room
    html.H1("Stock Chart with Bollinger Bands & Trading Signals", 
            style={'textAlign': 'center', 'marginTop': '20px', 'marginBottom': '10px'}),
    html.H2(id='ticker-name', 
            style={'textAlign': 'center', 'marginBottom': '30px'}),
    
    # Data Management Section
    data_management_card,
    data_details_modal,
    dcc.Store(id='update-trigger', data=0),
    
    # Original Controls with improved spacing
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Label("Select Ticker:"),
                html.I(className="bi bi-info-circle ms-1", id="info-ticker", style={'cursor': 'pointer', 'color': '#6c757d'}),
            ], style={'display': 'flex', 'alignItems': 'center'}),
            dcc.Dropdown(id='ticker-dropdown', options=[{'label': t, 'value': t} for t in tickers], value=tickers[0] if tickers else 'EEM'),
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
                {'label': ' Exit-to-Reentry Candlestick (Green)', 'value': 'complete_zone'},
                {'label': ' Exit-to-Reentry MA crossing (Orange)', 'value': 'incomplete_zone'}
            ], value=['complete_zone', 'incomplete_zone'], inline=True, style={'marginTop': '5px'}),
            dbc.Tooltip(
                "Colored background zones on the chart. Below MA (red): all periods below moving average. "
                "Exit-to-Reentry Candlestick (green): zones from exit signal to candlestick re-entry signal. "
                "Exit-to-Reentry MA crossing (orange): zones from exit signal to MA crossing re-entry.",
                target="info-zones",
                placement="right"
            ),
        ], width=8),
        dbc.Col([
            html.Div([
                html.Label("Trading Strategy:"),
                html.I(className="bi bi-info-circle ms-1", id="info-strategy", style={'cursor': 'pointer', 'color': '#6c757d'}),
            ], style={'display': 'flex', 'alignItems': 'center'}),
            dcc.RadioItems(id='strategy-selector', options=[
                {'label': ' Candlesticks only (Green)', 'value': 'green'},
                {'label': ' MA crossing + Candlestick (Orange and green)', 'value': 'orange'}
            ], value='orange', inline=True, style={'marginTop': '5px'}),
            dbc.Tooltip(
                "Candlesticks only (Green): Re-enter only at candlestick signals (conservative). "
                "MA crossing + Candlestick (Orange and green): Re-enter at either MA crossing (orange zones) or candlestick signal (green zones), whichever comes first (aggressive).",
                target="info-strategy",
                placement="right"
            ),
        ], width=4),
    ], className="mb-5"),  # Increased bottom margin before chart

    # Store for target date (hidden)
    dcc.Store(id='target-date-store'),

    # Main chart with improved spacing
    html.Div([
        dcc.Graph(id='stock-chart', style={'height': '120vh'}),
    ], style={'marginBottom': '80px'}),  # Fixed spacing after chart
    
    # Relative Strength Section with clear separation
    html.Div([
        html.Hr(style={
            'marginTop': '0px',
            'marginBottom': '50px',
            'borderTop': '2px solid #dee2e6'
        }),
        html.H3("Relative Strength Analysis", 
                style={
                    'textAlign': 'center', 
                    'marginBottom': '30px',
                    'fontWeight': '600'
                }),
        
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Label("Reference Ticker (Benchmark):", style={'fontWeight': 'bold'}),
                    html.I(className="bi bi-info-circle ms-1", id="info-rs-reference", style={'cursor': 'pointer', 'color': '#6c757d'}),
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '0.5rem'}),
                dcc.Dropdown(
                    id='rs-reference-dropdown',
                    options=[{'label': tickers_dict.get(t, t), 'value': t} for t in tickers],
                    value='URTH',
                    style={'width': '100%'}
                ),
                dbc.Tooltip(
                    "Select benchmark ticker for Levy RS calculation. "
                    "Levy RS shows how much each ticker outperforms (positive) or underperforms (negative) the benchmark. "
                    "The benchmark itself will show 0% Levy RS.",
                    target="info-rs-reference",
                    placement="right"
                ),
            ], width=4),
            dbc.Col([
                html.Div([
                    html.Label("Calculation Currency:", style={'fontWeight': 'bold'}),
                    html.I(className="bi bi-info-circle ms-1", id="info-rs-currency", style={'cursor': 'pointer', 'color': '#6c757d'}),
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '0.5rem'}),
                dcc.Dropdown(
                    id='rs-calculation-currency-dropdown',
                    options=[
                        {'label': 'USD (US Dollar)', 'value': 'USD'},
                        {'label': 'CHF (Swiss Franc)', 'value': 'CHF'},
                        {'label': 'EUR (Euro)', 'value': 'EUR'},
                        {'label': 'GBP (British Pound)', 'value': 'GBP'},
                    ],
                    value='USD',
                    style={'width': '100%'}
                ),
                dbc.Tooltip(
                    "Currency for calculating all performance metrics. "
                    "All tickers will be converted to this currency before calculating returns. "
                    "Use this to compare CHF-based assets (like SMI) with USD-based assets fairly.",
                    target="info-rs-currency",
                    placement="right"
                ),
            ], width=4),
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
            ], width=4),
        ], className="mb-4"),
        
        html.Div(id='relative-strength-table'),
    ], style={
        'paddingTop': '0px',
        'paddingBottom': '50px'
    }),
    
], fluid=True, className="p-4", style={'paddingBottom': '100px'})  # Extra padding at bottom of page

# ============================================================================
# ALL CALLBACKS - UNCHANGED FROM ORIGINAL
# ============================================================================

@app.callback(
    Output('data-status', 'children'),
    Input('update-trigger', 'data')
)
def update_data_status(_):
    """Display current data status."""
    try:
        info_df = storage_manager.get_all_data_info()
        
        if info_df.empty:
            return html.Span("⚠️ No data loaded", style={'color': 'red'})
        
        ok_count = (info_df['status'] == 'OK').sum()
        total_count = len(info_df)
        
        if 'end_date' in info_df.columns:
            dates = pd.to_datetime(info_df['end_date'], errors='coerce')
            latest_date = dates.max()
            if pd.notna(latest_date):
                days_old = (datetime.datetime.now() - latest_date).days
                if days_old == 0:
                    date_status = f"Latest: {latest_date.strftime('%Y-%m-%d')} (today)"
                elif days_old == 1:
                    date_status = f"Latest: {latest_date.strftime('%Y-%m-%d')} (yesterday)"
                else:
                    date_status = f"Latest: {latest_date.strftime('%Y-%m-%d')} ({days_old} days old)"
            else:
                date_status = "No date info"
        else:
            date_status = "No date info"
        
        status_color = 'green' if ok_count == total_count else 'orange'
        
        return html.Div([
            html.Span(f"✓ {ok_count}/{total_count} tickers loaded", 
                     style={'color': status_color, 'fontWeight': 'bold'}),
            html.Br(),
            html.Small(date_status, style={'color': 'gray'})
        ])
    except Exception as e:
        return html.Span(f"⚠️ Error: {str(e)}", style={'color': 'red'})


@app.callback(
    [Output('update-status', 'children'),
     Output('update-trigger', 'data')],
    Input('update-data-btn', 'n_clicks'),
    State('update-trigger', 'data'),
    prevent_initial_call=True
)
def update_data_button(n_clicks, current_trigger):
    """Handle data update button click."""
    if n_clicks is None or n_clicks == 0:
        return "", current_trigger
    
    try:
        end_date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        global ticker_data
        print("\n" + "="*80)
        print("MANUAL DATA UPDATE TRIGGERED")
        print("="*80)
        ticker_data = fetcher.update_all_tickers(end_date)
        print("="*80)
        
        return html.Span("✓ Data updated successfully!", 
                        style={'color': '#28a745', 'fontWeight': 'bold'}), current_trigger + 1
    except Exception as e:
        return html.Span(f"✗ Update failed: {str(e)}", 
                        style={'color': '#dc3545', 'fontWeight': 'bold'}), current_trigger


@app.callback(
    [Output("data-details-modal", "is_open"),
     Output("data-details-content", "children")],
    [Input("view-details-btn", "n_clicks"),
     Input("close-details-modal", "n_clicks")],
    [State("data-details-modal", "is_open")],
)
def toggle_details_modal(n1, n2, is_open):
    """Toggle the data details modal."""
    if n1 or n2:
        if not is_open:
            info_df = storage_manager.get_all_data_info()
            
            table = dash_table.DataTable(
                data=info_df.to_dict('records'),
                columns=[{'name': col, 'id': col} for col in info_df.columns],
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px',
                    'fontSize': '12px',
                    'maxWidth': '200px',
                    'overflow': 'hidden',
                    'textOverflow': 'ellipsis',
                },
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold',
                    'textAlign': 'center'
                },
                style_data_conditional=[
                    {
                        'if': {'column_id': 'status', 'filter_query': '{status} = OK'},
                        'color': 'green',
                        'fontWeight': 'bold'
                    },
                    {
                        'if': {'column_id': 'status', 'filter_query': '{status} != OK'},
                        'color': 'red',
                        'fontWeight': 'bold'
                    }
                ],
                style_table={'overflowX': 'auto'},
                tooltip_data=[
                    {
                        column: {'value': str(value), 'type': 'markdown'}
                        for column, value in row.items()
                    } for row in info_df.to_dict('records')
                ],
                tooltip_duration=None,
            )
            return not is_open, table
        else:
            return not is_open, ""
    return is_open, ""


@app.callback(
    Output('target-date-store', 'data'),
    Input('stock-chart', 'relayoutData'),
    prevent_initial_call=True
)
def update_target_date(relayout_data):
    """Extract the rightmost visible date from chart interactions"""
    if relayout_data is None:
        return None
    
    if 'xaxis.range[1]' in relayout_data:
        return relayout_data['xaxis.range[1]']
    
    if 'xaxis.range' in relayout_data and len(relayout_data['xaxis.range']) > 1:
        return relayout_data['xaxis.range'][1]
    
    if 'xaxis3.range[1]' in relayout_data:
        return relayout_data['xaxis3.range[1]']
    
    if 'xaxis3.range' in relayout_data and len(relayout_data['xaxis3.range']) > 1:
        return relayout_data['xaxis3.range'][1]
    
    if 'autosize' in relayout_data or 'width' in relayout_data or 'height' in relayout_data:
        return None
    
    return None


@app.callback(
    Output('relative-strength-table', 'children'),
    [Input('ticker-dropdown', 'value'),
     Input('rs-filter-dropdown', 'value'),
     Input('rs-reference-dropdown', 'value'),
     Input('rs-calculation-currency-dropdown', 'value'),
     Input('target-date-store', 'data')]
)
def update_relative_strength_table(selected_ticker, filter_value, reference_ticker, 
                                   calculation_currency, target_date):
    """Update the relative strength comparison table with USD-normalized data"""
    
    target_date_ts = None
    if target_date:
        try:
            target_date_ts = pd.Timestamp(target_date)
        except:
            target_date_ts = None
    
    data_for_metrics = ticker_data_usd
    currency_note = ""
    
    if calculation_currency and calculation_currency != 'USD':
        try:
            print(f"\nConverting metrics from USD to {calculation_currency}...")
            
            data_for_metrics = {}
            for ticker, usd_data in ticker_data_usd.items():
                try:
                    converted = currency_converter.convert_ohlc_data(
                        usd_data.copy(),
                        from_currency='USD',
                        to_currency=calculation_currency,
                        use_cache=True
                    )
                    data_for_metrics[ticker] = converted
                except Exception as e:
                    print(f"  Warning: Could not convert {ticker}: {e}")
                    data_for_metrics[ticker] = usd_data.copy()
            
            currency_note = f" | Currency: {calculation_currency}"
            print(f"✓ Converted all tickers to {calculation_currency}")
            
        except Exception as e:
            print(f"✗ Conversion failed: {e}")
            import traceback
            traceback.print_exc()
            data_for_metrics = ticker_data_usd
            currency_note = " | Currency: USD (conversion failed)"
    else:
        print("Using USD-normalized data for metrics")
    
    metrics_df = get_all_tickers_metrics(data_for_metrics, reference_ticker=reference_ticker, target_date=target_date_ts)
    
    if filter_value == '6m_positive':
        metrics_df = metrics_df[metrics_df['6M Performance (%)'] > 0]
    elif filter_value == '12m_positive':
        metrics_df = metrics_df[metrics_df['12M Performance (%)'] > 0]
    elif filter_value == 'avg_positive':
        metrics_df = metrics_df[metrics_df['Avg Performance (%)'] > 0]
    elif filter_value == 'levy_positive':
        metrics_df = metrics_df[metrics_df['6M Perf Rel. Bench (%)'] > 0]
    elif filter_value == '6m_negative':
        metrics_df = metrics_df[metrics_df['6M Performance (%)'] < 0]
    elif filter_value == '12m_negative':
        metrics_df = metrics_df[metrics_df['12M Performance (%)'] < 0]
    
    metrics_df = metrics_df.sort_values('Avg Performance (%)', ascending=False)
    
    def truncate_name(name, max_length=25):
        if pd.isna(name):
            return name
        if len(name) > max_length:
            return name[:max_length-3] + '...'
        return name
    
    metrics_df['Ticker Name'] = metrics_df['ticker'].map(tickers_dict)
    metrics_df['Ticker Name Short'] = metrics_df['Ticker Name'].apply(lambda x: truncate_name(x, max_length=25))
    metrics_df['Ticker Name Full'] = metrics_df['Ticker Name']
    
    metrics_df = metrics_df[['ticker', 'Ticker Name Short', 'Ticker Name Full', '6M Performance (%)', 
                              '12M Performance (%)', 'Avg Performance (%)', 
                              'Levy RS (%)', '6M Perf Rel. Bench (%)']]
    
    # Styling: benchmark gets blue background (applied first)
    style_data_conditional = [
        {
            'if': {'row_index': i},
            'backgroundColor': 'rgba(173, 216, 230, 0.3)'  # Light blue for benchmark
        }
        for i, ticker in enumerate(metrics_df['ticker']) if ticker == reference_ticker
    ]
    
    # Selected ticker gets italics, bold, and yellow background (applied second, takes priority)
    style_data_conditional.extend([
        {
            'if': {'row_index': i},
            'fontStyle': 'italic',
            'fontWeight': 'bold',
            'backgroundColor': 'rgba(255, 255, 200, 0.3)'  # Light yellow for selected ticker
        }
        for i, ticker in enumerate(metrics_df['ticker']) if ticker == selected_ticker
    ])
    
    for col in ['6M Performance (%)', '12M Performance (%)', 'Avg Performance (%)', 
                'Levy RS (%)', '6M Perf Rel. Bench (%)']:
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
    
    table = dash_table.DataTable(
        data=metrics_df.to_dict('records'),
        columns=[
            {'name': 'Ticker', 'id': 'ticker'},
            {'name': 'Name', 'id': 'Ticker Name Short'},
            {'name': '6M Perf (%)', 'id': '6M Performance (%)', 'type': 'numeric', 'format': {'specifier': '.2f'}},
            {'name': '12M Perf (%)', 'id': '12M Performance (%)', 'type': 'numeric', 'format': {'specifier': '.2f'}},
            {'name': 'Avg Perf (%)', 'id': 'Avg Performance (%)', 'type': 'numeric', 'format': {'specifier': '.2f'}},
            {'name': 'Levy RS (%)', 'id': 'Levy RS (%)', 'type': 'numeric', 'format': {'specifier': '.2f'}},
            {'name': '6M Perf Rel. Bench (%)', 'id': '6M Perf Rel. Bench (%)', 'type': 'numeric', 'format': {'specifier': '.2f'}},
        ],
        tooltip_data=[
            {
                'Ticker Name Short': {'value': row['Ticker Name Full'], 'type': 'text'}
            }
            for row in metrics_df.to_dict('records')
        ],
        tooltip_duration=None,
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
    
    benchmark_name = tickers_dict.get(reference_ticker, reference_ticker)
    benchmark_info = f" | Benchmark: {benchmark_name}"
    
    return html.Div([
        html.H5(f"Relative Strength Metrics{date_info}{benchmark_info}{currency_note}", 
                style={'marginBottom': '1rem'}),
        html.P([
            html.Strong("Note:"), " ",
            "Metrics calculated using USD-normalized data for fair comparisons across currencies. ",
            "Charts use original currency data for accurate trading signals.",
        ], style={'fontSize': '12px', 'color': '#666', 'fontStyle': 'italic', 'marginBottom': '0.5rem'}),
        html.P([
            html.Strong("Levy RS (%)"), ": (Current Price / 6M MA) - 1. ",
            html.Strong("6M Perf Rel. Bench (%)"), f": (Asset return / {reference_ticker} return) - 1. ",
            f"Benchmark ({reference_ticker}) shows 0%. ",
            "Positive = outperformance. ",
            html.Em("All conversions go through USD hub.")
        ], style={'fontSize': '14px', 'color': '#666', 'marginBottom': '1rem'}),
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
     Input('max-reentry-signals', 'value'), Input('strategy-selector', 'value')]
)
def update_chart(selected_ticker, period, ma_period, scale, flat_threshold_840, flat_threshold_420, 
                enabled_signals, bb_distance_threshold, display_zones, smoothing_window, 
                ma_condition_threshold, daily_lookahead, max_reentry_signals, strategy):
    try:
        if selected_ticker is None:
            selected_ticker = tickers[0] if tickers else 'EEM'
        
        data = ticker_data_original.get(selected_ticker)
        if data is None:
            data = ticker_data.get(selected_ticker)
        
        if data is None:
            return go.Figure(), f"No data for {selected_ticker}"
        
        if 'ticker' not in data.attrs:
            data.attrs['ticker'] = selected_ticker
        
        original_currency = ticker_currencies.get(selected_ticker, 'USD')
        
        data = data.dropna()
        data = data[data.index.notnull()]
        data = data[data.index >= '2000-01-01']
        
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
        strategy = strategy or 'orange'
        
        if ma_period == '20m10m':
            long_window, short_window, period_label = 420, 210, "20M/10M"
        else:
            long_window, short_window, period_label = 840, 420, "40M/20M"
        
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
        
        display_data = display_data.dropna()
        display_data = display_data[display_data.index.notnull()]
        display_data = display_data[display_data.index <= data.index[-1]]
        display_data = display_data[display_data.index >= '2000-01-01']
        
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
        
        reentry_signals = detect_reentry_signals(
            data, ma_long_values, bb_long_values, 
            enabled_signals, bb_distance_threshold
        )
        
        flat_long = ma_long_change < flat_threshold_840
        decreasing_short = ma_short_change < flat_threshold_420
        combined_ma_condition = flat_long & decreasing_short
        
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
            price_crossing = detect_price_crossing_down_period(display_data, ma_at_period_dates)
        
        if period in ['monthly', 'quarterly'] and price_crossing.sum() > 0:
            crossing_dates = display_data.index[price_crossing == 1]
            valid_crossings = pd.Series(0, index=display_data.index, dtype=float)
            
            for cross_date in crossing_dates:
                if 'original_date' in display_data.columns:
                    original_cross_date = display_data.loc[cross_date, 'original_date']
                else:
                    original_cross_date = cross_date
                
                if period == 'quarterly':
                    period_start = pd.Timestamp(original_cross_date.year, ((original_cross_date.month - 1) // 3) * 3 + 1, 1)
                else:
                    period_start = pd.Timestamp(original_cross_date.year, original_cross_date.month, 1)
                
                period_mask = (data.index >= period_start) & (data.index <= original_cross_date)
                period_data = data[period_mask]
                
                is_below = period_data['Close'] < ma_long_values[period_mask]
                is_above = period_data['Close'] >= ma_long_values[period_mask]
                
                crossing_day = None
                for i in range(1, len(is_below)):
                    if is_above.iloc[i-1] and is_below.iloc[i]:
                        crossing_day = period_data.index[i]
                        break
                
                if crossing_day is not None:
                    conditions_met, pct, days_met, total_days = check_ma_conditions_for_period(
                        original_cross_date, crossing_day, data, combined_ma_condition, 
                        threshold=ma_condition_threshold
                    )
                else:
                    conditions_met, pct, days_met, total_days = check_ma_conditions_for_period(
                        original_cross_date, period_start, data, combined_ma_condition, 
                        threshold=ma_condition_threshold
                    )
                
                if conditions_met:
                    valid_crossings.loc[cross_date] = 1
            
            price_crossing = valid_crossings
        
        allow_reentry_at_ma = (strategy == 'orange')
        
        entry_zones = identify_entry_zones_with_conditions(
            data, display_data, ma_long_values, reentry_signals, 
            price_crossing, combined_ma_condition,
            ma_condition_threshold=ma_condition_threshold, period=period,
            max_reentry_signals=max_reentry_signals,
            allow_reentry_at_ma=allow_reentry_at_ma
        )
        
        plotter = Plotter()
        plotter.fig = go.Figure()
        
        out_of_market = pd.Series(False, index=display_data.index)
        for zone in entry_zones:
            zone_mask = (display_data.index >= zone['start']) & (display_data.index <= zone['end'])
            out_of_market = out_of_market | zone_mask
        
        in_market_data = display_data[~out_of_market]
        out_market_data = display_data[out_of_market]
        
        if len(in_market_data) > 0:
            plotter.fig.add_trace(go.Candlestick(
                x=in_market_data.index,
                open=in_market_data['Open'],
                high=in_market_data['High'],
                low=in_market_data['Low'],
                close=in_market_data['Close'],
                name='In Market',
                increasing_line_color='green',
                decreasing_line_color='red',
                showlegend=True
            ))
        
        if len(out_market_data) > 0:
            plotter.fig.add_trace(go.Candlestick(
                x=out_market_data.index,
                open=out_market_data['Open'],
                high=out_market_data['High'],
                low=out_market_data['Low'],
                close=out_market_data['Close'],
                name='Out of Market',
                increasing_line_color='rgba(0, 128, 0, 0.3)',
                decreasing_line_color='rgba(255, 0, 0, 0.3)',
                increasing_fillcolor='rgba(0, 128, 0, 0.1)',
                decreasing_fillcolor='rgba(255, 0, 0, 0.1)',
                showlegend=True
            ))
        
        plotter.add_moving_average(ma_long_filt)
        plotter.add_bollinger_bands(bb_long_filt, name_prefix=f'BB {period_label.split("/")[0]}', dashed=False)
        plotter.add_bollinger_bands(bb_short_filt, name_prefix=f'BB {period_label.split("/")[1]}', dashed=True)
        
        ticker_name = tickers_dict.get(selected_ticker, selected_ticker)
        if original_currency != 'USD':
            ticker_name += f" ({original_currency})"
        long_name, short_name = period_label.split('/')
        
        # IMPROVED SPACING: Increase vertical_spacing for better separation
        fig_with_bandwidth = make_subplots(
            rows=3, cols=1, shared_xaxes=True, 
            vertical_spacing=0.20,  # INCREASED from 0.15 for more breathing room
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=(
                f"{ticker_name} ({display_label} Candles, {period_label} MA/BB) - Shaded = Out of Market", 
                f"Band Width ({long_name} BB)", 
                "Exit Signals: MA Change & Price Crossing"
            ),
            specs=[[{"secondary_y": False}], [{"secondary_y": False}], [{"secondary_y": False}]]
        )
        
        for trace in plotter.fig.data:
            fig_with_bandwidth.add_trace(trace, row=1, col=1)
        
        y_min = max(0, bb_long_filt['lower'].min() * 0.9) if len(bb_long_filt['lower']) > 0 else 0
        
        for zone in entry_zones:
            zone_data = data.loc[zone['start']:zone['end']]
            
            if zone['type'] == 'green' and 'complete_zone' in display_zones:
                fig_with_bandwidth.add_trace(
                    go.Scatter(x=zone_data.index, y=[y_min]*len(zone_data), mode='lines', 
                              line=dict(width=0), showlegend=False, hoverinfo='skip'), 
                    row=1, col=1
                )
                fig_with_bandwidth.add_trace(
                    go.Scatter(x=zone_data.index, y=zone_data['Close'], mode='lines', 
                              fill='tonexty', fillcolor='rgba(100,200,100,0.3)', 
                              line=dict(width=0), name='Candlestick Zone', showlegend=False, 
                              hoverinfo='skip'), 
                    row=1, col=1
                )
            elif zone['type'] == 'orange' and 'incomplete_zone' in display_zones:
                fig_with_bandwidth.add_trace(
                    go.Scatter(x=zone_data.index, y=[y_min]*len(zone_data), mode='lines', 
                              line=dict(width=0), showlegend=False, hoverinfo='skip'), 
                    row=1, col=1
                )
                fig_with_bandwidth.add_trace(
                    go.Scatter(x=zone_data.index, y=zone_data['Close'], mode='lines', 
                              fill='tonexty', fillcolor='rgba(255,200,100,0.3)', 
                              line=dict(width=0), name='MA Crossing Zone', showlegend=False, 
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
        
        fig_with_bandwidth.add_trace(
            go.Scatter(x=data.index, y=bandwidth_long, name='BandWidth', 
                      line=dict(color='darkblue', width=2)), 
            row=2, col=1
        )
        fig_with_bandwidth.add_hline(
            y=bandwidth_long.mean(), line_dash="dash", line_color="gray", 
            opacity=0.5, row=2, col=1
        )
        
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
        
        for cross_date in display_data.index[price_crossing == 1]:
            fig_with_bandwidth.add_vline(
                x=cross_date, line_width=2, line_dash="solid", 
                line_color="darkgrey", opacity=0.7, row=3, col=1
            )
        
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
        
        fig_with_bandwidth.add_hline(y=0, line_dash="solid", line_color="black", 
                                     opacity=1, line_width=2, row=3, col=1)
        fig_with_bandwidth.add_hline(y=flat_threshold_840, line_dash="dash", 
                                     line_color="red", opacity=0.5, row=3, col=1)
        fig_with_bandwidth.add_hline(y=flat_threshold_420, line_dash="dash", 
                                     line_color="green", opacity=0.5, row=3, col=1)
        
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
        fig = plotter.plot_candlestick(ticker_data.get(selected_ticker, list(ticker_data.values())[0]), name=selected_ticker)
        return fig, f"Error: {selected_ticker}"


if __name__ == '__main__':
    app.run(debug=False, port=8050)