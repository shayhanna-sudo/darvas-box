"""Gemini layer: hot-theme detection + candidate narrative (data-grounded)."""
import json
from google import genai
import config
import secrets_conf

_client = genai.Client(api_key=secrets_conf.GEMINI_API_KEY)


def _generate(prompt):
    resp = _client.models.generate_content(model=config.GEMINI_MODEL, contents=prompt)
    return (resp.text or "").strip()


def hot_themes():
    prompt = (
        "List the 5-8 hottest US stock market themes/sectors RIGHT NOW "
        "(for example: AI, semiconductors, nuclear/power, defense, cybersecurity). "
        "Return ONLY a comma-separated list of short theme names, no explanation."
    )
    try:
        text = _generate(prompt)
        themes = [t.strip() for t in text.replace("\n", ",").split(",") if t.strip()]
        return themes[:8]
    except Exception as e:
        print(f"[ai] hot_themes failed: {e}")
        return []


def judge_candidate(symbol, fundamentals, themes):
    prompt = (
        f"Ticker: {symbol}\n"
        f"Current hot themes: {', '.join(themes)}\n"
        f"Fundamentals we measured (do NOT invent any other numbers):\n"
        f"  revenue_growth_yoy: {fundamentals.get('revenue_growth')}\n"
        f"  eps_growth_yoy: {fundamentals.get('eps_growth')}\n"
        f"  net_income_latest: {fundamentals.get('net_income_latest')}\n\n"
        "Reply with STRICT JSON only: "
        '{"theme_match": true or false, "theme": "matched theme or empty", '
        '"verdict": "one short sentence on growth quality"}. '
        "Set theme_match true only if this company clearly belongs to one listed theme."
    )
    try:
        text = _generate(prompt).replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        return {
            "theme_match": bool(data.get("theme_match")),
            "theme": data.get("theme", ""),
            "verdict": data.get("verdict", ""),
        }
    except Exception as e:
        print(f"[ai] judge {symbol} failed: {e}")
        return {"theme_match": None, "theme": "", "verdict": f"AI error: {e}"}
