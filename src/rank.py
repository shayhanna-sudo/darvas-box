"""Rank candidates by a mechanical risk/reward score (AI conviction as one input),
then select the best N to fill available position slots."""
import config


def score(c):
    entry, stop = c["entry"], c["stop"]
    risk_pct = (entry - stop) / entry if entry else 1.0
    tight = max(0.0, (config.MAX_BOX_WIDTH - risk_pct) / config.MAX_BOX_WIDTH) * 40
    theme = 30 if c.get("theme_match") else 0
    g = (c.get("revenue_growth") or 0) + (c.get("eps_growth") or 0)
    growth = max(0.0, min(1.0, g / 0.6)) * 20
    kind = 10 if c.get("kind") == "BREAKOUT" else 0
    return round(tight + theme + growth + kind, 1)


def rank_and_select(candidates, slots):
    scored = [dict(c, score=score(c)) for c in candidates]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:max(0, slots)]
