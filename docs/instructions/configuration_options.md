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

## Exit Signal Confirmation (All Views)

### Confirmation Window

**Parameter**: Confirmation Window (All Views)  
**Type**: Numeric input  
**Range**: 5 - 60 days  
**Default**: 20 days  
**Step**: 5

**Description**:  
Size of the sliding window (in trading days) used to check MA conditions after a crossing. The exit signal is confirmed when MA conditions are sustained for the threshold percentage of this window.

**Applies to**: Daily, Monthly, and Quarterly views (unified behavior)

**Technical Logic**:
After a price crossing is detected:
1. Start checking daily from the crossing date
2. Use a sliding N-day window
3. For each day, check if MA conditions are met for ≥X% of the last N days
4. Check if price is still below MA
5. When both conditions are met, the exit signal is confirmed

**Effect**:
- **Lower values** (10-15 days): Faster confirmation, may catch early signals
- **Medium values** (20-25 days): Balanced approach (default)
- **Higher values** (30-40 days): Requires sustained conditions, fewer false signals

**Example** (Window = 20 days):
```
Day 0: Crossing detected (price drops below MA)
Days 1-19: Checking... accumulating data
Day 20: First full window check
  - Look back at days 1-20
  - Count days with MA conditions met
  - If ≥ threshold% → Can confirm (if price still < MA)
Day 21: Rolling window
  - Look back at days 2-21
  - Recalculate percentage
  - Continue checking...
```

**Recommendation**: 15-30 days for most applications

---

### Confirmation Threshold

**Parameter**: Confirmation Threshold (%)  
**Type**: Numeric input  
**Range**: 0 - 100%  
**Default**: 60%  
**Step**: 5

**Description**:  
Percentage of days within the confirmation window that must have MA conditions met to confirm an exit signal. Higher values require more sustained unfavorable conditions.

**Applies to**: Daily, Monthly, and Quarterly views (unified behavior)

**Technical Definition**:
```
For each potential confirmation day:
  window_days = last N days (confirmation window)
  
  For each day in window:
    Check if BOTH conditions are true:
      - Long MA is flat (change < flat threshold)
      - Short MA is decreasing (change < decreasing threshold)
  
  condition_percentage = days_with_conditions / window_size
  
  If condition_percentage >= confirmation_threshold
  AND price < MA on confirmation day
  THEN signal is CONFIRMED
```

**Effect**:
- **Lower values** (40-50%): More permissive, catches more signals
- **Medium values** (60-70%): Balanced approach (default)
- **Higher values** (80-100%): Very strict, only sustained conditions

**Example** (Threshold = 60%, Window = 20):
```
Crossing on Day 0

Day 20 check:
  - Days 1-20 examined
  - Days with MA conditions: 13 out of 20
  - Percentage: 13/20 = 65%
  - 65% ≥ 60% ✓
  - Price < MA ✓
  → Signal CONFIRMED
```

**Natural Limit**:
The exit signal must be confirmed **before the zone ends**:
- **Orange zones**: End when price crosses back above MA
- **Green zones**: End at Nth re-entry signal

If conditions aren't sustained before the zone naturally ends, the signal is rejected as a false alarm.

**Recommendation**:
- **Standard approach**: 60% (default)
- **More signals**: 50-55%
- **Higher confidence**: 70-80%

---

### Progressive Confirmation Process

**How it works** (same for all views):

**Phase 1: Crossing Detected**
- Price drops below MA
- Zone starts (background shading begins)
- Candlesticks remain normal colored (not officially "out" yet)

**Phase 2: Daily Checking**
System checks each trading day after crossing:
- Calculate: What % of last N days (confirmation window) had MA conditions?
- Check: Is price still below MA today?
- Continue until either:
  * Conditions are met → Confirm signal
  * Zone ends (re-entry occurs) → Reject signal

**Phase 3: Signal Confirmed**
When both conditions are met:
- Gray exit signal line appears on chart
- Candlesticks become shaded (officially "out of market")
- Investor executes or completes selling

**Phase 4: Zone Ends**
When re-entry occurs:
- **Orange strategy**: Price crosses back above MA
- **Green strategy**: Nth candlestick pattern appears
- Background shading ends
- Candlesticks return to normal colors

