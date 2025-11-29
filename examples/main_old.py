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
    ticker_data = {}

    tickers = ['EEM', 'URTH', 'GDX', 'GDXJ', 'LTAM.L', 'IBB', 'XBI']
    start_date = '2015-01-01'
    end_date = '2025-10-31'

    # data = fetcher.fetch_ohlc_data('EEM', start_date, end_date) # Emerging Markets ETF
    # data = fetcher.fetch_ohlc_data('URTH', start_date, end_date) # MSCI World ETF
    # data = fetcher.fetch_ohlc_data('GDX', start_date, end_date) # Gold Miners ETF
    # data = fetcher.fetch_ohlc_data('GDXJ', start_date, end_date) # Junior Gold Miners ETF
    # data = fetcher.fetch_ohlc_data('LTAM.L', start_date, end_date) # MSCI Latin America ETF
    # data = fetcher.fetch_ohlc_data('IBB', start_date, end_date) # iShares Biotechnology ETF
    # data = fetcher.fetch_ohlc_data('XBI', start_date, end_date) # SPDR Biotechnology ETF

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

    for ticker in tickers:
        data = fetcher.fetch_ohlc_data(ticker, start_date, end_date)
        ticker_data[ticker] = data

    # Calculate indicators
    ma = MovingAverage(window=840) # approx 40 months * 21 days/month
    ma_values = ma.calculate(data)

    bb_40 = BollingerBands(window=840, num_std=2) # approx 40 months * 21 days/month
    bb_40_values = bb_40.calculate(data)

    bb_20 = BollingerBands(window=420, num_std=2) # approx 20 months * 21 days/month
    bb_20_values = bb_20.calculate(data)

    # Plot everything
    plotter = Plotter()
    plotter.set_data(ticker_data)
    plotter.plot_candlestick(data)
    plotter.add_ticker_selector(tickers)
    plotter.add_moving_average(ma_values)
    plotter.add_bollinger_bands(bb_40_values, name_prefix='BB 40M', dashed=False)
    plotter.add_bollinger_bands(bb_20_values, name_prefix='BB 20M', dashed=True)
    plotter.show()



