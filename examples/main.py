from bollinger_bands import Strategy, DataFetcher

if __name__ == "__main__":
    # print("Running Bollinger Bands + Relative Strength analysis...")
    # strategy = Strategy(ticker='ACWI', benchmark='^GSPC')
    # strategy.run_analysis()
    fetcher = DataFetcher()

    data = fetcher.fetch_daily_data(['AAPL', 'IBM'], '2024-01-01', '2024-12-31')
    print(data.head())


