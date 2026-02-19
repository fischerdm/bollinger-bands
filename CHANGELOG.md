# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-19

### Added
- **Watchlist System:** Star/favorite tickers for quick filtering

  - Star button next to ticker dropdown to add/remove tickers from watchlist
  - "⭐ Only" toggle buttons to filter both ticker dropdown and relative strength table
  - Clickable ⭐ column in RS table to toggle stars directly
  - Persistent storage via watchlist.json and browser localStorage
  - Survives page refreshes and app restarts

- **Extra Moving Averages:** Optional 50D and 200D MA overlay on the main chart

  - Checklist placed just above the chart for quick access
  - 50D displayed as a pink dotted line, 200D as purple dotted line
  - 200D enabled by default
  - Calculated on daily data, overlaid regardless of selected chart period

- **Ticker Selection from RS Table:** Click any row to switch to that ticker instantly
- **Time Range Selector Buttons:** 10 range buttons (1m–All)
- **Zone Label Enhancements:** Entry/exit zones now display prices in USD

### Fixed
- Fixed zone price lookups to use correct dates
- Resolved tick label overlap on long time series
- Fixed form control label colors bleeding from chart theme

## [0.1.3] - 2026-01-31

### Fixed
- **Re-entry signal visualization** now correctly uses the same BB distance-filtered signals as zone identification
  - Eliminates orphaned green triangles appearing without corresponding zones
- **Signal consumption tracking** in zone identification
  - Signals are now only marked as used when they appear in a final green zone
  - Previously, signals detected during pattern analysis were marked as used even when the orange strategy won
  - Example: a 2009 exit detecting a green pattern with a 2022 signal, but orange winning, would lock that signal and make it unavailable for the actual 2022 exit

### Added
- Debug logging for BB distance filtering showing original count, filtered count, and number removed

## [0.1.2] - 2026-01-31

### Changed
- **BREAKING: Unified confirmation parameters:** Simplified exit signal confirmation from 7 parameters to 2
  - Removed: Smoothing Window, MA Condition Lookahead, MA Condition Threshold (Daily), Max Confirmation Wait
  - Kept: Confirmation Window (20 days) and Confirmation Threshold (60%)
  - Same progressive confirmation logic now applies consistently across all views (daily/monthly/quarterly)
- **Natural signal limits:** Exit signals must be confirmed before the zone ends — no artificial time limits
  - Orange zones end at MA crossing
  - Green zones end at Nth re-entry signal
  - Signals not confirmed in time are automatically rejected

### Added
- **Debouncing for numeric inputs:** 500ms delay prevents excessive recalculations when adjusting parameters
  - Applies to: Confirmation Window/Threshold, Max Re-Entry Signals, Flat Thresholds, BB Distance
- **Enhanced zone hover tooltips:** Each zone now shows start date (crossing), exit date (confirmation), and end date (re-entry)
  - Green zones display ordinal re-entry signal label (e.g. "4th Re-Entry Signal")
  - Orange zones display "MA Crossing"

### Fixed
- Exit signal lines now extend from MA value down to chart bottom instead of full height

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
