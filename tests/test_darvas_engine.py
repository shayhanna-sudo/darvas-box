"""Unit tests for the Darvas box engine on synthetic OHLC."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.darvas_engine import Bar, DarvasEngine, run_series, State


def make_bar(i, high, low, vol, close=None):
    close = close if close is not None else (high + low) / 2
    return Bar(date=f"2026-01-{i:02d}", open=(high + low) / 2,
               high=high, low=low, close=close, volume=vol)


def warmup_flat(n=60, price=100.0, vol=1000.0):
    return [make_bar(i + 1, price + 0.2, price - 0.2, vol) for i in range(n)]


def types(events):
    return [e.type for e in events]


def test_box_confirms_top_then_bottom():
    bars = warmup_flat()
    day = len(bars)
    bars.append(make_bar(day := day + 1, 110, 105, 4000))
    bars.append(make_bar(day := day + 1, 108, 103, 1200))
    bars.append(make_bar(day := day + 1, 107, 102, 1200))
    bars.append(make_bar(day := day + 1, 106, 101, 1200))
    bars.append(make_bar(day := day + 1, 105, 102, 1100))
    bars.append(make_bar(day := day + 1, 104, 103, 1100))
    bars.append(make_bar(day := day + 1, 105, 104, 1100))
    events = run_series("TEST", bars)
    assert "BOX_CONFIRMED" in types(events), types(events)
    box = [e for e in events if e.type == "BOX_CONFIRMED"][0]
    assert box.data["top"] == 110
    assert box.data["entry"] > 110 and box.data["stop"] < box.data["bottom"] + 1


def test_top_resets_on_new_high():
    bars = warmup_flat()
    day = len(bars)
    bars.append(make_bar(day := day + 1, 110, 105, 4000))
    bars.append(make_bar(day := day + 1, 108, 104, 1200))
    bars.append(make_bar(day := day + 1, 112, 106, 4000))
    bars.append(make_bar(day := day + 1, 111, 106, 1200))
    bars.append(make_bar(day := day + 1, 110, 105, 1200))
    eng = DarvasEngine("TEST")
    for b in bars:
        eng.process_bar(b)
    assert eng.state == State.TOP_PENDING
    assert eng.top_high == 112


def test_bottom_resets_on_new_low():
    bars = warmup_flat()
    day = len(bars)
    bars.append(make_bar(day := day + 1, 110, 105, 4000))
    bars.append(make_bar(day := day + 1, 108, 103, 1200))
    bars.append(make_bar(day := day + 1, 107, 102, 1200))
    bars.append(make_bar(day := day + 1, 106, 101, 1200))
    bars.append(make_bar(day := day + 1, 105, 102, 1100))
    bars.append(make_bar(day := day + 1, 104, 100, 1100))
    bars.append(make_bar(day := day + 1, 105, 101, 1100))
    eng = DarvasEngine("TEST")
    for b in bars:
        eng.process_bar(b)
    assert eng.state == State.BOTTOM_PENDING
    assert eng.bottom_low == 100


def test_breakout_signal():
    bars = warmup_flat()
    day = len(bars)
    bars.append(make_bar(day := day + 1, 110, 105, 4000))
    bars.append(make_bar(day := day + 1, 108, 103, 1200))
    bars.append(make_bar(day := day + 1, 107, 102, 1200))
    bars.append(make_bar(day := day + 1, 106, 101, 1200))
    bars.append(make_bar(day := day + 1, 105, 102, 1100))
    bars.append(make_bar(day := day + 1, 104, 103, 1100))
    bars.append(make_bar(day := day + 1, 105, 104, 1100))
    bars.append(make_bar(day := day + 1, 112, 106, 5000))
    events = run_series("TEST", bars)
    assert "BOX_CONFIRMED" in types(events)
    assert "BREAKOUT" in types(events), types(events)


def test_box_broken():
    bars = warmup_flat()
    day = len(bars)
    bars.append(make_bar(day := day + 1, 110, 105, 4000))
    bars.append(make_bar(day := day + 1, 108, 103, 1200))
    bars.append(make_bar(day := day + 1, 107, 102, 1200))
    bars.append(make_bar(day := day + 1, 106, 101, 1200))
    bars.append(make_bar(day := day + 1, 105, 102, 1100))
    bars.append(make_bar(day := day + 1, 104, 103, 1100))
    bars.append(make_bar(day := day + 1, 105, 104, 1100))
    bars.append(make_bar(day := day + 1, 103, 95, 3000))
    events = run_series("TEST", bars)
    assert "BOX_BROKEN" in types(events), types(events)


def test_volume_gate_blocks_low_volume_high():
    bars = warmup_flat()
    day = len(bars)
    bars.append(make_bar(day := day + 1, 110, 105, 1000))
    eng = DarvasEngine("TEST")
    for b in bars:
        eng.process_bar(b)
    assert eng.state == State.SCANNING


def test_trailing_stop_raised():
    bars = warmup_flat()
    day = len(bars)
    bars.append(make_bar(day := day + 1, 110, 105, 4000))
    bars.append(make_bar(day := day + 1, 108, 103, 1200))
    bars.append(make_bar(day := day + 1, 107, 102, 1200))
    bars.append(make_bar(day := day + 1, 106, 101, 1200))
    bars.append(make_bar(day := day + 1, 105, 102, 1100))
    bars.append(make_bar(day := day + 1, 104, 103, 1100))
    bars.append(make_bar(day := day + 1, 105, 104, 1100))
    bars.append(make_bar(day := day + 1, 112, 108, 5000))
    bars.append(make_bar(day := day + 1, 115, 111, 5000))
    bars.append(make_bar(day := day + 1, 114, 111, 1300))
    bars.append(make_bar(day := day + 1, 113, 110, 1300))
    bars.append(make_bar(day := day + 1, 114, 111, 1300))
    bars.append(make_bar(day := day + 1, 114, 111, 1200))
    bars.append(make_bar(day := day + 1, 113, 112, 1200))
    bars.append(make_bar(day := day + 1, 114, 113, 1200))
    events = run_series("TEST", bars)
    assert "BREAKOUT" in types(events)
    assert "STOP_RAISED" in types(events), types(events)
    raised = [e for e in events if e.type == "STOP_RAISED"][0]
    assert raised.data["new_stop"] > raised.data["old_stop"]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL  {fn.__name__}: {e}")
        except Exception as e:
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(fns)} tests passed")
    sys.exit(0 if passed == len(fns) else 1)
