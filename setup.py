from setuptools import setup, find_packages

setup(
    name="bollinger_bands",
    version="0.1",
    package_dir={"": "src"},  # Tell setuptools to look in src/
    packages=find_packages(where="src"),  # Find packages in src/
    install_requires=[
        'pandas',
        'matplotlib',
        'yfinance',
    ],
    author="Your Name",
    description="A Python library for calculating and visualizing Bollinger Bands",
    license="MIT",
)