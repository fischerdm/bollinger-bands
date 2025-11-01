from bollinger_bands import Strategy, DataFetcher
import plotly.graph_objects as go

if __name__ == "__main__":
    # print("Running Bollinger Bands + Relative Strength analysis...")
    # strategy = Strategy(ticker='ACWI', benchmark='^GSPC')
    # strategy.run_analysis()
    fetcher = DataFetcher()
    print(dir(fetcher)) 

    data = fetcher.fetch_daily_data(['AAPL', 'IBM'], '2024-01-01', '2024-12-31')
    print(data.head())

    data = fetcher.fetch_ohlc_data('EEM', '2024-01-01', '2024-12-31')
    print(data.head())

    print(data[['Open']])
    print(data['Open'])
    print(data.columns)

    # Create candlestick chart
    print(data.index)

    # symbol = "EEM"
    
    # Remove the MultiIndex - keep only the price type level
    # data.columns = data.columns.get_level_values(0)

    print(data.columns)  # Should now show: Index(['Open', 'High', 'Low', 'Close'])
    print(data.head())

    # Now the candlestick chart will work
    # symbol = "EEM"
    fig = go.Figure(data=[go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],

        # Set the body fill colors (e.g., green for up, red for down)
        increasing_fillcolor='green',
        decreasing_fillcolor='red',
        
        # Set the line color for increasing candles to black
        increasing_line_color='black',
        
        # Set the line color for decreasing candles to black
        decreasing_line_color='black'
    )])

    # Optional: You can also set the body colors to make the wicks stand out
    # fig.update_trace_ops(
    #     selector=dict(type='candlestick'),
    #     increasing_fillcolor='green',
    #     decreasing_fillcolor='red'
    # )

    fig.update_layout(
        title=f"{data.attrs['ticker']} Candlestick Chart (2024)",
        yaxis_title="Price",
        xaxis_rangeslider_visible=True # False
    )

    fig.show()


