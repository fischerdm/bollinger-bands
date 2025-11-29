import dash
from dash import dcc, html, Input, Output
from bollinger_bands.data.fetcher import DataFetcher
from bollinger_bands.indicators.moving_average import MovingAverage
from bollinger_bands.indicators.bollinger_bands import BollingerBands
from bollinger_bands.visualization.plotter import Plotter
import datetime

# Sectores
# Financial Services
# Basic Materials
# Consumer Cyclical
# Real Estate
# Consumer Defensive
# Healthcare
# Utilities
# Communication Services

# Geographies
# Emerging Markets
# Asia
# Frontier Markets
# Global Markets

# Fetch data for multiple tickers (do this once at startup)
tickers = ['EEM', 'URTH', 'GDX', 'GDXJ', 'LTAM.L', 'IBB', 'XBI']
ticker_data = {}
fetcher = DataFetcher()
start_date = '2015-01-01'
now = datetime.datetime.now()
end_date = now.strftime('%Y-%m-%d')

print("Fetching data...")
for ticker in tickers:
    data = fetcher.fetch_ohlc_data(ticker, start_date, end_date)
    data.attrs['ticker'] = ticker  # Make sure ticker is stored
    ticker_data[ticker] = data
print("Data loaded!")

# Create Dash app
app = dash.Dash(__name__)

# Define layout
app.layout = html.Div([
    html.H1("Stock Chart with Bollinger Bands", style={'textAlign': 'center'}),
    
    html.Div([
        html.Label("Select Ticker:"),
        dcc.Dropdown(
            id='ticker-dropdown',
            options=[{'label': ticker, 'value': ticker} for ticker in tickers],
            value='AAPL',
            style={'width': '200px'}
        )
    ], style={'padding': '20px'}),
    
    dcc.Graph(id='stock-chart', style={'height': '80vh'})
])

# Callback to update chart when ticker changes
@app.callback(
    Output('stock-chart', 'figure'),
    Input('ticker-dropdown', 'value')
)
def update_chart(selected_ticker):
    print(f"Updating chart for {selected_ticker}")
    
    # Get data for selected ticker
    data = ticker_data[selected_ticker]
    print(f"Data shape: {data.shape}")
    print(f"Data head:\n{data.head()}")
    
    # IMPORTANT: Make sure ticker attribute is set
    if 'ticker' not in data.attrs:
        data.attrs['ticker'] = selected_ticker
    
    # Calculate indicators FOR THIS SPECIFIC TICKER
    ma = MovingAverage(window=840)
    ma_values = ma.calculate(data)
    
    bb_40 = BollingerBands(window=840, num_std=2)
    bb_40_values = bb_40.calculate(data)
    
    bb_20 = BollingerBands(window=420, num_std=2)
    bb_20_values = bb_20.calculate(data)
    
    # Create plot
    plotter = Plotter()
    fig = plotter.plot_candlestick(data, name=selected_ticker)
    plotter.add_moving_average(ma_values)
    plotter.add_bollinger_bands(bb_40_values, name_prefix='BB 40M', dashed=False)
    plotter.add_bollinger_bands(bb_20_values, name_prefix='BB 20M', dashed=True)
    
    print(f"Figure created with {len(plotter.fig.data)} traces")
    
    return plotter.fig


# Run the app
if __name__ == '__main__':
    app.run(debug=False, port=8050)