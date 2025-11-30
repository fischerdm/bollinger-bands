# indicators/band_width.py
class BandWidth:
    def __init__(self, window=20):
        self.window = window
    
    def calculate(self, bb_values):
        """Calculate the width between upper and lower bands"""
        width = bb_values['upper'] - bb_values['lower']
        return width
    
    def calculate_daily_change(self, bb_values):
        """Calculate daily change in band width"""
        width = self.calculate(bb_values)
        return width.diff()
    
    def is_widening(self, bb_values, threshold=0, periods=5):
        """Detect if bands are widening (bubble formation)"""
        width_change = self.calculate_daily_change(bb_values)
        # Check if width is increasing over recent periods
        recent_changes = width_change.tail(periods)
        return (recent_changes > threshold).sum() >= periods * 0.6  # 60% of periods