# Configuration Options and Parameters

## Overview

This document provides detailed explanations of all configuration options and parameters available in the Bollinger Bands Trading Application. Understanding these parameters is essential for effective use of the trading strategy implementation.

## Chart Configuration

### Ticker Selection

**Parameter**: Ticker dropdown  
**Type**: Selection  
**Default**: EEM

**Description**:  
Choose which ETF or stock to analyze. Each ticker represents different market sectors or regions. The application supports multiple tickers configured in `config/tickers.yaml`.

**Available Tickers** (default configuration):
- **EEM**: Emerging Markets
- **URTH**: Global Markets
- **GDX**: Basic Materials (Gold Miners)
- **GDXJ**: Basic Materials Junior Miners
- **LTAM.L**: Latin America
- **IBB**: Healthcare (Biotechnology)
- **XBI**: Healthcare Extended
- **IOGP.L**: Oil & Gas Exploration & Production
- **WENS.AS**: Energy Sector

**Usage**:  
Select the ticker you want to analyze from the dropdown. The chart will update to show price data, Bollinger Bands, and trading signals for the selected ticker.

---

### Time Period for Price Chart

**Parameter**: Period selector  
**Type**: Radio buttons (Daily | Monthly | Quarterly)  
**Default**: Monthly

**Description**:  
How to aggregate price data for the candlestick chart display.

**Options**:

1. **Daily**: Shows each individual trading day as a separate candlestick
2. **Monthly**: Aggregates data by calendar month
   - Open: First trading day of the month
   - High: Highest price during the month
   - Low: Lowest price during the month
   - Close: Last trading day of the month
3. **Quarterly**: Aggregates data by calendar quarter
   - Open: First trading day of the quarter
   - High: Highest price during the quarter
   - Low: Lowest price during the quarter
   - Close: Last trading day of the quarter

**Effect on Analysis**:  
Monthly and quarterly views reduce noise and make long-term trends more visible. Daily view provides maximum detail but can be overwhelming for long time periods.

**Recommendation**:  
- **Long-term strategy analysis**: Monthly or Quarterly
- **Precise entry/exit timing**: Daily
- **Initial exploration**: Monthly

---

### Time Period for MA & Bollinger Bands

**Parameter**: MA period selector  
**Type**: Radio buttons (40M/20M | 20M/10M)  
**Default**: 40M/20M

**Description**:  
Moving Average and Bollinger Band calculation periods. This setting determines the sensitivity of the technical indicators.

**Options**:

1. **40M/20M** (Conservative):
   - Long MA: 840 trading days (approximately 40 months)
   - Short MA: 420 trading days (approximately 20 months)
   - More stable, fewer false signals
   - Better for long-term trend following

2. **20M/10M** (Aggressive):
   - Long MA: 420 trading days (approximately 20 months)
   - Short MA: 210 trading days (approximately 10 months)
   - More responsive, faster signals
   - Higher risk of false signals due to market noise

**Technical Details**:  
The system uses two moving averages:
- **Long MA**: Used for primary trend identification
- **Short MA**: Used for detecting trend changes
- **Bollinger Bands**: Calculated from both MAs to show volatility

**Recommendation**:  
Start with 40M/20M for more reliable signals, especially when learning the strategy.

---

### Chart Scale

**Parameter**: Scale selector  
**Type**: Radio buttons (Linear | Log)  
**Default**: Linear

**Description**:  
Y-axis scale type for price display.

**Options**:

1. **Linear**:
   - Equal spacing for equal price changes
   - $10 change always takes same vertical space
   - Better for short-term analysis

2. **Log (Logarithmic)**:
   - Equal spacing for equal percentage changes
   - 10% change always takes same vertical space
   - Better for long-term trends and assets with large price ranges

**When to Use**:
- **Linear**: Short time periods, assets with stable prices
- **Log**: Long time periods (5+ years), assets with exponential growth

---

## Moving Average Parameters

### Flat Long MA Threshold

**Parameter**: Flat Long MA Threshold (%)  
**Type**: Numeric input  
**Range**: 0.01 - 0.10  
**Default**: 0.025 (2.5%)  
**Step**: 0.005

