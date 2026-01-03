# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-01-03

### Changed
- **BREAKING**: Improved exit signal validation logic for monthly/quarterly views
  - Exit signals now use two-period lookahead validation
  - When crossing detected in period P, MA conditions are checked throughout ALL of period P+1 (next complete month/quarter)
  - Price must remain below MA at end of period P+1 for signal confirmation
  - This change makes exit signals more reliable and catches major market downturns like 2008 that were previously missed

### Added
- New function `check_ma_conditions_for_next_period()` in crossing_detection module
  - Implements two-part validation: MA conditions in P+1 + price position check
  - Provides detailed console logging for debugging
- Increased daily lookahead maximum from 30 to 90 days for more flexibility

### Removed
- Experimental "Upper BB Change" exit signal option (reverted to MA-only approach)
  - Upper BB proved more volatile and less reliable than MA-based signals
  - Simplified UI by removing the "Exit Signal Basis" toggle

### Fixed
- Exit signals now properly detected for 2008 market crash in EEM and other instruments
- Monthly/quarterly validation no longer rejects valid signals due to insufficient same-period MA conditions

## [0.1.0] - 2026-01-02

### Added
- Initial release of Bollinger Bands Trading Dashboard
- Implementation of Alfons Cortés' trading strategy based on Behavioral Finance principles
- Interactive visualization with Dash and Plotly
- Support for multiple tickers (ETFs and stocks)
- Three viewing modes: Daily, Monthly, Quarterly
- Two MA/BB period options: 40M/20M and 20M/10M
- Exit signal detection based on:
  - Price crossing below moving average
  - Flat long MA condition (configurable threshold)
  - Decreasing short MA condition (configurable threshold)
- Re-entry signal detection based on candlestick patterns:
  - Bullish Engulfing
  - Hammer/Inverted Hammer
  - Morning Star
- Configurable trading zones:
  - Below MA zones (red shading)
  - Exit-to-Reentry zones (green/orange shading)
- Two trading strategies:
  - Conservative: Candlestick signals only
  - Aggressive: MA crossing + Candlestick signals
- Relative Strength analysis table with:
  - 6M and 12M performance metrics
  - Levy RS calculation
  - Benchmark comparison
  - Multi-currency support (USD, CHF, EUR, GBP)
- Smart data caching with dual storage (original currency + USD-normalized)
- Automatic data updates on startup
- Manual data refresh functionality
- Comprehensive tooltips and help documentation
- Professional JOURNAL theme for clean presentation

### Technical Features
- Modular architecture with separate modules for:
  - Data fetching and storage
  - Currency conversion
  - Technical indicators (MA, Bollinger Bands, Band Width)
  - Signal detection
  - Zone identification
  - Visualization
- YAML-based configuration for tickers
- Parquet file storage for efficient data caching
- Web scraping fallback for exchange rate data
