# from bollinger_bands import Strategy, DataFetcher, Plotter
# import plotly.graph_objects as go

# if __name__ == "__main__":
#     # print("Running Bollinger Bands + Relative Strength analysis...")
#     # strategy = Strategy(ticker='ACWI', benchmark='^GSPC')
#     # strategy.run_analysis()
#     fetcher = DataFetcher()
#     # print(dir(fetcher)) 

#     # data = fetcher.fetch_daily_data(['AAPL', 'IBM'], '2024-01-01', '2024-12-31')
#     # print(data.head())

#     data = fetcher.fetch_ohlc_data('EEM', '2024-01-01', '2024-12-31')
#     print(data.head())

#     plotter = Plotter()
#     plotter.plot_price_chart(data)
#     plotter.plot_price_chart(data, line_color="black")


from bollinger_bands.data.fetcher import DataFetcher
from bollinger_bands.indicators.moving_average import MovingAverage
from bollinger_bands.indicators.bollinger_bands import BollingerBands
from bollinger_bands.visualization.plotter import Plotter

if __name__ == "__main__":

    # Fetch data
    fetcher = DataFetcher()
    # data = fetcher.fetch('AAPL', period='1y')
    data = fetcher.fetch_ohlc_data('EEM', '2024-01-01', '2024-12-31')

    # Calculate indicators
    ma = MovingAverage(window=20)
    ma_values = ma.calculate(data)

    bb = BollingerBands(window=20, num_std=2)
    bb_values = bb.calculate(data)

    # Plot everything
    plotter = Plotter()
    plotter.plot_candlestick(data)
    # plotter.add_moving_average(ma_values)
    # plotter.plot_bollinger_bands(bb_values)
    plotter.show()



