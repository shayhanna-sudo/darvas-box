"""Fetch daily bars from yfinance, cache in SQLite, and feed the Darvas engine."""
import time
import pandas as pd
import yfinance as yf

import config
from src.darvas_engine import Bar, DarvasEngine, State
from src.filters import passes_filters


def _df_to_bars(df):
    bars = []
    for idx, r in df.dropna().iterrows():
        try:
            bars.append(Bar(
                date=str(idx.date()),
                open=float(r["Open"]), high=float(r["High"]),
                low=float(r["Low"]), close=float(r["Close"]),
                volume=float(r["Volume"]),
            ))
        except Exception:
            continue
    return bars


def fetch_bars(symbols, period="2y", batch=100):
    out = {}
    for i in range(0, len(symbols), batch):
        chunk = symbols[i:i + batch]
        try:
            data = yf.download(chunk, period=period, interval="1d",
                               auto_adjust=True, group_by="ticker",
                               threads=True, progress=False)
        except Exception as e:
            print(f"[data] batch {i} failed: {e}")
            continue
        for s in chunk:
            try:
                df = data[s] if len(chunk) > 1 else data
                bars = _df_to_bars(df)
                if len(bars) >= config.HIGH_LOOKBACK // 4:
                    out[s] = bars
            except Exception:
                continue
        time.sleep(1)
    return out


def market_is_bullish(symbol="SPY"):
    """Regime filter: True if SPY closed above its 200-day SMA. Fails open on error."""
    try:
        df = yf.download(symbol, period="2y", interval="1d",
                         auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna()
        if len(df) < 200:
            return True
        sma200 = df["Close"].tail(200).mean()
        return float(df["Close"].iloc[-1]) > float(sma200)
    except Exception as e:
        print(f"[data] regime check failed: {e}")
        return True


def scan(symbols):
    """Run the engine over each symbol, then apply technical filters."""
    bars_map = fetch_bars(symbols)
    hits = []
    for s, bars in bars_map.items():
        eng = DarvasEngine(s, trail_every=config.TRAIL_EVERY)
        events = []
        for b in bars:
            events += eng.process_bar(b)
        last_date = bars[-1].date
        if eng.state == State.BOX_CONFIRMED:
            ok, _ = passes_filters(bars, eng.box_top, eng.box_bottom)
            if ok:
                hits.append((s, "BOX_ARMED", eng.entry_price, eng.stop_price))
        for e in events:
            if e.type == "BREAKOUT" and e.date == last_date:
                ok, _ = passes_filters(bars, e.data["box_top"], e.data["box_bottom"])
                if ok:
                    hits.append((s, "BREAKOUT", e.data["entry"], e.data["stop"]))
    return hits


if __name__ == "__main__":
    from src.universe import build_universe
    uni = build_universe()
    print(f"[scan] {len(uni)} tickers...")
    results = scan(uni)
    if not results:
        print("[scan] no candidates today.")
    for sym, kind, entry, stop in results:
        w = (1 - stop / entry) * 100
        print(f"{kind:10} {sym:6} entry={entry} stop={stop}  risk~{w:.1f}%")
    print("[scan] done.")
