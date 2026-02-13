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

A stock is flagged when **2 or more indicators** fire simultaneously (configurable).

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python run.py                   # Default: 2+ signals, 365-day lookback
python run.py --min-signals 1   # Lower threshold for more alerts
python run.py --days 730        # 2-year lookback period
```

## Example Output

```
=============================================
  STOCK TRADING ALERTS — 2026-02-13
=============================================

BUY SIGNALS:
  ABNB  | RSI: 27.9 (oversold), Volume 2.2x avg, Price below lower BB (115.96 < 116.16)
  ADP   | RSI: 14.0 (oversold), Volume 2.6x avg, Price below lower BB (209.96 < 213.22)
  AKAM  | MACD crossover UP, Volume 3.1x avg

SELL SIGNALS:
  WFC   | MACD crossover DOWN, EMA crossover DOWN

Summary: 37 buy alert(s), 40 sell alert(s) out of 502 stocks scanned
```

## Configuration

Edit `config.py` to adjust thresholds:

- RSI oversold/overbought levels
- Volume spike multiplier
- Bollinger Bands period and standard deviation
- SMA and EMA periods
- Minimum signals required to trigger an alert
- Historical data lookback period

## Data Sources

- **yfinance** — stock price and volume history (free, no API key needed)
- **Wikipedia** — S&P 500 ticker list