**Description**:  
The long Moving Average (40M or 20M depending on MA period selection) is considered "flat" when its rate of change is below this threshold. This is one of the exit signal conditions.

**Technical Definition**:  
```
MA_change = (MA[today] - MA[20 days ago]) / MA[20 days ago] * 100
If MA_change < threshold → MA is "flat"
```

**Effect**:
- **Lower values** (e.g., 0.01): Stricter requirement, MA must be nearly horizontal
- **Higher values** (e.g., 0.05): More permissive, allows gentle slopes

**Typical Range**: 0.01 - 0.05

**Trading Interpretation**:  
A flat long MA indicates the long-term trend has lost momentum. This is a key component of the exit signal, suggesting it may be time to move to cash.

**Recommendation**:  
- **Conservative traders**: 0.01-0.02 (stricter condition)
- **Moderate traders**: 0.025-0.03 (default)
- **Aggressive traders**: 0.03-0.05 (more permissive)

---

### Decreasing Short MA Threshold

**Parameter**: Decreasing Short MA Threshold (%)  
**Type**: Numeric input  
**Range**: -0.10 - 0.05  
**Default**: 0 (any decrease)  
**Step**: 0.005

**Description**:  
The short Moving Average (20M or 10M) is considered "decreasing" when its rate of change is below this threshold. This is the second exit signal condition.

**Technical Definition**:  
```
MA_change = (MA[today] - MA[20 days ago]) / MA[20 days ago] * 100
If MA_change < threshold → MA is "decreasing"
```

**Effect**:
- **Value = 0**: Any decrease qualifies (default)
- **Negative values** (e.g., -0.02): Requires stronger downward movement
- **Positive values** (e.g., 0.02): Allows slight increases (very permissive)

**Typical Range**: -0.05 to 0.05

**Trading Interpretation**:  
A decreasing short MA indicates short-term weakness developing. Combined with a flat long MA, this suggests momentum is fading and risk is increasing.

**Recommendation**:  
- **Standard approach**: 0 (any decrease)
- **Aggressive exits**: 0.02-0.05 (exit on slight weakness)
- **Conservative exits**: -0.02 to -0.05 (require strong decline)

---

### MA Condition Threshold (All Views)

**Parameter**: MA Condition Threshold  
**Type**: Numeric input  
**Range**: 0 - 1  
**Default**: 0.5 (50%)  
**Step**: 0.05

**Description**:  
Minimum percentage of days that must have MA conditions met within the validation period. This parameter filters exit signals to ensure the unfavorable MA conditions persist for a meaningful portion of the period.

**Values**:
- **0**: Disabled (no validation required)
- **0.5**: 50% of days must meet conditions (default)
- **1**: 100% of days must meet conditions (very strict)

**Application**:

For **Monthly/Quarterly** views:
- Validation period: From crossing date to end of period
- Example: If crossing occurs on day 10 of a 30-day month, checks days 10-30

For **Daily** view:
- Validation period: From crossing date to (crossing date + lookahead days)
- Configured via "MA Condition Lookahead" parameter

**Technical Details**:  
When a price crossing below MA is detected, the system checks whether the MA conditions (flat long MA and decreasing short MA) are met for the specified percentage of days in the validation window.

**Example** (Monthly view, threshold = 0.5):
```
Period: January (30 days)
Crossing detected: January 15
Validation window: January 15-31 (17 days)
MA conditions met: 10 days out of 17
Result: 10/17 = 58.8% > 50% → Signal is VALID
```

**Effect**:
- **Lower values** (e.g., 0.3): More permissive, catches more signals
- **Higher values** (e.g., 0.7): More strict, filters out weak signals

**Recommendation**:  
- **Default approach**: 0.5 (balanced)
- **More signals**: 0.3-0.4
- **Higher confidence**: 0.6-0.7
- **Maximum strictness**: 0.8-1.0

---

## Exit Signal Detection (Daily View)

### Smoothing Window

**Parameter**: Smoothing Window (Daily Exit)  
**Type**: Numeric input  
**Range**: 1 - 20 days  
**Default**: 5 days  
**Step**: 1

