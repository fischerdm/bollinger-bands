from setuptools import setup, find_packages

setup(
    name="bollinger_bands",
    version="0.1",
    package_dir={"": "src"},  # Tell setuptools to look in src/
    packages=find_packages(where="src"),  # Find packages in src/
    install_requires=[
        'pandas>=1.3.0',           # Data manipulation
        'matplotlib>=3.4.0',       # Plotting
        'yfinance>=0.1.67',        # Fetching financial data
        'pytest>=6.2.0',           # Testing (optional)
    ],
    author="David Fischer",
    description="A Python library for calculating and visualizing Bollinger Bands",
    license="MIT",
)