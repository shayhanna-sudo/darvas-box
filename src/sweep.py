import sys
from src.universe import build_universe
from src.data import fetch_bars
from src.backtest import stats
from src.experiment import spy_regime, backtest_variant

n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
uni = build_universe()[:n]
print(f"[sweep] downloading {len(uni)}+SPY once...")
bm = fetch_bars(uni, period="5y")
reg = spy_regime()
print(f"\n{'trail_every':>11}{'trades':>7}{'win%':>6}{'expR':>7}{'avgW':>6}{'PF':>6}{'DD_R':>8}")
for te in [2, 3, 4, 5, 6]:
    s = stats(backtest_variant(bm, te, reg))
    print(f"{te:>11}{s['trades']:>7}{s['win_rate']*100:>5.0f}%{s['expectancy_R']:>7.3f}"
          f"{s['avg_win_R']:>6.2f}{s['profit_factor']:>6.2f}{s['max_drawdown_R']:>8.1f}")
