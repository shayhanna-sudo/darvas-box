"""EOD entrypoint: run pipeline, push candidates to Telegram (HOT first), wait for Approve/Reject."""
from src.pipeline import run
from src import telegram_bot as tg


def _on_decision(action, row):
    if not row:
        return
    if action == "app":
        print(f"[notify] APPROVED {row['symbol']} entry={row['entry_price']} stop={row['stop_price']}")
        # P6: broker.submit_bracket(row) goes here
    else:
        print(f"[notify] rejected {row['symbol']}")


def main():
    candidates = run()
    if not candidates:
        tg.send_message("Darvas EOD scan: no candidates today.")
        return
    candidates.sort(key=lambda c: c.get("theme_match") is True, reverse=True)
    tg.send_message(f"Darvas EOD scan: {len(candidates)} candidate(s). Review below.")
    for c in candidates:
        tg.send_signal(c)
    print("[notify] alerts sent. Polling 180s for approvals...")
    tg.poll(_on_decision, timeout=180)
    print("[notify] done.")


if __name__ == "__main__":
    main()
