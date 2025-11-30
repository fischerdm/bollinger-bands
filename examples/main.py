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


# Aktualisierte MovingAverage Klasse
class MovingAverage:
    def __init__(self, window=20):
        self.window = window
    
    def calculate(self, data):
        """Calculate simple moving average"""
        return data['Close'].rolling(window=self.window).mean()
    
    def calculate_change(self, data):
        """Calculate the percentage change of the moving average"""
        sma = self.calculate(data)
        return sma.pct_change() * 100

# Aktualisierte BollingerBands Klasse
class BollingerBands:
    def __init__(self, window=20, num_std=2):
        self.window = window
        self.num_std = num_std
    
    def calculate(self, data):
        """Calculate Bollinger Bands and return as DataFrame"""
        sma = data['Close'].rolling(window=self.window).mean()
        std = data['Close'].rolling(window=self.window).std()
        
        upper_band = sma + (std * self.num_std)
        lower_band = sma - (std * self.num_std)
        
        return pd.DataFrame({
            'middle': sma,
            'upper': upper_band,
            'lower': lower_band
        })

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

app.layout = dbc.Container([
    html.H1("Stock Chart with Bollinger Bands", style={'textAlign': 'center'}),
    html.H2(id='ticker-name', style={'textAlign': 'center'}),
    
    dbc.Row([
        dbc.Col([
            html.Label("Select Ticker:"),
            dcc.Dropdown(
                id='ticker-dropdown',
                options=[{'label': ticker, 'value': ticker} for ticker in tickers],
                value='EEM',
            )
        ], width=4),
    ], className="mb-4"),

    dcc.Graph(id='stock-chart', style={'height': '120vh'})
], fluid=True, className="p-4")


@app.callback(
    [Output('stock-chart', 'figure'),
     Output('ticker-name', 'children')],
    Input('ticker-dropdown', 'value')
)
def update_chart(selected_ticker):
    try:
        print(f"Updating chart for {selected_ticker}")
        data = ticker_data[selected_ticker]
        
        if 'ticker' not in data.attrs:
            data.attrs['ticker'] = selected_ticker
        
        # Calculate indicators
        ma_840 = MovingAverage(window=840)
        ma_840_values = ma_840.calculate(data)
        ma_840_change = ma_840.calculate_change(data)

        ma_420 = MovingAverage(window=420)
        ma_420_values = ma_420.calculate(data)
        ma_420_change = ma_420.calculate_change(data)
        
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
        plotter.add_moving_average(ma_840_values)
        plotter.add_bollinger_bands(bb_40_values, name_prefix='BB 40M', dashed=False)
        plotter.add_bollinger_bands(bb_20_values, name_prefix='BB 20M', dashed=True)
        
        print(f"Original figure: {len(plotter.fig.data)} traces")
        
        ticker_name = tickers_dict.get(selected_ticker, selected_ticker)
        
        # Create subplot figure with 3 rows
        fig_with_bandwidth = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=(ticker_name, "Band Width (40M BB)", "MA Change (420 & 840)"),
            specs=[[{"secondary_y": False}], [{"secondary_y": False}], [{"secondary_y": False}]]
        )
        
        # Copy traces to row 1
        for trace in plotter.fig.data:
            fig_with_bandwidth.add_trace(trace, row=1, col=1)

        # NEU & KORRIGIERT: Schattierung der Bereiche basierend auf 50%-Regel zwischen Crossovers
        is_below = data['Close'] < ma_840_values
        # Segmente identifizieren, indem Crossovers gezählt werden
        segment_id = (is_below != is_below.shift(1)).cumsum()
        segment_id = segment_id.fillna(0)
        
        # DataFrame mit Segment-ID und Close-Preis
        segments_df = pd.DataFrame({'Close': data['Close'], 'is_below': is_below})
        
        # Iteriere durch die Segmente und prüfe die Bedingung
        for name, group in segments_df.groupby(segment_id):
            if len(group) < 2:
                continue
            
            # Prüfe ob mehr als 50% der Tage in diesem Segment unter dem SMA lagen
            if group['is_below'].mean() > 0.5:
                # Füge eine schattierte Spur für dieses spezifische Segment hinzu
                fig_with_bandwidth.add_trace(
                    go.Scatter(
                        x=group.index,
                        y=group['Close'],
                        mode='lines',
                        fill='tozeroy',
                        fillcolor='rgba(255, 0, 0, 0.2)', # Rote, transparente Farbe
                        line=dict(color='rgba(255, 255, 255, 0)'), # Unsichtbare Linie
                        name=f'Price below 40M SMA Segment {name}',
                        showlegend=False # Legende nicht anzeigen, da es viele Segmente gibt
                    ),
                    row=1, col=1
                )
        
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
        
        # Add mean line for Bandwidth
        mean_bw = bandwidth_40.mean()
        fig_with_bandwidth.add_hline(
            y=mean_bw,
            line_dash="dash",
            line_color="gray",
            opacity=0.5,
            row=2, col=1
        )
        
        # Add MA change to row 3
        fig_with_bandwidth.add_trace(
            go.Scatter(
                x=data.index,
                y=ma_840_change,
                name='MA 840 Change',
                line=dict(color='red', width=2)
            ),
            row=3, col=1
        )
        fig_with_bandwidth.add_trace(
            go.Scatter(
                x=data.index,
                y=ma_420_change,
                name='MA 420 Change',
                line=dict(color='green', width=2)
            ),
            row=3, col=1
        )

        # Hinzufügen der horizontalen Linie bei Y=0 zur dritten Subplot
        fig_with_bandwidth.add_hline(
            y=0,
            line_dash="solid",
            line_color="black",
            opacity=1,
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
        
        # Configure axes - NO range slider on top charts
        fig_with_bandwidth.update_xaxes(row=1, col=1, rangeslider_visible=False)
        fig_with_bandwidth.update_xaxes(row=2, col=1, rangeslider_visible=False)
        
        # Range slider ONLY on bottom chart
        fig_with_bandwidth.update_xaxes(
            title_text="Date", 
            row=3, col=1,
            rangeslider_visible=True
        )
        
        # Y-axis labels
        fig_with_bandwidth.update_yaxes(title_text="Price", row=1, col=1)
        fig_with_bandwidth.update_yaxes(title_text="Band Width", row=2, col=1)
        fig_with_bandwidth.update_yaxes(title_text="MA Change (%)", row=3, col=1)
        
        # KORRIGIERT: Fix subplot titles positioning by iterating through the list
        annotations = fig_with_bandwidth.layout.annotations
        if len(annotations) > 0:
            annotations[0].update(y=1.02) # Titel für Reihe 1
        if len(annotations) > 1:
            annotations[1].update(y=0.45) # Titel für Reihe 2
        if len(annotations) > 2:
            annotations[2].update(y=0.21) # Titel für Reihe 3


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