**Description**:  
Number of days to smooth the closing price before detecting crossings in daily view. This reduces noise and prevents false signals from daily volatility.

**Technical Implementation**:  
```python
smoothed_price = price.rolling(window=smoothing_window).mean()
crossing = (smoothed_price crosses below MA)
```

**Effect**:
- **Lower values** (1-3): More responsive but noisier signals
- **Medium values** (4-7): Balanced approach (default)
- **Higher values** (8-20): Smoother but slower signals

**Trade-off**:
- **Higher values**: Reduce noise, may delay signals by several days
- **Lower values**: React quickly, may generate false signals

**Recommendation**:  
3-7 days for most applications. Adjust based on ticker volatility.

---

### MA Condition Lookahead

**Parameter**: MA Condition Lookahead (Daily)  
**Type**: Numeric input  
**Range**: 0 - 30 days  
**Default**: 10 days  
**Step**: 1

**Description**:  
Days to look ahead after a crossing to verify MA conditions are met. This parameter only applies to daily view.

**Purpose**:  
Sometimes MA conditions develop shortly after a crossing rather than exactly at the crossing date. This parameter allows the system to capture these signals.

**Technical Logic**:
```
Crossing detected: Day X
Validation window: Day X to Day (X + lookahead)
Check: Are MA conditions met for threshold% of days in this window?
```

**Special Case**:  
Set to **0** to disable lookahead and require MA conditions at the exact crossing date.

**Example** (lookahead = 10, threshold = 0.5):
```
Crossing: Day 100
Validation: Days 100-110 (11 days)
MA conditions met: 7 days
Result: 7/11 = 63.6% > 50% → Signal VALID
```

**Recommendation**:
- **Strict signals**: 0-5 days
- **Balanced**: 10 days (default)
- **Permissive**: 15-20 days

---

## Period-Based Signal Detection (Monthly/Quarterly)

### Crossing Detection Logic

**Important**: For monthly and quarterly views, the system uses **period-end prices** to detect crossings.

**Technical Implementation**:

1. **Price Aggregation**:
   - Monthly: Last trading day's close of each month
   - Quarterly: Last trading day's close of each quarter

2. **MA Alignment**:
   - MA value taken at the period end date
   - Ensures fair comparison between price and MA

3. **Crossing Detection**:
   ```
   Crossing occurs when:
   - Period Open Price >= MA value (at period end)
   AND
   - Period Close Price < MA value (at period end)
   ```

**Rationale**:  
Using period-end prices for both price and MA ensures consistency. The candlestick represents the full period, and we check if price crossed below MA during that period.

**Example** (Monthly):
```
Month: January 2024
Period: Jan 1 - Jan 31
Candlestick:
  - Open: Jan 1 close = $100
  - Close: Jan 31 close = $95
MA at Jan 31: $97

Evaluation:
  - Open ($100) >= MA ($97) ✓
  - Close ($95) < MA ($97) ✓
  → Crossing detected
```

### Exit Signal Validation (Monthly/Quarterly)

**Critical Logic**: When validating exit signals in monthly/quarterly views, the validation period runs from **the crossing date to the end of the period**.

**Implementation Details**:

1. **Identify Crossing**:
   - Detected at period level (e.g., January 2024)
   - Period end date: January 31, 2024

2. **Find Actual Crossing Day**:
   - Search daily data within the period
   - Find specific day when price crossed below MA
   - Example: Crossing occurred on January 15, 2024

3. **Validation Window**:
   - Start: Crossing day (January 15)
   - End: Period end date (January 31)
   - Duration: 17 days in this example

4. **Check MA Conditions**:
   - Count how many days have both:
     * Flat long MA (below flat threshold)
     * Decreasing short MA (below decreasing threshold)
   - Calculate percentage: days_met / total_days

5. **Apply Threshold**:
   ```
   If percentage >= MA_condition_threshold:
       Signal is VALID
   Else:
       Signal is REJECTED
   ```

