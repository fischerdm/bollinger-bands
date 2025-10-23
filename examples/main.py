from bollinger_bands import Strategy

if __name__ == "__main__":
    print("Running Bollinger Bands + Relative Strength analysis...")
    strategy = Strategy(ticker='ACWI', benchmark='^GSPC')
    strategy.run_analysis()

