"""Configuration and thresholds for the stock trading alerts scanner."""

# RSI settings
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

# MACD settings
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Volume spike
VOLUME_AVG_PERIOD = 20
VOLUME_SPIKE_MULTIPLIER = 2.0

# Bollinger Bands settings
BB_PERIOD = 20
BB_STD_DEV = 2

# Moving average crossovers
SMA_SHORT = 50
SMA_LONG = 200
EMA_SHORT = 12
EMA_LONG = 26

# Alert thresholds
MIN_SIGNALS = 2  # Minimum simultaneous signals to trigger an alert

# Data fetch settings
LOOKBACK_DAYS = 365
SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