**Example Validation** (Monthly, threshold = 0.5):
```
Period: January 2024 (monthly candlestick)
Crossing detected in this period

Step 1: Find exact crossing day in daily data
  → January 15, 2024

Step 2: Define validation window
  → January 15 to January 31 (17 days)

Step 3: Check MA conditions for each day
  Jan 15: Flat=Yes, Decreasing=Yes ✓
  Jan 16: Flat=Yes, Decreasing=Yes ✓
  Jan 17: Flat=No,  Decreasing=Yes ✗
  ...
  Jan 31: Flat=Yes, Decreasing=Yes ✓
  
  Result: 12 days met conditions out of 17 days

Step 4: Calculate percentage
  → 12 / 17 = 70.6%

Step 5: Compare to threshold (50%)
  → 70.6% > 50% → Signal VALID
```

**Key Insight**:  
This validation ensures that the unfavorable MA conditions (flat long MA + decreasing short MA) persist through the majority of the period, not just occurring briefly at the crossing point.

---

## Re-Entry Signal Parameters

### Bollinger Band Distance for Re-Entry

**Parameter**: BB Distance for Re-Entry (%)  
**Type**: Numeric input  
**Range**: 0 - 50%  
**Default**: 10%  
**Step**: 5

**Description**:  
Maximum distance from the lower Bollinger Band for a re-entry signal to be valid. Re-entry signals (candlestick patterns) must occur within this percentage of the lower Bollinger Band.

**Technical Definition**:
```
band_distance = (price - lower_BB) / lower_BB * 100
If band_distance <= threshold → Signal can be valid
```

**Rationale**:  
Re-entry signals are most reliable when price is near the lower Bollinger Band, indicating oversold conditions. This parameter ensures signals occur in the appropriate price zone.

**Effect**:
- **Lower values** (5-10%): More restrictive, only near lower band
- **Higher values** (15-25%): More permissive, farther from band
- **Very high values** (30-50%): May include signals far from oversold zone

**Typical Range**: 5-15%

**Recommendation**:
- **Standard approach**: 10% (default)
- **Stricter entries**: 5-7%
- **More opportunities**: 15-20%

---

### Re-Entry Signal Types

**Parameter**: Re-Entry Signals checkboxes  
**Type**: Multi-select  
**Default**: All enabled (Bullish Engulfing, Hammer, Morning Star)

**Description**:  
Candlestick patterns that signal potential re-entry points when price is below MA and near lower Bollinger Band.

**Available Patterns**:

1. **Bullish Engulfing**:
   - **Definition**: Green candle completely engulfs previous red candle
   - **Body**: Current candle body must contain entire previous body
   - **Color**: Previous candle red (down), current candle green (up)
   - **Interpretation**: Strong reversal signal, buyers overwhelming sellers

2. **Hammer / Inverted Hammer**:
   - **Definition**: Small body with long lower wick
   - **Wick**: Lower wick ≥ 2× body size
   - **Body position**: Can be at top (hammer) or bottom (inverted)
   - **Interpretation**: Failed selling pressure, potential reversal

3. **Morning Star**:
   - **Definition**: Three-candle reversal pattern
   - **Candle 1**: Large red candle (downtrend)
   - **Candle 2**: Small body (indecision)
   - **Candle 3**: Large green candle (reversal)
   - **Interpretation**: Strong trend reversal signal

**Selection Strategy**:
- **All enabled**: Maximum signals, some may be weaker
- **Engulfing + Morning Star**: Strong patterns only
- **Hammer only**: Focus on wick patterns

**Recommendation**:  
Start with all enabled, then refine based on backtesting results for your specific tickers.

---

### Maximum Re-Entry Signals per Zone

**Parameter**: Max Re-Entry Signals per Zone  
**Type**: Numeric input  
**Range**: 1 - 20  
**Default**: 1  
**Step**: 1

**Description**:  
Number of re-entry signals to wait for before marking the zone as complete. This affects how quickly zones end and can filter out premature signals.

**Values**:
- **1**: Zone ends at first signal (default)
- **2-3**: Wait for confirmation
- **4+**: Multiple entry opportunities, longer zones

**Trading Implications**:

**Value = 1** (First signal):
- Most responsive
- Captures earliest entry
- May include false signals

**Value = 3** (Third signal):
- More confirmation
- Filters weak signals
- May miss early moves

