"""End-to-end EOD pipeline: regime gate -> scan -> filters -> fundamentals -> Gemini."""
import config
from src.universe import build_universe
from src.data import scan, market_is_bullish
from src.fundamentals import get_fundamentals, fundamental_gate
from src.ai_filter import hot_themes, judge_candidate


def run():
    if config.USE_REGIME_FILTER and not market_is_bullish():
        print("[pipeline] SPY below 200SMA - market not bullish, standing aside.")
        return []
    uni = build_universe()
    print(f"[pipeline] scanning {len(uni)} tickers...")
    candidates = scan(uni)
    print(f"[pipeline] {len(candidates)} technical candidates")
    if not candidates:
        return []
    themes = hot_themes()
    print(f"[pipeline] hot themes: {themes}")
    final = []
    for sym, kind, entry, stop in candidates:
        f = get_fundamentals(sym)
        ok, why = fundamental_gate(f)
        if not ok:
            print(f"  reject {sym:6} - {why}")
            continue
        j = judge_candidate(sym, f, themes)
        final.append({
            "symbol": sym, "kind": kind, "entry": entry, "stop": stop,
            "revenue_growth": f.get("revenue_growth"), "eps_growth": f.get("eps_growth"),
            "theme": j["theme"], "theme_match": j["theme_match"], "verdict": j["verdict"],
        })
        flag = "HOT" if j["theme_match"] else "---"
        print(f"  PASS {sym:6} [{kind:9}] {flag} theme={j['theme']!r} :: {j['verdict']}")
    return final


if __name__ == "__main__":
    results = run()
    print(f"\n[pipeline] {len(results)} final candidates")
    for r in results:
        print(f"  {r['kind']:9} {r['symbol']:6} entry={r['entry']} stop={r['stop']} "
              f"theme={r['theme']!r} match={r['theme_match']}")
