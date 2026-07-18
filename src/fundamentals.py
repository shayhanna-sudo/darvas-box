"""Pull quarterly EPS + revenue from yfinance and apply a deterministic growth gate."""
import yfinance as yf
import config

REV_ROWS = ["Total Revenue", "TotalRevenue"]
EPS_ROWS = ["Diluted EPS", "Basic EPS", "DilutedEPS"]
NI_ROWS = ["Net Income", "NetIncome"]


def _row(df, names):
    for n in names:
        if n in df.index:
            return df.loc[n]
    return None


def _series(row):
    if row is None:
        return []
    return [float(x) for x in row.tolist() if x == x]


def _yoy(vals):
    if len(vals) >= 5:
        old = vals[4]
    elif len(vals) >= 2:
        old = vals[-1]
    else:
        return None
    new = vals[0]
    if old == 0:
        return None
    return (new - old) / abs(old)


def get_fundamentals(symbol):
    try:
        q = yf.Ticker(symbol).quarterly_income_stmt
        if q is None or q.empty:
            return None
        rev = _series(_row(q, REV_ROWS))
        eps = _series(_row(q, EPS_ROWS))
        ni = _series(_row(q, NI_ROWS))
        return {
            "symbol": symbol,
            "revenue_latest": rev[0] if rev else None,
            "revenue_growth": _yoy(rev),
            "eps_growth": _yoy(eps),
            "net_income_latest": ni[0] if ni else None,
        }
    except Exception as e:
        print(f"[fund] {symbol} failed: {e}")
        return None


def fundamental_gate(f):
    if not f:
        return False, "no fundamentals"
    rg, eg, ni = f.get("revenue_growth"), f.get("eps_growth"), f.get("net_income_latest")
    if ni is not None and ni <= 0:
        return False, "unprofitable"
    if rg is None or rg < config.MIN_REV_YOY_GROWTH:
        return False, f"weak revenue growth ({rg})"
    if eg is None or eg < config.MIN_EPS_YOY_GROWTH:
        return False, f"weak EPS growth ({eg})"
    return True, "pass"