**Example** (max = 3):
```
Exit signal: Day 100
Price below MA, near lower BB

Day 105: Hammer signal → Count = 1 (zone continues)
Day 112: Engulfing signal → Count = 2 (zone continues)
Day 118: Morning star signal → Count = 3 (zone ends, re-enter)
```

**Recommendation**:
- **Quick entries**: 1 (default)
- **Confirmed entries**: 2-3
- **Multiple opportunities**: 3-5

---

## Zone Display Options

### Display Zones Checkboxes

**Parameter**: Display Zones  
**Type**: Multi-select  
**Default**: Exit-to-Reentry Candlestick (Green), Exit-to-Reentry MA crossing (Orange)

**Description**:  
Colored background zones on the chart showing different market conditions.

**Available Zones**:

1. **Below MA (Red)**:
   - Shows all periods when price is below the long MA
   - Indicates weaker trend conditions
   - Not necessarily an exit signal (requires MA conditions too)

2. **Exit-to-Reentry Candlestick (Green)**:
   - From exit signal to candlestick re-entry signal
   - Represents "out of market" periods using candlestick strategy
   - Conservative approach: wait for strong reversal patterns

3. **Exit-to-Reentry MA Crossing (Orange)**:
   - From exit signal to price crossing back above MA
   - Represents potential early re-entry points
   - More aggressive: re-enter as soon as price recovers above MA

**Usage**:
- **Red zones**: Understanding price position relative to MA
- **Green zones**: Main strategy zones (out of market)
- **Orange zones**: Alternative re-entry timing (earlier than green)

**Visual Interpretation**:
- Clear zones: In market position
- Shaded zones: Out of market (cash position)
- Zone color indicates re-entry type used

---

## Trading Strategy Selector

### Strategy Type

**Parameter**: Trading Strategy  
**Type**: Radio buttons  
**Default**: MA crossing + Candlestick (Orange and green)

**Description**:  
Determines which re-entry method to use.

**Options**:

1. **Candlesticks only (Green)**:
   - **Re-entry trigger**: Only candlestick patterns
   - **Approach**: Conservative
   - **Waiting period**: Until strong reversal pattern appears
   - **Risk**: Lower (more confirmation)
   - **Opportunity**: May miss early moves

2. **MA crossing + Candlestick (Orange and green)**:
   - **Re-entry trigger**: Whichever comes first:
     * Price crosses back above MA (orange zones), OR
     * Candlestick pattern appears (green zones)
   - **Approach**: Aggressive
   - **Waiting period**: Shorter
   - **Risk**: Higher (less confirmation)
   - **Opportunity**: Captures early recoveries

**Zone Behavior**:

**Green strategy** (Candlesticks only):
- All zones are green
- End only on candlestick signals
- May have longer out-of-market periods

**Orange strategy** (MA + Candlesticks):
- Orange zones: Exit to MA crossing
- Green zones: MA crossing to candlestick signal
- Provides two entry opportunities
- Generally shorter out-of-market periods

**Recommendation**:
- **Conservative traders**: Green (candlesticks only)
- **Balanced traders**: Orange (default)
- **Aggressive traders**: Orange with lower thresholds

---

## Relative Strength Analysis

### Filter by Metric

**Parameter**: RS Filter dropdown  
**Type**: Selection  
**Default**: All Tickers

**Description**:  
Filter the relative strength table based on performance metrics.

**Available Filters**:
- **All Tickers**: Show all configured tickers
- **6M Performance > 0%**: Only tickers with positive 6-month returns
- **12M Performance > 0%**: Only tickers with positive 12-month returns
- **Avg Performance > 0%**: Average of 6M and 12M positive
- **Levy RS > 0%**: Levy Relative Strength indicator positive
- **6M Performance < 0%**: Only tickers with negative 6-month returns
- **12M Performance < 0%**: Only tickers with negative 12-month returns

**Purpose**:  
Quickly identify tickers with strongest or weakest momentum, aligning with Cortés' principle of selecting sectors/regions with superior performance.

**Metrics Explained**:

