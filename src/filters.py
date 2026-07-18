"""Technical pre-filters - refine Darvas candidates before AI / Telegram."""
from typing import List, Tuple
import config
from src.darvas_engine import Bar


def _sma(values, n):
    return sum(values[-n:]) / n if len(values) >= n else None


def sma_close(bars, n):
    return _sma([b.close for b in bars], n)


def avg_dollar_volume(bars, n):
    return _sma([b.close * b.volume for b in bars], n) or 0.0


def high_52w(bars):
    window = bars[-config.HIGH_LOOKBACK:]
    return max(b.high for b in window) if window else None


def box_width(top, bottom):
    return (top - bottom) / top if top else 1.0


def passes_filters(bars: List[Bar], box_top: float, box_bottom: float) -> Tuple[bool, str]:
    if not bars:
        return False, "no data"
    last = bars[-1]

    w = box_width(box_top, box_bottom)
    if w > config.MAX_BOX_WIDTH:
        return False, f"box too wide {w:.1%}"

    sma = sma_close(bars, config.SMA_TREND)
    if sma is None or last.close < sma:
        return False, "below 200SMA"

    hi = high_52w(bars)
    if hi is None or box_top < (1 - config.NEAR_HIGH_PCT) * hi:
        return False, "not near 52w high"

    if last.close < config.MIN_PRICE:
        return False, f"price<{config.MIN_PRICE}"
    if avg_dollar_volume(bars, config.VOL_WINDOW) < config.MIN_AVG_DOLLAR_VOL:
        return False, "illiquid"

    return True, "pass"
