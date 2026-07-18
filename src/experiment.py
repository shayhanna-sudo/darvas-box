"""Compare trailing + market-regime variants. Downloads once, runs all configs."""
import sys
import pandas as pd
import yfinance as yf

from src.universe import build_universe
from src.data import fetch_bars
from src.darvas_engine import DarvasEngine
from src.filters import passes_filters
from src.backtest import stats


def spy_regime():
    df = yf.download("SPY", period="7y", interval="1d", auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna()
    sma = df["Close"].rolling(200).mean()
    reg = {}
    for dt, c, m in zip(df.index, df["Close"], sma):
        reg[str(dt.date())] = bool(m == m and c > m)
    return reg


def backtest_variant(bars_map, trail_every, regime=None):
    trades = []
    for sym, bars in bars_map.items():
        eng = DarvasEngine(sym, trail_every=trail_every)
        open_t = None
        for i, b in enumerate(bars):
            for e in eng.process_bar(b):
                if e.type == "BREAKOUT" and open_t is None:
                    ok, _ = passes_filters(bars[:i + 1], e.data["box_top"], e.data["box_bottom"])
                    if regime is not None and not regime.get(b.date, True):
                        ok = False
                    if ok:
                        open_t = {"symbol": sym, "entry": e.data["entry"],
                                  "stop": e.data["stop"], "entry_date": b.date}
                elif e.type == "STOPPED_OUT" and open_t is not None:
                    open_t.update(exit=e.data["stop"], exit_date=b.date)
                    trades.append(open_t)
                    open_t = None
        if open_t is not None:
            open_t.update(exit=bars[-1].close, exit_date=bars[-1].date)
            trades.append(open_t)
    return trades


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    uni = build_universe()[:n]
    print(f"[exp] downloading {len(uni)} symbols + SPY once...")
    bars_map = fetch_bars(uni, period="5y")
    reg = spy_regime()

    configs = [
        ("baseline: trail every box",     1, None),
        ("loose: trail every 2nd box",    2, None),
        ("no trail: ride initial stop",   0, None),
        ("baseline + SPY>200SMA",         1, reg),
        ("loose + SPY>200SMA",            2, reg),
        ("no trail + SPY>200SMA",         0, reg),
    ]
    hdr = f"{'config':30}{'trades':>7}{'win%':>6}{'expR':>7}{'avgW':>6}{'PF':>6}{'DD_R':>8}"
    print("\n" + hdr)
    print("-" * len(hdr))
    for name, te, rg in configs:
        s = stats(backtest_variant(bars_map, te, rg))
        if not s.get("trades"):
            print(f"{name:30}{0:>7}")
            continue
        print(f"{name:30}{s['trades']:>7}{s['win_rate'] * 100:>5.0f}%"
              f"{s['expectancy_R']:>7.3f}{s['avg_win_R']:>6.2f}"
              f"{s['profit_factor']:>6.2f}{s['max_drawdown_R']:>8.1f}")
