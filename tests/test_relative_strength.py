import pytest
from bollinger_bands.relative_strength import RelativeStrengthAnalyzer

def test_relative_strength_empty_ticker():
    with pytest.raises(ValueError):
        RelativeStrengthAnalyzer(ticker='', benchmark='^GSPC')

def test_relative_strength_invalid_ticker():
    with pytest.raises(RuntimeError):
        analyzer = RelativeStrengthAnalyzer(ticker='INVALID_TICKER', benchmark='^GSPC')
        analyzer.fetch_data()

def test_relative_strength_calculation():
    analyzer = RelativeStrengthAnalyzer(ticker='ACWI', benchmark='^GSPC')
    data = analyzer.fetch_data()
    assert not data.empty
    result = analyzer.calculate_relative_strength()
    assert 'relative_strength' in result.columns
