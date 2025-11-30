import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc  # Import the library
from dash_bootstrap_templates import load_figure_template  # Import figure templates
from bollinger_bands.data.fetcher import DataFetcher
from bollinger_bands.indicators.moving_average import MovingAverage
from bollinger_bands.indicators.bollinger_bands import BollingerBands
from bollinger_bands.indicators.band_width import BandWidth
from bollinger_bands.visualization.plotter import Plotter
import datetime
from plotly.subplots import make_subplots
import plotly.graph_objs as go

# Tickers configuration
tickers = ['EEM', 'URTH', 'GDX', 'GDXJ', 'LTAM.L', 'IBB', 'XBI']
tickers_dict = {
    'EEM': 'Emerging Markets (EEM)',
    'URTH': 'Global Markets (URTH)',
    'GDX': 'Basic Materials (GDX)',
    'GDXJ': 'Basic Materials (GDXJ)',
    'LTAM.L': 'Latin America (LTAM.L)',
    'IBB': 'Healthcare (IBB)',
    'XBI': 'Healthcare (XBI)',
}

ticker_data = {}
fetcher = DataFetcher()
start_date = '2015-01-01'
now = datetime.datetime.now()
end_date = now.strftime('%Y-%m-%d')

print("Fetching data...")
for ticker in tickers:
    data = fetcher.fetch_ohlc_data(ticker, start_date, end_date)
    data.attrs['ticker'] = ticker
    ticker_data[ticker] = data
print("Data loaded!")

# Set up the app with a theme (e.g., 'LUX')
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])
load_figure_template("LUX") # Match Plotly charts to the theme

app.layout = dbc.Container([  # Use dbc.Container for responsive layout
    html.H1("Stock Chart with Bollinger Bands", style={'textAlign': 'center'}),
    html.H2(id='ticker-name', style={'textAlign': 'center'}),
    
    dbc.Row([
        dbc.Col([  # Use dbc.Col to define column widths (e.g. width=4 for a 12-column grid)
            html.Label("Select Ticker:"),
            dcc.Dropdown(
                id='ticker-dropdown',
                options=[{'label': ticker, 'value': ticker} for ticker in tickers],
                value='EEM',
                # Style is handled by the theme now, no specific width needed
            )
        ], width=4),
    ], className="mb-4"), # Add margin bottom

    # html.Div(id='bandwidth-info', style={'padding': '20px', 'fontSize': '14px'}), # Can be styled with DBC
    dcc.Graph(id='stock-chart', style={'height': '80vh'})
], fluid=True, className="p-4") # Add padding to the container


@app.callback(
    [Output('stock-chart', 'figure'),
     Output('ticker-name', 'children')],
    # Output('bandwidth-info', 'children')],
    Input('ticker-dropdown', 'value')
)
def update_chart(selected_ticker):
    try:
        print(f"Updating chart for {selected_ticker}")
        data = ticker_data[selected_ticker]
        
        if 'ticker' not in data.attrs:
            data.attrs['ticker'] = selected_ticker
        
        # Calculate indicators
        ma = MovingAverage(window=840)
        ma_values = ma.calculate(data)
        
        bb_40 = BollingerBands(window=840, num_std=2)
        bb_40_values = bb_40.calculate(data)
        
        bb_20 = BollingerBands(window=420, num_std=2)
        bb_20_values = bb_20.calculate(data)
        
        # Calculate BandWidth
        bw = BandWidth(window=840)
        bandwidth_40 = bw.calculate(bb_40_values)
        
        # Create original plot
        plotter = Plotter()
        fig = plotter.plot_candlestick(data, name=selected_ticker)
        plotter.add_moving_average(ma_values)
        plotter.add_bollinger_bands(bb_40_values, name_prefix='BB 40M', dashed=False)
        plotter.add_bollinger_bands(bb_20_values, name_prefix='BB 20M', dashed=True)
        
        print(f"Original figure: {len(plotter.fig.data)} traces")
        
        ticker_name = tickers_dict.get(selected_ticker, selected_ticker)
        
        # Create subplot figure
        # Add template="plotly_dark" or another template name to match theme if desired
        fig_with_bandwidth = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.15,
            row_heights=[0.75, 0.25],
            subplot_titles=(ticker_name, "Band Width (40M BB)"),
            specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
        )
        
        # Copy traces to row 1
        for trace in plotter.fig.data:
            fig_with_bandwidth.add_trace(trace, row=1, col=1)
        
        # Add BandWidth to row 2
        fig_with_bandwidth.add_trace(
            go.Scatter(
                x=data.index,
                y=bandwidth_40,
                name='BandWidth',
                line=dict(color='darkblue', width=2)
            ),
            row=2, col=1
        )
        
        # Add mean line
        mean_bw = bandwidth_40.mean()
        fig_with_bandwidth.add_hline(
            y=mean_bw,
            line_dash="dash",
            line_color="gray",
            opacity=0.5,
            row=2, col=1
        )
        
        # Update layout - preserve range slider for bottom chart
        fig_with_bandwidth.update_layout(
            height=900,
            showlegend=True,
            hovermode='x unified',
            # Move the time buttons to the top
            xaxis=dict(
                rangeselector=dict(
                    buttons=list([
                        dict(count=1, label="1m", step="month", stepmode="backward"),
                        dict(count=6, label="6m", step="month", stepmode="backward"),
                        dict(count=1, label="1y", step="year", stepmode="backward"),
                        dict(step="all", label="All")
                    ]),
                    y=1.07,  # Position above the chart
                    yanchor="top"
                )
            )
        )
        
        # Configure axes - NO range slider on top chart
        fig_with_bandwidth.update_xaxes(row=1, col=1, rangeslider_visible=False)
        
        # Range slider ONLY on bottom chart
        fig_with_bandwidth.update_xaxes(
            title_text="Date", 
            row=2, col=1,
            rangeslider_visible=True
        )
        
        # Y-axis labels
        fig_with_bandwidth.update_yaxes(title_text="Price", row=1, col=1)
        fig_with_bandwidth.update_yaxes(title_text="Band Width", row=2, col=1)
        
        # Fix subplot titles positioning
        fig_with_bandwidth.layout.annotations[0].update(y=1.02)  # Top subplot title
        fig_with_bandwidth.layout.annotations[1].update(y=0.23)  # Bottom subplot title
        
        print(f"Subplot figure: {len(fig_with_bandwidth.data)} traces")
        
        # bandwidth_info = html.Div([
        #     html.P(f"Current BandWidth (40M): {bandwidth_40.iloc[-1]:.2f}"),
        #     html.P(f"Mean BandWidth: {mean_bw:.2f}"),
        # ])
        
        return fig_with_bandwidth, ticker_name #, bandwidth_info
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        plotter = Plotter()
        fig = plotter.plot_candlestick(ticker_data[selected_ticker], name=selected_ticker)
        return fig, f"Error: {selected_ticker}", html.Div(f"Error: {str(e)}")

if __name__ == '__main__':
    app.run(debug=False, port=8050)
