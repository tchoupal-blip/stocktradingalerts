"""Entry point for the Stock Trading Alerts scanner."""

import argparse

import config
from scanner import scan


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan S&P 500 stocks for technical buy/sell signals")
    parser.add_argument(
        "--min-signals",
        type=int,
        default=config.MIN_SIGNALS,
        help=f"Minimum simultaneous signals to trigger an alert (default: {config.MIN_SIGNALS})",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=config.LOOKBACK_DAYS,
        help=f"Lookback period in days for historical data (default: {config.LOOKBACK_DAYS})",
    )
    args = parser.parse_args()
    scan(min_signals=args.min_signals, days=args.days)


if __name__ == "__main__":
    main()
