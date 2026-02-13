"""Technical indicator calculations and signal detection."""

from dataclasses import dataclass

import pandas as pd
import ta

import config


@dataclass
class Signal:
    """A single technical signal for a stock."""
    name: str
    direction: str  # "buy" or "sell"
    detail: str


def check_rsi(df: pd.DataFrame) -> Signal | None:
    """Check RSI for oversold/overbought conditions."""
    rsi = ta.momentum.RSIIndicator(df["Close"], window=config.RSI_PERIOD).rsi()
    if rsi.empty:
        return None
    latest = rsi.iloc[-1]
    if pd.isna(latest):
        return None
    if latest < config.RSI_OVERSOLD:
        return Signal("RSI", "buy", f"RSI: {latest:.1f} (oversold)")
    if latest > config.RSI_OVERBOUGHT:
        return Signal("RSI", "sell", f"RSI: {latest:.1f} (overbought)")
    return None


def check_macd(df: pd.DataFrame) -> Signal | None:
    """Check for MACD / signal line crossover."""
    macd_ind = ta.trend.MACD(
        df["Close"],
        window_fast=config.MACD_FAST,
        window_slow=config.MACD_SLOW,
        window_sign=config.MACD_SIGNAL,
    )
    macd_line = macd_ind.macd()
    signal_line = macd_ind.macd_signal()
    if len(macd_line) < 2:
        return None
    prev_diff = macd_line.iloc[-2] - signal_line.iloc[-2]
    curr_diff = macd_line.iloc[-1] - signal_line.iloc[-1]
    if pd.isna(prev_diff) or pd.isna(curr_diff):
        return None
    if prev_diff <= 0 < curr_diff:
        return Signal("MACD", "buy", "MACD crossover UP")
    if prev_diff >= 0 > curr_diff:
        return Signal("MACD", "sell", "MACD crossover DOWN")
    return None


def check_volume_spike(df: pd.DataFrame) -> Signal | None:
    """Check if latest volume exceeds N× the 20-day average."""
    vol = df["Volume"]
    if len(vol) < config.VOLUME_AVG_PERIOD + 1:
        return None
    avg_vol = vol.iloc[-(config.VOLUME_AVG_PERIOD + 1):-1].mean()
    if avg_vol == 0 or pd.isna(avg_vol):
        return None
    ratio = vol.iloc[-1] / avg_vol
    if ratio >= config.VOLUME_SPIKE_MULTIPLIER:
        return Signal("Volume", "buy", f"Volume {ratio:.1f}x avg")
    return None


def check_sma_cross(df: pd.DataFrame) -> Signal | None:
    """Check for golden cross (buy) or death cross (sell) on SMA 50/200."""
    if len(df) < config.SMA_LONG + 1:
        return None
    sma_short = df["Close"].rolling(window=config.SMA_SHORT).mean()
    sma_long = df["Close"].rolling(window=config.SMA_LONG).mean()
    prev_diff = sma_short.iloc[-2] - sma_long.iloc[-2]
    curr_diff = sma_short.iloc[-1] - sma_long.iloc[-1]
    if pd.isna(prev_diff) or pd.isna(curr_diff):
        return None
    if prev_diff <= 0 < curr_diff:
        return Signal("SMA Cross", "buy", f"Golden Cross ({config.SMA_SHORT}/{config.SMA_LONG} SMA)")
    if prev_diff >= 0 > curr_diff:
        return Signal("SMA Cross", "sell", f"Death Cross ({config.SMA_SHORT}/{config.SMA_LONG} SMA)")
    return None


def check_ema_cross(df: pd.DataFrame) -> Signal | None:
    """Check for EMA 12/26 crossover."""
    if len(df) < config.EMA_LONG + 1:
        return None
    ema_short = ta.trend.EMAIndicator(df["Close"], window=config.EMA_SHORT).ema_indicator()
    ema_long = ta.trend.EMAIndicator(df["Close"], window=config.EMA_LONG).ema_indicator()
    prev_diff = ema_short.iloc[-2] - ema_long.iloc[-2]
    curr_diff = ema_short.iloc[-1] - ema_long.iloc[-1]
    if pd.isna(prev_diff) or pd.isna(curr_diff):
        return None
    if prev_diff <= 0 < curr_diff:
        return Signal("EMA Cross", "buy", "EMA crossover UP")
    if prev_diff >= 0 > curr_diff:
        return Signal("EMA Cross", "sell", "EMA crossover DOWN")
    return None


def check_bollinger_bands(df: pd.DataFrame) -> Signal | None:
    """Check if price closed outside Bollinger Bands."""
    bb = ta.volatility.BollingerBands(
        df["Close"], window=config.BB_PERIOD, window_dev=config.BB_STD_DEV
    )
    upper = bb.bollinger_hband().iloc[-1]
    lower = bb.bollinger_lband().iloc[-1]
    close = df["Close"].iloc[-1]
    if pd.isna(upper) or pd.isna(lower) or pd.isna(close):
        return None
    if close < lower:
        return Signal("Bollinger", "buy", f"Price below lower BB ({close:.2f} < {lower:.2f})")
    if close > upper:
        return Signal("Bollinger", "sell", f"Price above upper BB ({close:.2f} > {upper:.2f})")
    return None


ALL_CHECKS = [check_rsi, check_macd, check_volume_spike, check_sma_cross, check_ema_cross, check_bollinger_bands]


def analyze(df: pd.DataFrame) -> list[Signal]:
    """Run all indicator checks on a ticker DataFrame and return fired signals."""
    signals: list[Signal] = []
    for check in ALL_CHECKS:
        result = check(df)
        if result is not None:
            signals.append(result)
    return signals
