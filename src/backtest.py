"""Backtest the MECHANICAL Darvas system (engine + P3 filters) on historical bars.
Technical-only: fundamentals/AI are point-in-time and would add look-ahead bias.
Metric of record: expectancy in R (avg profit per unit of risk).
Usage: python3 -m src.backtest [N]   # N = limit tickers for a faster first read
"""
import sys
import statistics
from src.data import fetch_bars
from src.darvas_engine import DarvasEngine
from src.filters import passes_filters


def backtest_symbol(symbol, bars):
    eng = DarvasEngine(symbol)
    trades, open_t = [], None
    for i, b in enumerate(bars):
        for e in eng.process_bar(b):
            if e.type == "BREAKOUT" and open_t is None:
                ok, _ = passes_filters(bars[:i + 1], e.data["box_top"], e.data["box_bottom"])
                if ok:
                    open_t = {"symbol": symbol, "entry": e.data["entry"],
                              "stop": e.data["stop"], "entry_date": b.date}
            elif e.type == "STOPPED_OUT" and open_t is not None:
                open_t.update(exit=e.data["stop"], exit_date=b.date)
                trades.append(open_t)
                open_t = None
    if open_t is not None:
        open_t.update(exit=bars[-1].close, exit_date=bars[-1].date, open_end=True)
        trades.append(open_t)
    return trades


def r_multiple(t):
    risk = t["entry"] - t["stop"]
    return (t["exit"] - t["entry"]) / risk if risk > 0 else 0.0


def max_drawdown_R(trades):
    cum = peak = dd = 0.0
    for t in sorted(trades, key=lambda x: x["exit_date"]):
        cum += r_multiple(t)
        peak = max(peak, cum)
        dd = min(dd, cum - peak)
    return dd


def stats(trades):
    if not trades:
        return {"trades": 0}
    rs = [r_multiple(t) for t in trades]
    rets = [t["exit"] / t["entry"] - 1 for t in trades]
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    gross_win = sum(r for r in rs if r > 0)
    gross_loss = -sum(r for r in rs if r < 0)
    return {
        "trades": len(trades),
        "win_rate": round(len(wins) / len(rs), 3),
        "expectancy_R": round(statistics.mean(rs), 3),
        "avg_win_R": round(statistics.mean(wins), 2) if wins else 0,
        "avg_loss_R": round(statistics.mean(losses), 2) if losses else 0,
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss else float("inf"),
        "avg_return_pct": round(statistics.mean(rets) * 100, 2),
        "total_R": round(sum(rs), 1),
        "max_drawdown_R": round(max_drawdown_R(trades), 1),
    }


def run(symbols, period="5y"):
    bars_map = fetch_bars(symbols, period=period)
    all_trades = []
    for s, bars in bars_map.items():
        all_trades += backtest_symbol(s, bars)
    return all_trades


if __name__ == "__main__":
    from src.universe import build_universe
    uni = build_universe()
    if len(sys.argv) > 1:
        uni = uni[:int(sys.argv[1])]
    print(f"[backtest] {len(uni)} symbols, 5y history (can take a few minutes)...")
    trades = run(uni, period="5y")
    s = stats(trades)
    print("\n===== DARVAS MECHANICAL BACKTEST (technical-only) =====")
    for k, v in s.items():
        print(f"  {k:16}: {v}")
    print("=======================================================")