**Complete Example** (Window=20, Threshold=60%):
```
Sep 15: Price crosses below MA
  → Zone starts (light background shading)
  → Candlesticks still normal colored
  → Start daily checking

Sep 16-Oct 3: Checking...
  → Not enough days yet (window = 20)
  → Keep accumulating

Oct 4: First possible confirmation (Day 20)
  → Check last 20 days (Sep 15-Oct 4)
  → MA conditions met: 13 days
  → 13/20 = 65% ≥ 60% ✓
  → Price < MA ✓
  → CONFIRMED! Gray line appears on Oct 4
  → Candlesticks from Oct 4 onward become shaded

Oct 4-Dec 3: Out of market period
  → Shaded candlesticks
  → Background zone shading continues
  → Waiting for re-entry signal

Dec 3: Re-entry signal (candlestick pattern)
  → Zone ends
  → Shading stops
  → Back in market
```

**Key Benefits**:
1. **Unified approach**: Same logic for daily, monthly, quarterly
2. **Natural limits**: No arbitrary time cutoffs
3. **Adaptive**: Works regardless of when crossing occurs in a period
4. **Realistic**: Allows conditions to develop after crossing
5. **Self-regulating**: Invalid signals automatically rejected when zone ends

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

**Important**: Each zone gets its own fresh count - signals from one zone cannot be reused by subsequent zones.

**Values**:
- **1**: Zone ends at first signal (default)
- **2-3**: Wait for confirmation
- **4+**: Multiple entry opportunities, longer zones

**Trading Implications**:

**Value = 1** (First signal):
- Most responsive
- Captures earliest entry
- May include false signals
- Suitable for aggressive traders

**Value = 3** (Third signal):
- More confirmation
- Filters weak signals
- May miss early moves
- Suitable for conservative traders

**Example** (max = 3):
```
Exit signal: Day 100
Price below MA, near lower BB

Day 105: Hammer signal → Count = 1 (zone continues)
Day 112: Engulfing signal → Count = 2 (zone continues)
Day 118: Morning star signal → Count = 3 (zone ends, re-enter)
```

**Signal Uniqueness**:
Signals used by one zone cannot be reused by later zones. This ensures:
- Each zone has its own distinct signals
- No overlapping or shared entry points
- Clear separation between trading periods

**Hover Information**:
When you hover over a zone, you'll see:
```
Green Zone
Start: 2008-09-15
Exit: 2008-10-09
End: 2008-12-03 (4th Re-Entry Signal)
```
The ordinal (1st, 2nd, 3rd, 4th, etc.) indicates which signal number ended the zone.

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
   - Useful for understanding overall price position

2. **Exit-to-Reentry Candlestick (Green)**:
   - From exit signal to candlestick re-entry signal
   - Represents "out of market" periods using candlestick strategy
   - Conservative approach: wait for strong reversal patterns
   - Zone ends when Nth candlestick signal appears

3. **Exit-to-Reentry MA Crossing (Orange)**:
   - From exit signal to price crossing back above MA
   - Represents potential early re-entry points
   - More aggressive: re-enter as soon as price recovers above MA
   - Zone ends when price crosses MA upward

**Zone Visualization Details**:

**Background Shading**:
- Begins at crossing date (when price drops below MA)
- Continues until re-entry point
- Shows the "danger period" or "out of market" time

**Candlestick Shading**:
- Begins at exit signal confirmation date (not crossing date)
- Shows when you're officially "out of market"
- More transparent colors indicate out-of-market candlesticks

**Exit Signal Line** (gray vertical line):
- Appears at confirmation date
- Extends from MA value down to chart bottom
- Marks the moment when conditions are confirmed

**Hover Information**:
Hover over any zone to see:
- **Start date**: When price crossed below MA
- **Exit date**: When exit signal was confirmed
- **End date**: When to re-enter
- **Re-entry type**: "Nth Re-Entry Signal" or "MA Crossing"

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
Determines which re-entry method to use and which comes first.

**Options**:

1. **Candlesticks only (Green)**:
   - **Re-entry trigger**: Only candlestick patterns
   - **Approach**: Conservative
   - **Waiting period**: Until strong reversal pattern appears
   - **Risk**: Lower (more confirmation)
   - **Opportunity**: May miss early moves
   - **All zones appear green**

