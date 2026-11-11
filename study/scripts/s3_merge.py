"""Step 3: normalise names, merge the same model across stores, and shortlist
candidate measurements for each model.

Output:
  raw/models.json      one entry per (model key, plug) with all store listings
  raw/match_tasks.json one entry per model key with top measurement candidates
"""
import difflib, json, os, re, sys
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(ROOT, "raw")

BRAND_ALIASES = {
    "kiwiears": "kiwi ears", "kiwi ears": "kiwi ears", "7hz": "7hz", "truthear": "truthear",
    "tangzu": "tangzu", "kefine": "kefine", "moondrop": "moondrop", "kz": "kz", "kz acoustics": "kz",
    "simgot": "simgot", "tanchjim": "tanchjim", "letshuoer": "letshuoer", "shuoer": "letshuoer",
    "cca": "cca", "trn": "trn", "qkz": "qkz", "kinera": "kinera", "celest": "kinera celest",
    "fiio": "fiio", "sennheiser": "sennheiser", "final": "final", "final audio": "final",
    "dunu": "dunu", "artti": "artti", "blon": "blon", "cvj": "cvj", "gk": "gk", "ziigaat": "ziigaat",
    "juzear": "juzear", "kbear": "kbear", "tri": "tri", "nicehck": "nicehck", "thieaudio": "thieaudio",
    "softears": "softears", "hidizs": "hidizs", "ikko": "ikko", "audiocular": "audiocular",
    "cozoy": "cozoy", "earacoustic": "earacoustic", "twistura": "twistura", "salnotes": "7hz",
    "ibasso": "ibasso", "activo": "activo", "meze": "meze", "shure": "shure", "oriveti": "oriveti",
    "crinear": "crinear", "sivga": "sivga", "pula": "pula", "isn": "isn", "isn audio": "isn",
    "headphone zone": "headphone zone", "hz": "headphone zone", "nd": "nd", "kiwi": "kiwi ears", "7 hertz acoustics": "7hz", "7 hertz": "7hz", "7hertz": "7hz",
}

NOISE = re.compile(
    r"\b(iems?|in[- ]?ear( monitors?)?|monitors?|earphones?|earbuds?|wired|hi[- ]?fi|hifi|hi[- ]?res|"
    r"with( hd)?( dual)? (mic|microphone)|mic|microphone|type[- ]?c( plug)?|usb[- ]?c|3\.5 ?mm( plug)?|"
    r"plug|gaming|audiophile|professional|studio|new|edition|version|standard|"
    r"\d+(\.\d+)? ?mm|\d+ ?dd|\d+ ?ba|\d+ ?drivers?|dynamic|drivers?|diaphragm|hybrid|planar( magnetic)?|"
    r"balanced armature|armatures?|dual|triple|single|quad|tri[- ]magnetic|magnetic|super[- ]linear|"
    r"silver[- ]plated|detachable|cable|ofc|lcp|dlc|polymer|resin|shell|metal|composite|nano|carbon|"
    r"beryllium|titanium|bio)\b", re.I)


def norm(s):
    s = s.lower().replace("&", " and ").replace("’", "'").replace("–", "-").replace("—", "-")
    s = s.replace("+", " plus ")
    s = re.sub(r"[()\[\]{}:,/|]", " ", s)
    s = s.replace("'", "").replace(".", "")
    return re.sub(r"\s+", " ", s).strip()


def split_brand(title, vendor=""):
    t = norm(title)
    v = norm(vendor)
    collab = bool(re.match(r"headphone zone x ", t))
    t = re.sub(r"^headphone zone x ", "", t)
    # longest alias first
    for a in sorted(BRAND_ALIASES, key=len, reverse=True):
        if t.startswith(a + " ") or t.startswith(a + "-"):
            return BRAND_ALIASES[a], t[len(a):].strip(" -"), collab
    if v and v in BRAND_ALIASES and t.startswith(v):
        return BRAND_ALIASES[v], t[len(v):].strip(" -"), collab
    first = t.split(" ")[0]
    return BRAND_ALIASES.get(first, first), t[len(first):].strip(" -"), collab


def model_key(rest):
    rest = re.sub(r"^-\s*", "", rest)
    rest = re.sub(r"\bx crinacle\b|\bx\s+(?=\S)", " x ", rest)
    rest = NOISE.sub(" ", rest)
    rest = re.sub(r"\b(ii)\b", "2", rest)
    rest = re.sub(r"\b(iii)\b", "3", rest)
    rest = re.sub(r"\s*-\s*", " ", rest)
    rest = re.sub(r"\s+", " ", rest).strip()
    return rest


def toks(s):
    return set(re.findall(r"[a-z0-9]+", s))


if __name__ == "__main__":
    listings = json.load(open(os.path.join(RAW, "listings.json")))
    models = defaultdict(lambda: {"listings": []})
    for l in listings:
        brand, rest, collab = split_brand(l["title"], l["vendor"])
        key = f"{'hz x ' if collab else ''}{brand} | {model_key(rest)}"
        m = models[(key, l["plug"])]
        m.update(brand=brand, model=model_key(rest), collab=collab, plug=l["plug"], key=key)
        m["listings"].append(l)
    out = []
    for (key, plug), m in models.items():
        ls = m["listings"]
        stock = [x for x in ls if x["in_stock"]]
        m["best_price"] = min(x["price"] for x in (stock or ls))
        m["in_stock_anywhere"] = bool(stock)
        m["stores"] = sorted({x["store"] for x in ls})
        m["display"] = ls[0]["title"]
        out.append(m)
    out.sort(key=lambda m: m["key"])
    json.dump(out, open(os.path.join(RAW, "models.json"), "w"), indent=1)

    # measurement candidates, per model key (plug-agnostic unless DSP)
    meas = json.load(open(os.path.join(RAW, "squigrank", "results_latest_iem_harman.json")))["devices"]
    mnames = defaultdict(list)
    for d in meas:
        mnames[norm(d["name"])].append(d)
    keys = sorted({m["key"] for m in out})
    tasks = []
    for k in keys:
        m = next(x for x in out if x["key"] == k)
        brand, model = m["brand"], m["model"]
        q = f"{brand} {model}"
        qt = toks(q)
        btoks = toks(brand)
        scored = []
        for n in mnames:
            nt = toks(n)
            if not (btoks & nt) and not (toks(model) and toks(model) <= nt):
                continue
            r = difflib.SequenceMatcher(None, q, n).ratio()
            j = len(qt & nt) / max(1, len(qt | nt))
            scored.append((0.5 * r + 0.5 * j, n))
        scored.sort(reverse=True)
        tasks.append({
            "key": k, "store_titles": sorted({l["title"] for x in out if x["key"] == k for l in x["listings"]}),
            "plugs": sorted({x["plug"] for x in out if x["key"] == k}),
            "candidates": [{"name": n, "score": round(s, 3), "examples": sorted({d["name"] for d in mnames[n]})[:3],
                            "n_measurements": len(mnames[n])} for s, n in scored[:12]],
        })
    json.dump(tasks, open(os.path.join(RAW, "match_tasks.json"), "w"), indent=1)
    print(len(listings), "listings ->", len(out), "model+plug rows,", len(keys), "unique models")
