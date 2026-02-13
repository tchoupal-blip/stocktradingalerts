# Stock Trading Alerts

A Python tool that scans all S&P 500 stocks for strong technical buy/sell signals and prints color-coded alerts to the console.

## Technical Indicators

| Indicator | Buy Signal | Sell Signal |
|---|---|---|
| RSI (14) | RSI < 30 (oversold) | RSI > 70 (overbought) |
| MACD | MACD crosses above signal line | MACD crosses below signal line |
| Volume Spike | Volume > 2x 20-day avg | — |
| Golden/Death Cross | 50-SMA crosses above 200-SMA | 50-SMA crosses below 200-SMA |
| EMA Crossover | 12-EMA crosses above 26-EMA | 12-EMA crosses below 26-EMA |
| Bollinger Bands | Price closes below lower band | Price closes above upper band |
| Stochastic Oscillator | %K < 20 (oversold) | %K > 80 (overbought) |
| ADX + Directional | +DI crosses above -DI (ADX > 25) | -DI crosses above +DI (ADX > 25) |
| CCI (20) | CCI < -100 | CCI > 100 |
| Williams %R | %R < -80 (oversold) | %R > -20 (overbought) |

A stock is flagged when **2 or more indicators** fire simultaneously (configurable).

## Signal Strength Scoring

Each indicator returns a strength value (0.0–1.0) based on how extreme the reading is. These are aggregated into an overall score out of 10. Alerts are ranked strongest-first so the most compelling signals appear at the top.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python run.py                   # Default: 2+ signals, 365-day lookback
python run.py --min-signals 5   # Recommended: high-conviction alerts only
python run.py --min-signals 1   # Lower threshold for more alerts
python run.py --days 730        # 2-year lookback period
```

### Recommended `--min-signals` values

With 10 indicators, the threshold controls how selective the scan is:

| Value | Result | Use Case |
|---|---|---|
| 1–2 | 100+ alerts | Broad market overview |
| 3–5 | 15–100 alerts | Balanced filtering (recommended) |
| 6 | ~15 alerts | High-conviction signals only |
| 7+ | 0 alerts | Extremely rare, near-perfect setups |

## Example Output

```
=============================================
  STOCK TRADING ALERTS — 2026-02-13
=============================================

BUY SIGNALS:
  CPRT  | [ 3.4/10] Volume 2.2x avg, Price below lower BB, Stochastic %K: 3.9, CCI: -296.4, Williams %R: -96.1
  DASH  | [ 3.2/10] RSI: 18.2 (oversold), Volume 2.2x avg, Price below lower BB, Stochastic %K: 0.8, CCI: -196.1, Williams %R: -99.2
  FOXA  | [ 3.2/10] RSI: 15.6 (oversold), Volume 2.5x avg, Price below lower BB, Stochastic %K: 2.2, CCI: -199.3, Williams %R: -97.8

SELL SIGNALS:
  FICO  | [ 2.6/10] RSI: 79.8 (overbought), Price above upper BB, Stochastic %K: 95.4, CCI: 183.2, Williams %R: -4.6

Summary: 131 buy alert(s), 162 sell alert(s) out of 502 stocks scanned
```

## Configuration

Edit `config.py` to adjust thresholds:

- RSI oversold/overbought levels
- Volume spike multiplier
- Bollinger Bands period and standard deviation
- Stochastic Oscillator period and levels
- ADX period and trend strength threshold
- CCI period and levels
- Williams %R period and levels
- SMA and EMA periods
- Minimum signals required to trigger an alert
- Historical data lookback period

## Data Sources

- **yfinance** — stock price and volume history (free, no API key needed)
- **Wikipedia** — S&P 500 ticker list
