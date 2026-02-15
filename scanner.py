"""Main scanning logic: fetch data, run indicators, format and print alerts."""

import datetime
import io
import sys

import pandas as pd
import requests
import yfinance as yf
from colorama import Fore, Style, init as colorama_init

import config
import indicators


def fetch_sp500_tickers() -> tuple[list[str], dict[str, str]]:
    """Scrape the S&P 500 ticker list and company names from Wikipedia.

    Returns:
        Tuple of (tickers, ticker_to_name) where ticker_to_name maps
        ticker symbols to company names.
    """
    headers = {"User-Agent": "StockTradingAlerts/1.0"}
    resp = requests.get(config.SP500_WIKI_URL, headers=headers)
    resp.raise_for_status()
    tables = pd.read_html(io.StringIO(resp.text))
    df = tables[0]
    tickers = df["Symbol"].tolist()
    names = df["Security"].tolist()
    # Some Wikipedia tickers use dots (e.g. BRK.B) but yfinance expects dashes
    ticker_to_name = {t.replace(".", "-"): n for t, n in zip(tickers, names)}
    tickers = [t.replace(".", "-") for t in tickers]
    return tickers, ticker_to_name


def fetch_price_data(tickers: list[str], days: int) -> dict[str, pd.DataFrame]:
    """Download historical price data for all tickers in a single batch."""
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days)
    print(f"Downloading price data for {len(tickers)} tickers …")
    raw = yf.download(
        tickers,
        start=start.isoformat(),
        end=end.isoformat(),
        group_by="ticker",
        threads=True,
        progress=True,
    )
    result: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        try:
            if len(tickers) == 1:
                df = raw.copy()
            else:
                df = raw[ticker].copy()
            # Drop rows where Close is NaN (delisted / missing data)
            df = df.dropna(subset=["Close"])
            if len(df) >= config.SMA_LONG:
                # Flatten MultiIndex columns if present
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)
                result[ticker] = df
        except (KeyError, TypeError):
            continue
    return result


def get_alerts(
    min_signals: int, days: int, progress_callback=None
) -> tuple[
    list[tuple[str, list[indicators.Signal], float]],  # buy_alerts
    list[tuple[str, list[indicators.Signal], float]],  # sell_alerts
    int,  # total_scanned
    dict[str, str],  # ticker_to_name
]:
    """Run the full scan and return structured alert data.

    Args:
        min_signals: Minimum simultaneous signals to trigger an alert.
        days: Lookback period in days for historical data.
        progress_callback: Optional callable(current, total) for progress updates.

    Returns:
        Tuple of (buy_alerts, sell_alerts, total_scanned, ticker_to_name).
    """
    tickers, ticker_to_name = fetch_sp500_tickers()
    data = fetch_price_data(tickers, days)

    buy_alerts: list[tuple[str, list[indicators.Signal], float]] = []
    sell_alerts: list[tuple[str, list[indicators.Signal], float]] = []

    total_scanned = len(data)
    for i, (ticker, df) in enumerate(data.items()):
        if progress_callback:
            progress_callback(i, total_scanned)
        signals = indicators.analyze(df)
        if len(signals) < min_signals:
            continue
        buy_sigs = [s for s in signals if s.direction == "buy"]
        sell_sigs = [s for s in signals if s.direction == "sell"]
        if len(buy_sigs) >= min_signals:
            score = indicators.total_strength(buy_sigs)
            buy_alerts.append((ticker, buy_sigs, score))
        if len(sell_sigs) >= min_signals:
            score = indicators.total_strength(sell_sigs)
            sell_alerts.append((ticker, sell_sigs, score))
    if progress_callback:
        progress_callback(total_scanned, total_scanned)

    # Sort by strength score descending (strongest first)
    buy_alerts.sort(key=lambda x: x[2], reverse=True)
    sell_alerts.sort(key=lambda x: x[2], reverse=True)

    return buy_alerts, sell_alerts, total_scanned, ticker_to_name


def scan(min_signals: int, days: int) -> None:
    """Run the full scan and print results."""
    colorama_init()

    buy_alerts, sell_alerts, total_scanned, _names = get_alerts(min_signals, days)

    today = datetime.date.today().isoformat()
    print()
    print("=" * 45)
    print(f"  STOCK TRADING ALERTS — {today}")
    print("=" * 45)

    if buy_alerts:
        print(f"\n{Fore.GREEN}BUY SIGNALS:{Style.RESET_ALL}")
        for ticker, sigs, score in buy_alerts:
            details = ", ".join(s.detail for s in sigs)
            print(f"  {Fore.GREEN}{ticker:<6}{Style.RESET_ALL}| {Fore.YELLOW}[{score:4.1f}/10]{Style.RESET_ALL} {details}")
    else:
        print(f"\n{Fore.GREEN}BUY SIGNALS:{Style.RESET_ALL}  (none)")

    if sell_alerts:
        print(f"\n{Fore.RED}SELL SIGNALS:{Style.RESET_ALL}")
        for ticker, sigs, score in sell_alerts:
            details = ", ".join(s.detail for s in sigs)
            print(f"  {Fore.RED}{ticker:<6}{Style.RESET_ALL}| {Fore.YELLOW}[{score:4.1f}/10]{Style.RESET_ALL} {details}")
    else:
        print(f"\n{Fore.RED}SELL SIGNALS:{Style.RESET_ALL}  (none)")

    print(
        f"\nSummary: {len(buy_alerts)} buy alert(s), {len(sell_alerts)} sell alert(s) "
        f"out of {total_scanned} stocks scanned"
    )
