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
    strength: float = 1.0  # 0.0–1.0 indicating how extreme the signal is


def check_rsi(df: pd.DataFrame) -> Signal | None:
    """Check RSI for oversold/overbought conditions."""
    rsi = ta.momentum.RSIIndicator(df["Close"], window=config.RSI_PERIOD).rsi()
    if rsi.empty:
        return None
    latest = rsi.iloc[-1]
    if pd.isna(latest):
        return None
    if latest < config.RSI_OVERSOLD:
        # Strength: RSI 30 -> 0.0, RSI 0 -> 1.0
        strength = min(1.0, (config.RSI_OVERSOLD - latest) / config.RSI_OVERSOLD)
        return Signal("RSI", "buy", f"RSI: {latest:.1f} (oversold)", strength)
    if latest > config.RSI_OVERBOUGHT:
        # Strength: RSI 70 -> 0.0, RSI 100 -> 1.0
        strength = min(1.0, (latest - config.RSI_OVERBOUGHT) / (100 - config.RSI_OVERBOUGHT))
        return Signal("RSI", "sell", f"RSI: {latest:.1f} (overbought)", strength)
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
        # Strength based on how far MACD moved above signal
        strength = min(1.0, abs(curr_diff) / (abs(prev_diff) + abs(curr_diff) + 1e-9))
        return Signal("MACD", "buy", "MACD crossover UP", strength)
    if prev_diff >= 0 > curr_diff:
        strength = min(1.0, abs(curr_diff) / (abs(prev_diff) + abs(curr_diff) + 1e-9))
        return Signal("MACD", "sell", "MACD crossover DOWN", strength)
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
        # Strength: 2x -> 0.0, 5x+ -> 1.0
        strength = min(1.0, (ratio - config.VOLUME_SPIKE_MULTIPLIER) / 3.0)
        return Signal("Volume", "buy", f"Volume {ratio:.1f}x avg", strength)
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
        return Signal("SMA Cross", "buy", f"Golden Cross ({config.SMA_SHORT}/{config.SMA_LONG} SMA)", 0.8)
    if prev_diff >= 0 > curr_diff:
        return Signal("SMA Cross", "sell", f"Death Cross ({config.SMA_SHORT}/{config.SMA_LONG} SMA)", 0.8)
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
        return Signal("EMA Cross", "buy", "EMA crossover UP", 0.6)
    if prev_diff >= 0 > curr_diff:
        return Signal("EMA Cross", "sell", "EMA crossover DOWN", 0.6)
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
        band_width = upper - lower if upper != lower else 1.0
        strength = min(1.0, (lower - close) / (band_width * 0.5))
        return Signal("Bollinger", "buy", f"Price below lower BB ({close:.2f} < {lower:.2f})", strength)
    if close > upper:
        band_width = upper - lower if upper != lower else 1.0
        strength = min(1.0, (close - upper) / (band_width * 0.5))
        return Signal("Bollinger", "sell", f"Price above upper BB ({close:.2f} > {upper:.2f})", strength)
    return None


def check_stochastic(df: pd.DataFrame) -> Signal | None:
    """Check Stochastic Oscillator for oversold/overbought."""
    stoch = ta.momentum.StochasticOscillator(
        df["High"], df["Low"], df["Close"],
        window=config.STOCH_PERIOD, smooth_window=config.STOCH_SMOOTH,
    )
    k = stoch.stoch().iloc[-1]
    if pd.isna(k):
        return None
    if k < config.STOCH_OVERSOLD:
        strength = min(1.0, (config.STOCH_OVERSOLD - k) / config.STOCH_OVERSOLD)
        return Signal("Stochastic", "buy", f"Stochastic %K: {k:.1f} (oversold)", strength)
    if k > config.STOCH_OVERBOUGHT:
        strength = min(1.0, (k - config.STOCH_OVERBOUGHT) / (100 - config.STOCH_OVERBOUGHT))
        return Signal("Stochastic", "sell", f"Stochastic %K: {k:.1f} (overbought)", strength)
    return None


