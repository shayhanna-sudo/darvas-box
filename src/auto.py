"""Fully automatic EOD runner (maintain-don't-churn): skip held/pending, drop stale, add new."""
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

    candidates = run_pipeline()
    equity = broker.get_equity()
    bp = broker.get_buying_power()
    held = broker.open_symbols()
    pending = {o.symbol for o in broker.open_orders() if o.symbol not in held}
    candidate_syms = {c["symbol"] for c in candidates}

    dropped = broker.cancel_orders_for_symbols(pending - candidate_syms)
    pending -= (pending - candidate_syms)

    committed = held | pending
    slots = min(config.MAX_OPEN_POSITIONS - len(committed), config.MAX_TRADES_PER_DAY)
    ranked = rank_and_select(candidates, len(candidates))
    fresh = [c for c in ranked if c["symbol"] not in committed][:max(0, slots)]

    lines = [f"Darvas AUTO - equity ${equity:,.0f} | BP ${bp:,.0f} | "
             f"{len(held)} held | {len(pending)} pending | dropped {dropped} | new {len(fresh)}:"]
    for c in fresh:
        price = broker.latest_price(c["symbol"])
        if price is not None and price >= c["entry"]:
            lines.append(f"  skip {c['symbol']} (price {price} >= entry {c['entry']} - missed/stale)")
            continue
        qty = risk.position_size(equity, c["entry"], c["stop"])
        if qty <= 0:
            lines.append(f"  skip {c['symbol']} (qty 0)")
            continue
        cost = qty * c["entry"]
        if cost > bp:
            lines.append(f"  skip {c['symbol']} (need ${cost:,.0f}, BP ${bp:,.0f})")
            continue
        try:
            broker.submit_darvas_order(c["symbol"], qty, c["entry"], c["stop"])
            tg.insert_signal(c)
            bp -= cost
            hot = "HOT" if c.get("theme_match") else ""
            lines.append(f"  BUY {c['symbol']} x{qty} @ {c['entry']} stop {c['stop']} score {c['score']} {hot}")
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
