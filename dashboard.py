"""Streamlit dashboard for Stock Trading Alerts."""

import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

import config
import indicators
from scanner import fetch_sp500_tickers, fetch_price_data, get_alerts

st.set_page_config(page_title="Stock Trading Alerts", layout="wide")

# ── Sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.header("Scan Settings")
min_signals = st.sidebar.slider(
    "Min signals", min_value=1, max_value=10, value=config.MIN_SIGNALS
)
days = st.sidebar.slider(
    "Lookback days", min_value=30, max_value=730, value=config.LOOKBACK_DAYS
)
run_scan = st.sidebar.button("Scan Now", type="primary", use_container_width=True)


# ── Cached data fetch ────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def cached_get_alerts(
    min_signals: int, days: int
) -> tuple[list, list, int, dict]:
    """Wrapper around get_alerts with Streamlit caching (5-min TTL)."""
    return get_alerts(min_signals, days)


@st.cache_data(ttl=300, show_spinner=False)
def cached_price_data(ticker: str, days: int) -> pd.DataFrame:
    """Fetch price data for a single ticker (for detail charts)."""
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days)
    df = yf.download(ticker, start=start.isoformat(), end=end.isoformat(), progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    return df


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_alerts_df(
    alerts: list[tuple[str, list[indicators.Signal], float]],
    ticker_to_name: dict[str, str],
) -> pd.DataFrame:
    """Convert alert tuples into a display DataFrame."""
    rows = []
    for rank, (ticker, sigs, score) in enumerate(alerts, 1):
        rows.append(
            {
                "Rank": rank,
                "Ticker": ticker,
                "Company": ticker_to_name.get(ticker, ""),
                "Score": score,
                "# Signals": len(sigs),
                "Signal Details": ", ".join(s.detail for s in sigs),
            }
        )
    return pd.DataFrame(rows)


def _strength_color(score: float, direction: str) -> str:
    """Return a CSS background colour string scaled by score."""
    intensity = min(1.0, score / 10.0)
    alpha = 0.15 + intensity * 0.45  # range 0.15 – 0.60
    if direction == "buy":
        return f"rgba(0, 180, 0, {alpha:.2f})"
    return f"rgba(220, 0, 0, {alpha:.2f})"


def _style_table(df: pd.DataFrame, direction: str) -> pd.io.formats.style.Styler:
    """Apply row-level background colour based on Score column."""

    def row_bg(row):
        color = _strength_color(row["Score"], direction)
        return [f"background-color: {color}"] * len(row)

    return df.style.apply(row_bg, axis=1).format({"Score": "{:.1f}"})


def _candlestick_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Create a Plotly candlestick chart for a ticker."""
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name=ticker,
            )
        ]
    )
    fig.update_layout(
        title=f"{ticker} Price Chart",
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        xaxis_rangeslider_visible=False,
        height=450,
        margin=dict(l=40, r=40, t=50, b=40),
    )
    return fig


def _show_detail(ticker: str, sigs: list[indicators.Signal], days: int):
    """Render expandable detail section for a single stock."""
    with st.expander(f"Details for {ticker}"):
        df = cached_price_data(ticker, days)
        if df.empty:
            st.warning(f"No price data available for {ticker}.")
            return
        st.plotly_chart(_candlestick_chart(df, ticker), use_container_width=True)

        st.markdown("**Individual Indicator Values**")
        sig_rows = [
            {
                "Indicator": s.name,
                "Direction": s.direction.upper(),
                "Strength": f"{s.strength:.2f}",
                "Detail": s.detail,
            }
            for s in sigs
        ]
        st.table(pd.DataFrame(sig_rows))


def _render_tab(
    alerts: list[tuple[str, list[indicators.Signal], float]],
    direction: str,
    days: int,
    ticker_to_name: dict[str, str],
):
    """Render a full alert tab (table + expandable details)."""
    if not alerts:
        st.info(f"No {direction} alerts found.")
        return

    df = _build_alerts_df(alerts, ticker_to_name)
    st.dataframe(
        _style_table(df, direction),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")
    st.subheader("Stock Details")
    for ticker, sigs, _score in alerts:
        _show_detail(ticker, sigs, days)


# ── Main page ────────────────────────────────────────────────────────────────

st.title("Stock Trading Alerts")
st.caption(f"Date: {datetime.date.today().isoformat()}")

if run_scan:
    with st.spinner("Scanning S&P 500 stocks..."):
        buy_alerts, sell_alerts, total_scanned, ticker_to_name = cached_get_alerts(min_signals, days)
    st.session_state["scan_results"] = (buy_alerts, sell_alerts, total_scanned, ticker_to_name)
    st.session_state["scan_days"] = days

if "scan_results" in st.session_state:
    buy_alerts, sell_alerts, total_scanned, ticker_to_name = st.session_state["scan_results"]
    scan_days = st.session_state["scan_days"]

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Scanned", total_scanned)
    col2.metric("Buy Alerts", len(buy_alerts))
    col3.metric("Sell Alerts", len(sell_alerts))

    # Tabs
    tab_buy, tab_sell = st.tabs(["Buy Signals", "Sell Signals"])
    with tab_buy:
        _render_tab(buy_alerts, "buy", scan_days, ticker_to_name)
    with tab_sell:
        _render_tab(sell_alerts, "sell", scan_days, ticker_to_name)
else:
    st.info(
        'Configure the settings in the sidebar and click **"Scan Now"** to begin.'
    )