2. **MA crossing + Candlestick (Orange and green)**:
   - **Re-entry trigger**: Whichever comes first:
     * Price crosses back above MA (orange zones), OR
     * Candlestick pattern appears (green zones)
   - **Approach**: Aggressive
   - **Waiting period**: Shorter
   - **Risk**: Higher (less confirmation)
   - **Opportunity**: Captures early recoveries
   - **Zones are orange or green depending on which signal comes first**

**Zone Behavior**:

**Green strategy** (Candlesticks only):
- All zones are green
- End only on candlestick signals
- May have longer out-of-market periods
- More confirmation required

**Orange strategy** (MA + Candlesticks):
- Some zones are orange (MA crossing came first)
- Some zones are green (candlestick signal came first)
- Provides two entry opportunities per exit
- Generally shorter out-of-market periods
- More responsive to market recovery

**Decision Logic** (Orange strategy):
For each exit signal:
1. Detect green zone end (Nth candlestick signal)
2. Detect orange zone end (MA crossing)
3. Use whichever occurs FIRST

**Example**:
```
Exit signal: Sep 15

Green zone would end: Dec 3 (3rd candlestick signal)
Orange zone would end: Nov 10 (MA crossing)

Result: Orange zone used (Nov 10 < Dec 3)
```

**Recommendation**:
- **Conservative traders**: Green (candlesticks only)
- **Balanced traders**: Orange (default)
- **Aggressive traders**: Orange with lower thresholds

---

## Relative Strength Analysis

### Reference Ticker (Benchmark)

**Parameter**: RS Reference dropdown  
**Type**: Selection  
**Default**: URTH

**Description**:  
Select benchmark ticker for Levy RS calculation. Levy RS shows how much each ticker outperforms (positive) or underperforms (negative) the benchmark.

**Common Benchmarks**:
- **URTH**: Global markets (most comprehensive)
- **SPY**: S&P 500 (US large cap)
- **VTI**: Total US market

**Note**: The benchmark itself will show 0% Levy RS by definition.

---

### Calculation Currency

**Parameter**: Calculation Currency dropdown  
**Type**: Selection  
**Default**: USD

**Description**:  
Currency for calculating all performance metrics. All tickers will be converted to this currency before calculating returns.

**Available Currencies**:
- **USD**: US Dollar
- **CHF**: Swiss Franc
- **EUR**: Euro
- **GBP**: British Pound

**Purpose**:  
Ensures fair comparison between tickers denominated in different currencies. For example, comparing SMI (CHF) with S&P 500 (USD) requires currency normalization.

---

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
5. **6M Perf Rel. Bench (%)**: 6-month performance relative to benchmark

**Table Sorting**:  
By default, the table is sorted by **6M Performance Relative to Benchmark** (descending), showing the strongest performers first. This aligns with Cortés' principle of focusing on sectors with superior momentum.

Click any column header to re-sort by that metric.

**Usage in Strategy**:  
According to Cortés, focus on tickers with strongest positive momentum (highest average performance). Avoid sectors underperforming the broad market.

---

## Performance Optimization

### Input Debouncing

**Feature**: Automatic 500ms delay on numeric inputs  
**Applies to**: All numeric parameter inputs

**Description**:  
When you adjust numeric parameters (using increment/decrement buttons or typing), the system waits 500ms after your last change before recalculating the chart.

**Debounced Parameters**:
- Confirmation Window
- Confirmation Threshold
- Max Re-Entry Signals per Zone
- Flat Long MA Threshold
- Decreasing Short MA Threshold
- BB Distance for Re-Entry

**Behavior**:

**Without debouncing** (old behavior):
```
Click +1 → Recalculate chart (500ms)
Click +1 → Recalculate chart (500ms)
Click +1 → Recalculate chart (500ms)
Total: 1500ms, 3 calculations
```

**With debouncing** (current):
```
Click +1 → Wait...
Click +1 → Wait...
Click +1 → Wait...
[After 500ms of no changes]
→ Recalculate chart (500ms)
Total: 1000ms, 1 calculation
```

**Benefits**:
- **Faster UI**: Fewer unnecessary calculations
- **More responsive**: Can adjust multiple parameters quickly
- **Better user experience**: No lag when making changes

