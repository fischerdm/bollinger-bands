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