from .strategies.strategy import Strategy

if __name__ == "__main__":
    print("Running Bollinger Bands package as a module...")
    strategy = Strategy(ticker='ACWI', benchmark='^GSPC')
    strategy.run_analysis()
