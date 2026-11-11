"""Step 10: fetch each in-scope product page (polite, resumable) and keep only spec / box snippets.

Stores: Headphone Zone, The Audio Store, Concept Kart (robots.txt allows; checked 2026-11-10).
HiFiNage is skipped: its robots.txt blocks Claude's crawlers.
Raw HTML is deleted right after conversion (pages are 0.4-2 MB each); only snippets are kept:
raw/pages_text/<store>__<handle>.txt
Run: GAP=4 python3 scripts/s10_pages.py
"""
import html, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from polite import fetch

ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(ROOT, "raw")
OUT = os.path.join(RAW, "pages_text")
TMP = os.path.join(RAW, "cache_pages")
KEYS = re.compile(r"in the box|box content|what.?s in the box|package (?:includes|contents?)|packing list|accessor(?:y|ies) included|"
                  r"specification|impedance|sensitivity|detachable|2[- ]?pin|mmcx|0\.78|ear ?tips|warranty|microphone|\bmic\b|"
                  r"\bdsp\b|\beq\b|app\b|carrying|case\b|pouch|adapter|cable", re.I)
NAV_NOISE = re.compile(r"(Back IEMS|Headphone Stands|Terms Of Service|Every FAQ Ever|Site navi|Login Cart)", re.I)


def to_text(h):
    h = re.sub(r"(?is)<(script|style|noscript|svg|header|footer|nav)[^>]*>.*?</\1>", " ", h)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h))).strip()


STRONG = re.compile(r"in the box|box content|what.?s in the box|package (?:includes|contents?)|packing list|specification|impedance|sensitivity", re.I)
POLICY = re.compile(r"return|replacement policy|exchange policy|club audiophile|store credit|cash on delivery|\bCOD\b|shipping", re.I)


def spans_for(t, rx, width):
    spans = []
    for m in rx.finditer(t):
        a, b = max(0, m.start() - 120), min(len(t), m.end() + width)
        if spans and a <= spans[-1][1]:
            spans[-1][1] = b
        else:
            spans.append([a, b])
    return spans


def snippets(t, cap=7000):
    """Strong sections (box list, specs) first, then other keyword hits; store policy text skipped."""
    out, n, seen = [], 0, set()
    for rx, width in ((STRONG, 700), (KEYS, 300)):
        for a, b in spans_for(t, rx, width):
            s = t[a:b]
            if (a // 200) in seen or (rx is KEYS and (POLICY.search(s) or NAV_NOISE.search(s))):
                continue
            seen.update(range(a // 200, b // 200 + 1))
            out.append(s)
            n += len(s)
            if n > cap:
                return "\n...\n".join(out)
    return "\n...\n".join(out)


def main():
    os.makedirs(OUT, exist_ok=True)
    L = json.load(open(os.path.join(RAW, "listings.json")))
    todo = sorted({(l["store"], l["handle"], l["url"]) for l in L if l["store"] != "hifinage"})
    print(len(todo), "pages", flush=True)
    for i, (store, handle, url) in enumerate(todo, 1):
        path = os.path.join(OUT, f"{store}__{handle}.txt")
        if os.path.exists(path):
            continue
        b = fetch(url, TMP)
        for f in os.listdir(TMP):  # never keep raw HTML
            os.remove(os.path.join(TMP, f))
        if not b:
            print(f"[{i}/{len(todo)}] FAILED {store}:{handle}", flush=True)
            continue
        t = to_text(b.decode("utf-8", "ignore"))
        title = re.search(r"<title>(.*?)</title>", b.decode("utf-8", "ignore"), re.S)
        open(path, "w").write(f"URL: {url}\nTITLE: {html.unescape(title.group(1).strip()) if title else ''}\n\n{snippets(t)}")
        if i % 25 == 0:
            print(f"[{i}/{len(todo)}] {store}:{handle} ok", flush=True)
    print("DONE", len(os.listdir(OUT)), "files", flush=True)


if __name__ == "__main__":
    main()
