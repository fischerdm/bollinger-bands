from bollinger_bands.indicators.bollinger_bands import BollingerBands
from bollinger_bands.indicators.bollinger_bands import MovingAverage

# from bollinger_bands.indicators.bollinger_bands import BollingerBandsAnalyzer
# from bollinger_bands.strategies.relative_strength import RelativeStrengthAnalyzer

# class Strategy:
#     """Combines Bollinger Bands and Relative Strength for advanced analysis."""

#     def __init__(self, ticker: str, benchmark: str = None, start_date: str = '1990-01-01', end_date: str = '2025-10-21'):
#         self.ticker = ticker
#         self.benchmark = benchmark
#         self.start_date = start_date
#         self.end_date = end_date
#         self.bb_analyzer = BollingerBandsAnalyzer(ticker, start_date, end_date)
#         self.rs_analyzer = RelativeStrengthAnalyzer(ticker, benchmark, start_date, end_date) if benchmark else None

#     def run_analysis(self):
#         """Runs Bollinger Bands and Relative Strength analysis."""
#         # Bollinger Bands
#         self.bb_analyzer.fetch_data()
#         self.bb_analyzer.calculate_bollinger_bands(window=20)
#         self.bb_analyzer.calculate_bollinger_bands(window=40)
#         self.bb_analyzer.plot_bollinger_bands(windows=[20, 40])

#         # Relative Strength (if benchmark provided)
#         if self.rs_analyzer:
#             self.rs_analyzer.fetch_data()
#             self.rs_analyzer.calculate_relative_strength()
#             self.rs_analyzer.plot_relative_strength()


class BollingerBandStrategy:
    def __init__(self):
        self.bb = BollingerBands(window=20, num_std=2)
        self.ma = MovingAverage(window=20)
    
    def generate_signals(self, data):
        bb_values = self.bb.calculate(data)
        # Use bb_values to determine buy/sell signals