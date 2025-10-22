# Bollinger-Bands
A Python library for calculating and visualizing Bollinger Bands, a popular technical analysis tool for financial markets.

## Folder Structure

```bash
bollinger-bands/
│
├── src/
│   └── bollinger_bands/         # Main package directory
│       ├── __init__.py          # Makes the directory a Python package
│       ├── data_fetcher.py      # Data fetching logic
│       ├── plotter.py           # Plotting functions
│       ├── bollinger_bands.py   # Bollinger Bands logic
│       └── relative_strength.py # Relative strength logic
│       └── strategy.py
│
├── tests/                       # Unit tests (optional but recommended)
│   └── test_bands.py
│
├── setup.py                     # Installation script
├── README.md                    # Project documentation
└── LICENSE                      # License file (e.g., MIT)
```