1. **6M Performance (%)**: Simple return over last 6 months
2. **12M Performance (%)**: Simple return over last 12 months
3. **Avg Performance (%)**: Average of 6M and 12M returns
4. **Levy RS (%)**: Relative strength calculation based on Levy methodology

**Usage in Strategy**:  
According to Cortés, focus on tickers with strongest positive momentum (highest average performance). Avoid sectors underperforming the broad market.

---

## Parameter Interaction Effects

### Exit Signal Generation

Exit signals require **ALL** of the following:
1. Price crosses below long MA
2. Long MA is flat (rate of change < flat threshold)
3. Short MA is decreasing (rate of change < decreasing threshold)
4. MA conditions persist for specified percentage of validation period

Adjusting any parameter changes signal frequency:
- **Stricter** (fewer signals): Lower thresholds, higher MA condition percentage
- **Looser** (more signals): Higher thresholds, lower MA condition percentage

### Re-Entry Signal Generation

Re-entry signals require **ALL** of the following:
1. Price is below long MA
2. Price is within specified distance of lower Bollinger Band
3. Selected candlestick pattern appears
4. (Optional) Price has crossed back above MA (if orange strategy selected)

### Signal Timing

**Daily View**:
- Most responsive
- Precise entry/exit timing
- Requires lookahead and smoothing parameters

**Monthly/Quarterly View**:
- Reduced noise
- Broader perspective
- Uses period-end validation logic
- Better for long-term strategy

---

## Best Practices

### Starting Configuration

For users new to the system, start with:
- **Period**: Monthly
- **MA Period**: 40M/20M
- **Flat Long MA**: 0.025
- **Decreasing Short MA**: 0.0
- **MA Condition Threshold**: 0.5
- **BB Distance**: 10%
- **Max Signals**: 1
- **Strategy**: Orange (MA + Candlesticks)

### Optimization Process

1. **Analyze historical signals**: Review past signals on your tickers
2. **Adjust one parameter at a time**: Understand individual effects
3. **Validate with backtesting**: Check signal quality and frequency
4. **Consider transaction costs**: More signals = more costs
5. **Balance sensitivity vs. noise**: Find optimal threshold levels

### Parameter Relationships

**Related Parameters**:
- Flat threshold ↔ Decreasing threshold: Both affect exit sensitivity
- MA period ↔ Flat/decreasing thresholds: Longer periods need different thresholds
- Period (daily/monthly) ↔ Lookahead: Daily needs lookahead, monthly uses period logic
- BB distance ↔ Max signals: Tighter distance needs lower max signal count

**Consistency Principle**:  
Maintain consistent relative strictness across all parameters. Don't combine very strict exit criteria with very loose re-entry criteria, or vice versa.

---

## Troubleshooting

### Too Many Signals

**Symptoms**: Frequent entries and exits, high transaction costs

**Solutions**:
- Increase MA condition threshold (0.5 → 0.7)
- Lower flat/decreasing MA thresholds (stricter)
- Increase BB distance requirement (stricter)
- Use monthly instead of daily view

### Too Few Signals

**Symptoms**: Long periods without any signals, missing opportunities

**Solutions**:
- Decrease MA condition threshold (0.5 → 0.3)
- Raise flat/decreasing MA thresholds (more permissive)
- Decrease BB distance requirement (more permissive)
- Enable all re-entry patterns
- Use orange strategy (MA + candlesticks)

### Delayed Signals

**Symptoms**: Signals occur after obvious trend changes

**Solutions**:
- Use 20M/10M MA period (faster)
- Decrease smoothing window (daily view)
- Reduce MA condition threshold
- Enable orange strategy for earlier re-entry

### False Signals

**Symptoms**: Signals quickly reversed, whipsaws

**Solutions**:
- Use 40M/20M MA period (more stable)
- Increase smoothing window (daily view)
- Increase MA condition threshold
- Use monthly/quarterly view
- Increase max signals per zone (more confirmation)

---

## Summary

Understanding these parameters allows you to customize the trading strategy to your:
- Risk tolerance
- Trading frequency preference
- Market conditions
- Specific tickers being traded

Start with defaults, observe behavior, and adjust systematically based on your analysis and goals.
