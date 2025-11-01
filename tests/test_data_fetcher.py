import pytest
import pandas as pd
from bollinger_bands.data.fetcher import DataFetcher

def test_fetch_daily_data_empty_tickers():
    fetcher = DataFetcher()
    with pytest.raises(ValueError):
        fetcher.fetch_daily_data([], '2020-01-01', '2020-02-01')

def test_fetch_daily_data_invalid_ticker():
    fetcher = DataFetcher()
    with pytest.raises(RuntimeError):
        fetcher.fetch_daily_data(['INVALID_TICKER'], '2020-01-01', '2020-02-01')

def test_resample_to_monthly_empty_data():
    fetcher = DataFetcher()
    with pytest.raises(ValueError):
        fetcher.resample_to_monthly(pd.DataFrame())