**Not Debounced** (instant response):
- Ticker selection
- Period selection (Daily/Monthly/Quarterly)
- MA Period (40M/20M vs 20M/10M)
- Checkboxes (signals, zones, strategy)
- Scale selector (Linear/Log)

---

## Parameter Interaction Effects

### Exit Signal Generation

Exit signals require **ALL** of the following:
1. Price crosses below long MA
2. Long MA is flat (rate of change < flat threshold)
3. Short MA is decreasing (rate of change < decreasing threshold)
4. MA conditions persist for specified percentage of confirmation window
5. Price remains below MA at confirmation point

Adjusting any parameter changes signal frequency:
- **Stricter** (fewer signals): Lower MA thresholds, higher confirmation percentage
- **Looser** (more signals): Higher MA thresholds, lower confirmation percentage

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
- Uses same progressive confirmation as monthly/quarterly
- No special parameters needed

**Monthly/Quarterly View**:
- Reduced noise
- Broader perspective
- Uses same progressive confirmation as daily
- Better for long-term strategy

**All views now use the same unified confirmation logic**, making behavior consistent and predictable across time periods.

---

## Best Practices

### Starting Configuration

For users new to the system, start with:
- **Period**: Monthly
- **MA Period**: 40M/20M
- **Flat Long MA**: 0.025
- **Decreasing Short MA**: 0.0
- **Confirmation Window**: 20 days
- **Confirmation Threshold**: 60%
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
- Confirmation window ↔ Confirmation threshold: Work together to filter signals
- BB distance ↔ Max signals: Tighter distance needs lower max signal count

**Consistency Principle**:  
Maintain consistent relative strictness across all parameters. Don't combine very strict exit criteria with very loose re-entry criteria, or vice versa.

---

## Troubleshooting

### Too Many Signals

**Symptoms**: Frequent entries and exits, high transaction costs

**Solutions**:
- Increase confirmation threshold (60% → 70-80%)
- Increase confirmation window (20 → 30 days)
- Lower flat/decreasing MA thresholds (stricter)
- Increase BB distance requirement (stricter)
- Use monthly instead of daily view

### Too Few Signals

**Symptoms**: Long periods without any signals, missing opportunities

**Solutions**:
- Decrease confirmation threshold (60% → 50%)
- Decrease confirmation window (20 → 15 days)
- Raise flat/decreasing MA thresholds (more permissive)
- Decrease BB distance requirement (more permissive)
- Enable all re-entry patterns
- Use orange strategy (MA + candlesticks)

### Delayed Signals

**Symptoms**: Signals occur after obvious trend changes

**Solutions**:
- Use 20M/10M MA period (faster)
- Decrease confirmation window (20 → 10-15 days)
- Reduce confirmation threshold (60% → 50%)
- Enable orange strategy for earlier re-entry

### False Signals

**Symptoms**: Signals quickly reversed, whipsaws

**Solutions**:
- Use 40M/20M MA period (more stable)
- Increase confirmation window (20 → 30 days)
- Increase confirmation threshold (60% → 70-80%)
- Use monthly/quarterly view
- Increase max signals per zone (more confirmation)

### Exit Signals Not Appearing

**Symptoms**: Zone starts (background shading) but no gray exit line appears

**Possible Causes**:
1. **MA conditions not sustained**: Conditions may have been met briefly but not for the required percentage of the confirmation window
2. **Price recovered too quickly**: Zone ended (re-entry occurred) before confirmation
3. **Thresholds too strict**: Combination of high confirmation threshold + strict MA thresholds

**Solutions**:
- Lower confirmation threshold (e.g., 60% → 50%)
- Decrease confirmation window (e.g., 20 → 15 days)
- Raise MA condition thresholds (more permissive)
- Check console output for rejection reasons

---

## Summary

Understanding these parameters allows you to customize the trading strategy to your:
- Risk tolerance
- Trading frequency preference
- Market conditions
- Specific tickers being traded

The unified confirmation approach (same 2 parameters for all views) makes the system:
- **Simpler**: Fewer parameters to manage
- **More intuitive**: Consistent behavior across time periods
- **Self-regulating**: Natural limits prevent artificial cutoffs
- **Adaptive**: Works regardless of crossing timing

Start with defaults, observe behavior, and adjust systematically based on your analysis and goals.