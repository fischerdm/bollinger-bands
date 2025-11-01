from bollinger_bands import Strategy, DataFetcher, Plotter
import plotly.graph_objects as go

if __name__ == "__main__":
    # print("Running Bollinger Bands + Relative Strength analysis...")
    # strategy = Strategy(ticker='ACWI', benchmark='^GSPC')
    # strategy.run_analysis()
    fetcher = DataFetcher()
    # print(dir(fetcher)) 

    # data = fetcher.fetch_daily_data(['AAPL', 'IBM'], '2024-01-01', '2024-12-31')
    # print(data.head())

    data = fetcher.fetch_ohlc_data('EEM', '2024-01-01', '2024-12-31')
    print(data.head())

    plotter = Plotter()
    plotter.plot_price_chart(data)
    plotter.plot_price_chart(data, line_color="black")