def check_adx(df: pd.DataFrame) -> Signal | None:
    """Check ADX for strong trend with +DI/-DI crossover."""
    adx_ind = ta.trend.ADXIndicator(
        df["High"], df["Low"], df["Close"], window=config.ADX_PERIOD,
    )
    adx = adx_ind.adx().iloc[-1]
    plus_di = adx_ind.adx_pos()
    minus_di = adx_ind.adx_neg()
    if len(plus_di) < 2:
        return None
    if pd.isna(adx) or adx < config.ADX_THRESHOLD:
        return None
    prev_diff = plus_di.iloc[-2] - minus_di.iloc[-2]
    curr_diff = plus_di.iloc[-1] - minus_di.iloc[-1]
    if pd.isna(prev_diff) or pd.isna(curr_diff):
        return None
    if prev_diff <= 0 < curr_diff:
        # Strength based on ADX value: 25 -> 0.0, 50+ -> 1.0
        strength = min(1.0, (adx - config.ADX_THRESHOLD) / 25.0)
        return Signal("ADX", "buy", f"ADX: {adx:.1f}, +DI crossed above -DI", strength)
    if prev_diff >= 0 > curr_diff:
        strength = min(1.0, (adx - config.ADX_THRESHOLD) / 25.0)
        return Signal("ADX", "sell", f"ADX: {adx:.1f}, -DI crossed above +DI", strength)
    return None


def check_cci(df: pd.DataFrame) -> Signal | None:
    """Check CCI for oversold/overbought conditions."""
    cci = ta.trend.CCIIndicator(
        df["High"], df["Low"], df["Close"], window=config.CCI_PERIOD,
    ).cci()
    latest = cci.iloc[-1]
    if pd.isna(latest):
        return None
    if latest < config.CCI_OVERSOLD:
        # Strength: -100 -> 0.0, -300+ -> 1.0
        strength = min(1.0, (abs(latest) - abs(config.CCI_OVERSOLD)) / 200.0)
        return Signal("CCI", "buy", f"CCI: {latest:.1f} (oversold)", strength)
    if latest > config.CCI_OVERBOUGHT:
        strength = min(1.0, (latest - config.CCI_OVERBOUGHT) / 200.0)
        return Signal("CCI", "sell", f"CCI: {latest:.1f} (overbought)", strength)
    return None


def check_williams_r(df: pd.DataFrame) -> Signal | None:
    """Check Williams %R for oversold/overbought conditions."""
    wr = ta.momentum.WilliamsRIndicator(
        df["High"], df["Low"], df["Close"], lbp=config.WILLIAMS_PERIOD,
    ).williams_r()
    latest = wr.iloc[-1]
    if pd.isna(latest):
        return None
    if latest < config.WILLIAMS_OVERSOLD:
        # Strength: -80 -> 0.0, -100 -> 1.0
        strength = min(1.0, (abs(latest) - abs(config.WILLIAMS_OVERSOLD)) / 20.0)
        return Signal("Williams %R", "buy", f"Williams %R: {latest:.1f} (oversold)", strength)
    if latest > config.WILLIAMS_OVERBOUGHT:
        strength = min(1.0, (latest - config.WILLIAMS_OVERBOUGHT) / 20.0)
        return Signal("Williams %R", "sell", f"Williams %R: {latest:.1f} (overbought)", strength)
    return None


ALL_CHECKS = [
    check_rsi, check_macd, check_volume_spike, check_sma_cross,
    check_ema_cross, check_bollinger_bands, check_stochastic,
    check_adx, check_cci, check_williams_r,
]


def analyze(df: pd.DataFrame) -> list[Signal]:
    """Run all indicator checks on a ticker DataFrame and return fired signals."""
    signals: list[Signal] = []
    for check in ALL_CHECKS:
        result = check(df)
        if result is not None:
            signals.append(result)
    return signals


def total_strength(signals: list[Signal]) -> float:
    """Compute aggregate strength score: sum of individual strengths scaled to 0–10."""
    if not signals:
        return 0.0
    raw = sum(s.strength for s in signals)
    # Scale: each signal contributes up to 1.0, max 10 indicators
    return round(raw / len(ALL_CHECKS) * 10, 1)
