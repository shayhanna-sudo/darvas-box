"""Build the tradable universe: S&P 500 + Nasdaq 100 + S&P 400 midcap (~1500 tickers)."""
import os
from io import StringIO
import requests
import pandas as pd

UNIVERSE_FILE = "data/universe.txt"

# Wikipedia blocks requests without a real User-Agent (HTTP 403).
HEADERS = {"User-Agent": "Mozilla/5.0 (Darvas-Bot research; github.com/shayhanna-sudo)"}

WIKI_SOURCES = [
    "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    "https://en.wikipedia.org/wiki/Nasdaq-100",
    "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
]

FALLBACK = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AVGO", "TSLA", "AMD",
    "NFLX", "ADBE", "CRM", "COST", "PEP", "QCOM", "TXN", "INTC", "AMAT",
    "MU", "LRCX", "PLTR", "SMCI", "ARM", "PANW", "SNOW", "JPM", "V", "MA",
]


def _clean(symbols):
    out = set()
    for s in symbols:
        s = str(s).replace(".", "-").strip().upper()
        core = s.replace("-", "")
        if s and s.isascii() and 1 <= len(s) <= 6 and core.isalnum():
            out.add(s)
    return out


def _pick_symbol_column(table):
    for col in ("Symbol", "Ticker", "Ticker symbol"):
        if col in table.columns:
            return col
    return None


def _from_wikipedia():
    syms = set()
    for url in WIKI_SOURCES:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            tables = pd.read_html(StringIO(resp.text))
            best = None
            for t in tables:
                col = _pick_symbol_column(t)
                if col is not None and (best is None or len(t) > len(best[0])):
                    best = (t, col)
            if best is not None:
                syms.update(best[0][best[1]].tolist())
                print(f"[universe] {url.split('/')[-1]}: +{len(best[0])} rows")
        except Exception as e:
            print(f"[universe] FAILED {url}: {e}")
    return syms


def build_universe(refresh=False):
    if not refresh and os.path.exists(UNIVERSE_FILE):
        with open(UNIVERSE_FILE) as f:
            return [ln.strip() for ln in f if ln.strip()]
    syms = _clean(_from_wikipedia())
    if len(syms) < 100:
        print("[universe] Wikipedia unreachable / too few - using FALLBACK list")
        syms = _clean(FALLBACK)
    syms = sorted(syms)
    os.makedirs(os.path.dirname(UNIVERSE_FILE) or ".", exist_ok=True)
    with open(UNIVERSE_FILE, "w") as f:
        f.write("\n".join(syms))
    return syms


if __name__ == "__main__":
    u = build_universe(refresh=True)
    print(f"Universe: {len(u)} tickers")
    print(u[:25])
