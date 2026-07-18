"""Risk & position sizing: risk a fixed % of equity per trade; enforce guardrails."""
import config


def position_size(equity, entry, stop, risk_pct=None, max_position_pct=None):
    risk_pct = config.RISK_PER_TRADE if risk_pct is None else risk_pct
    max_position_pct = getattr(config, "MAX_POSITION_PCT", 0.25) if max_position_pct is None else max_position_pct
    risk_per_share = entry - stop
    if risk_per_share <= 0 or equity <= 0:
        return 0
    qty = int((equity * risk_pct) // risk_per_share)
    max_notional = equity * max_position_pct
    if qty * entry > max_notional:
        qty = int(max_notional // entry)
    return max(qty, 0)


def can_trade(open_positions, trades_today):
    if config.KILL_SWITCH:
        return False, "kill switch ON"
    if trades_today >= config.MAX_TRADES_PER_DAY:
        return False, "daily trade cap reached"
    if open_positions >= config.MAX_OPEN_POSITIONS:
        return False, "max open positions reached"
    return True, "ok"


def summarize(equity, entry, stop, qty):
    risk = qty * (entry - stop)
    notional = qty * entry
    return {
        "qty": qty,
        "notional": round(notional, 2),
        "dollar_risk": round(risk, 2),
        "risk_pct": round(risk / equity * 100, 2) if equity else 0,
        "notional_pct": round(notional / equity * 100, 2) if equity else 0,
    }
