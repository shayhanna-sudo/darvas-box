"""Fully automatic EOD runner: clean stale orders -> pipeline -> rank -> guard -> size -> execute -> notify."""
import config
from src.pipeline import run as run_pipeline
from src.rank import rank_and_select
from src import risk
from src import broker_alpaca as broker
from src import telegram_bot as tg


def main():
    if config.KILL_SWITCH:
        tg.send_message("Darvas AUTO: kill switch ON - no trades.")
        return

    canceled = broker.cancel_unheld_open_orders()
    candidates = run_pipeline()
    equity = broker.get_equity()
    held = broker.open_symbols()
    open_n = len(held)

    slots = min(config.MAX_OPEN_POSITIONS - open_n, config.MAX_TRADES_PER_DAY)
    fresh = [c for c in candidates if c["symbol"] not in held]
    picks = rank_and_select(fresh, slots)

    lines = [f"Darvas AUTO - equity ${equity:,.0f} | {open_n} held | "
             f"canceled {canceled} stale | placing {len(picks)}:"]
    for c in picks:
        price = broker.latest_price(c["symbol"])
        if price is not None and price >= c["entry"]:
            lines.append(f"  skip {c['symbol']} (price {price} >= entry {c['entry']} - missed/stale box)")
            continue
        qty = risk.position_size(equity, c["entry"], c["stop"])
        if qty <= 0:
            lines.append(f"  skip {c['symbol']} (qty 0)")
            continue
        try:
            broker.submit_darvas_order(c["symbol"], qty, c["entry"], c["stop"])
            tg.insert_signal(c)
            hot = "HOT" if c.get("theme_match") else ""
            lines.append(f"  BUY {c['symbol']} x{qty} @ {c['entry']} stop {c['stop']} "
                         f"score {c['score']} {hot}")
        except Exception as e:
            lines.append(f"  FAIL {c['symbol']}: {e}")

    pos = broker.positions_summary()
    if pos:
        lines.append("Open positions:")
        lines += [f"  {p}" for p in pos]

    tg.send_message("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
