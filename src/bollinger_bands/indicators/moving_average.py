class MovingAverage:
    def __init__(self, window=20):
        self.window = window
    
    def calculate(self, data):
        """Calculate simple moving average"""
        return data['Close'].rolling(window=self.window).mean()