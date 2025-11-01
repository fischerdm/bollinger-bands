import pytest
from bollinger_bands.bollinger_bands import BollingerBandsAnalyzer

def test_bollinger_bands_empty_ticker():
    with pytest.raises(ValueError):
        BollingerBandsAnalyzer(ticker='')

def test_bollinger_bands_invalid_ticker():
    with pytest.raises(RuntimeError):
        analyzer = BollingerBandsAnalyzer(ticker='INVALID_TICKER')
        analyzer.fetch_data()

def test_bollinger_bands_calculation():
    analyzer = BollingerBandsAnalyzer(ticker='ACWI')
    data = analyzer.fetch_data()
    assert not data.empty
    result = analyzer.calculate_bollinger_bands(window=20)
    assert 'middle_bb_20m' in result.columns
