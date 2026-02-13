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


def fetch_sp500_tickers() -> list[str]:
    """Scrape the S&P 500 ticker list from Wikipedia."""
    headers = {"User-Agent": "StockTradingAlerts/1.0"}
    resp = requests.get(config.SP500_WIKI_URL, headers=headers)
    resp.raise_for_status()
    tables = pd.read_html(io.StringIO(resp.text))
    df = tables[0]
    tickers = df["Symbol"].tolist()
    # Some Wikipedia tickers use dots (e.g. BRK.B) but yfinance expects dashes
    tickers = [t.replace(".", "-") for t in tickers]
    return tickers


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


def scan(min_signals: int, days: int) -> None:
    """Run the full scan and print results."""
    colorama_init()

    tickers = fetch_sp500_tickers()
    data = fetch_price_data(tickers, days)

    buy_alerts: list[tuple[str, list[indicators.Signal]]] = []
    sell_alerts: list[tuple[str, list[indicators.Signal]]] = []

    total_scanned = len(data)
    for ticker, df in data.items():
        signals = indicators.analyze(df)
        if len(signals) < min_signals:
            continue
        buy_sigs = [s for s in signals if s.direction == "buy"]
        sell_sigs = [s for s in signals if s.direction == "sell"]
        if len(buy_sigs) >= min_signals:
            buy_alerts.append((ticker, buy_sigs))
        if len(sell_sigs) >= min_signals:
            sell_alerts.append((ticker, sell_sigs))

    # Sort alphabetically
    buy_alerts.sort(key=lambda x: x[0])
    sell_alerts.sort(key=lambda x: x[0])

    today = datetime.date.today().isoformat()
    print()
    print("=" * 45)
    print(f"  STOCK TRADING ALERTS — {today}")
    print("=" * 45)

    if buy_alerts:
        print(f"\n{Fore.GREEN}BUY SIGNALS:{Style.RESET_ALL}")
        for ticker, sigs in buy_alerts:
            details = ", ".join(s.detail for s in sigs)
            print(f"  {Fore.GREEN}{ticker:<6}{Style.RESET_ALL}| {details}")
    else:
        print(f"\n{Fore.GREEN}BUY SIGNALS:{Style.RESET_ALL}  (none)")

    if sell_alerts:
        print(f"\n{Fore.RED}SELL SIGNALS:{Style.RESET_ALL}")
        for ticker, sigs in sell_alerts:
            details = ", ".join(s.detail for s in sigs)
            print(f"  {Fore.RED}{ticker:<6}{Style.RESET_ALL}| {details}")
    else:
        print(f"\n{Fore.RED}SELL SIGNALS:{Style.RESET_ALL}  (none)")

    print(
        f"\nSummary: {len(buy_alerts)} buy alert(s), {len(sell_alerts)} sell alert(s) "
        f"out of {total_scanned} stocks scanned"
    )
