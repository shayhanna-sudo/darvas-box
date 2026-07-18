"""Telegram hybrid layer: send each candidate with Approve/Reject buttons, poll decisions."""
import json
import time
import sqlite3
from datetime import date

import requests
import config
import secrets_conf

API = f"https://api.telegram.org/bot{secrets_conf.TELEGRAM_BOT_TOKEN}"
CHAT_ID = secrets_conf.TELEGRAM_CHAT_ID


def _conn():
    c = sqlite3.connect(config.DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    return c


def insert_signal(cand):
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO signals(symbol,date,entry_price,stop_price,fundamental,theme,verdict,status) "
            "VALUES(?,?,?,?,?,?,?, 'pending')",
            (cand["symbol"], str(date.today()), cand["entry"], cand["stop"],
             "pass", cand.get("theme", ""), cand.get("verdict", "")),
        )
        c.commit()
        return cur.lastrowid


def get_signal(sig_id):
    with _conn() as c:
        row = c.execute("SELECT * FROM signals WHERE id=?", (sig_id,)).fetchone()
        return dict(row) if row else None


def set_status(sig_id, status):
    with _conn() as c:
        c.execute("UPDATE signals SET status=? WHERE id=?", (status, sig_id))
        c.commit()


def send_message(text, reply_markup=None):
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        return requests.post(f"{API}/sendMessage", data=payload, timeout=20).json()
    except Exception as e:
        print(f"[tg] send failed: {e}")
        return {"ok": False, "error": str(e)}


def send_signal(cand):
    sig_id = insert_signal(cand)
    hot = "\U0001F525 HOT" if cand.get("theme_match") else ""
    risk = (1 - cand["stop"] / cand["entry"]) * 100
    text = (
        f"<b>{cand['kind']} - {cand['symbol']}</b> {hot}\n"
        f"Entry (buy-stop): <b>{cand['entry']}</b>\n"
        f"Stop-loss: <b>{cand['stop']}</b>  (risk {risk:.1f}%)\n"
        f"Theme: {cand.get('theme') or '-'}\n"
        f"Rev growth: {cand.get('revenue_growth')} | EPS growth: {cand.get('eps_growth')}\n"
        f"Gemini: {cand.get('verdict')}"
    )
    kb = {"inline_keyboard": [[
        {"text": "✅ Approve", "callback_data": f"app:{sig_id}"},
        {"text": "❌ Reject", "callback_data": f"rej:{sig_id}"},
    ]]}
    send_message(text, kb)
    return sig_id


def poll(handler=None, timeout=120):
    offset = None
    end = time.time() + timeout
    while time.time() < end:
        try:
            r = requests.get(f"{API}/getUpdates",
                             params={"timeout": 20, "offset": offset}, timeout=30).json()
        except Exception as e:
            print(f"[tg] poll error: {e}")
            time.sleep(3)
            continue
        for upd in r.get("result", []):
            offset = upd["update_id"] + 1
            cq = upd.get("callback_query")
            if not cq:
                continue
            action, _, sid = cq["data"].partition(":")
            row = get_signal(int(sid))
            status = "approved" if action == "app" else "rejected"
            set_status(int(sid), status)
            requests.post(f"{API}/answerCallbackQuery",
                          data={"callback_query_id": cq["id"], "text": status})
            msg = cq["message"]
            requests.post(f"{API}/editMessageText", data={
                "chat_id": CHAT_ID, "message_id": msg["message_id"],
                "text": msg["text"] + f"\n\n➡️ {status.upper()}"})
            if handler:
                handler(action, row)
