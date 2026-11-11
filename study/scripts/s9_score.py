"""Step 9: score every IEM with the agreed spec (debate/proposal_v2.md, critic ACCEPT).

Parts (weights live in the workbook's Weights sheet; these are defaults):
  Sound 60      Harman PPI minus a margin of error that shrinks with the number of measurers:
                  LB = ppi - sqrt(SIG2 / n)            SIG2 = 24.4 (pooled between-measurer variance,
                                                       206 IEMs with 2+ measurers; debate/scripts/engine.py)
                  Proxy (collab, base model measured): LB - 5
                  Buyer beware (no measurement): LB = 25th percentile of measured LB
                  points = W * clip((LB - 40) / 50, 0, 1)
  Hardware 30   share of hardware points: detachable cable 9, mic 6, easy to drive 4 (3.5 mm only),
                DSP / EQ app 6 (Type-C only). Unknown items are imputed at the average rate for that plug
                (mic: overall rate), never scored 0, so terse store pages are not punished.
  In the box 10 eartips 4, eartip variety 3, case/pouch 4, cable 2, adapter 2, as claimed by the store.
                Unknown imputed at the average. Decorative until product pages are fetched.
Discontinued (removed): sold out everywhere AND (clearance tag OR a newer version is in stock on our list).
Sold-out rows otherwise stay, flagged "Sold out, restocking signs" or "Sold out, status unclear".
Value: score-rank minus price-rank (percentiles of score and ln price), per plug, measured IEMs (sold-out included),
       only for IEMs in the top half by score. Not a fitted curve: score vs price R2 is about 0.01.
Output: raw/scores.json keyed "name|plug".
"""
import collections, datetime as dt, json, math, os, re, statistics as st

ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(ROOT, "raw")
SIG2, PROXY_PEN, LO, HI = 24.4, 5.0, 40.0, 90.0
HWPTS = {"detach": 9, "mic": 6, "drive": 4, "dsp": 6}
BXPTS = {"tips": 4, "tip_variety": 3, "case": 4, "cable": 2, "adapter": 2}
CLEAR = {"closeout", "collection_dom-clearance", "dom-clearance"}
PRE = {"coming-soon", "pre-order", "sd_preorder", "pre-order_4-6", "__labelpo:pre-order"}
NOW = dt.datetime(2026, 11, 10, 11, 0, tzinfo=dt.timezone.utc)  # catalogue snapshot

M = json.load(open(os.path.join(RAW, "master.json")))
CAT = {s: {(p.get("handle") or p.get("slug")): p for p in json.load(open(os.path.join(RAW, f"catalogue_{s}.json")))}
       for s in ("headphonezone", "theaudiostore", "conceptkart", "hifinage")
       if os.path.exists(os.path.join(RAW, f"catalogue_{s}.json"))}


def strip(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h or ""))


def products(r):
    for k in r["listing_keys"]:
        s, h = k.split(":", 1)
        if CAT[s].get(h):
            yield s, CAT[s][h]


def tags(s, p):
    return [t["name"] if isinstance(t, dict) else t for t in (p.get("tags") or [])]


def body(r):
    return " ".join(strip(p.get("description")) + " " + strip(p.get("short_description")) if s == "hifinage"
                    else strip(p.get("body_html")) for s, p in products(r))


def alltext(r):
    extra = " ".join(r["store_titles"])
    for s, p in products(r):
        extra += " " + " ".join(tags(s, p))
        if s == "hifinage":
            extra += " " + " ".join(a["name"] + " " + " ".join(t["name"] for t in a["terms"]) for a in p.get("attributes", []))
    return body(r) + " " + extra


# ---------- hardware detection (as claimed by the store)
DET = re.compile(r"detachable|removable cable|2[- ]?pin|0\.7[58] ?mm|\bmmcx\b|\bqdc\b|interchangeable cable|swappable cable", re.I)
FIX = re.compile(r"non[- ]?detachable|fixed cable|\bfixed\b|integrated cable", re.I)
DSP = re.compile(r"\bDSP\b|\bEQ\b|equali[sz]er|companion app|\bapp\b|firmware", re.I)


def detach(t):
    if DET.search(t) and not re.search(r"non[- ]?detachable", t, re.I):
        return True
    return False if FIX.search(t) else None


def drive(t):
    z = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*(?:Ω|ohms?)\b", t, re.I) if 8 <= float(x) <= 300]
    s = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*dB(?:\s*/\s*(?:mW|Vrms|V))?", t, re.I) if 80 <= float(x) <= 130]
    z, s = (z[0] if z else None), (s[0] if s else None)
    if z is None and s is None:
        return None
    if z is not None:
        return z <= 32 and (s is None or s >= 98)
    return s >= 105


def hw_items(r):
    t = alltext(r)
    d = {"detach": detach(t), "mic": True if r["mic"] else None}
    if r["plug"] == "Type-C":
        # no description at all (e.g. Headphone Zone keeps specs off its feed) = unknown, not "no DSP"
        d["dsp"] = True if DSP.search(t) else (False if len(body(r).strip()) >= 50 else None)
    else:
        d["drive"] = drive(t)
    return d


# ---------- box contents (as claimed by the store)
SEC = re.compile(r"(in the box|inside the box|box contents?|package (?:includes|contents?|list)|what.?s in (?:the )?box|"
                 r"accessories included|included accessories|in the package|packing list|accessor(?:y|ies)[: ]|what you get|what.s included)(.{0,420})", re.I)


def box_items(r):
    """{item: True/False/None}; None = store does not say."""
    t = body(r)
    secs = [m.group(2) for m in SEC.finditer(t)]
    if secs:
        s = " ".join(secs)
        kinds = sum(bool(re.search(x, s, re.I)) for x in (r"silicone", r"foam", r"wide|thick", r"narrow|thin", r"s ?/ ?m ?/ ?l|small.{0,10}large"))
        n = re.search(r"(\d+)\s*(?:sets?|pairs?)", s, re.I)
        return {"tips": bool(re.search(r"ear ?tips?|tips|silicone|foam", s, re.I)),
                "tip_variety": kinds >= 2 or bool(n and int(n.group(1)) >= 3),
                "case": bool(re.search(r"\bcase\b|pouch|\bbag\b|carrying|storage box", s, re.I)),
                "cable": bool(re.search(r"\bcable\b|\bcord\b", s, re.I)),
                "adapter": bool(re.search(r"adapter|adaptor|dongle|converter|type-?c to|usb-?c to", s, re.I))}
    inc = r"(?:comes|come|includes?|included|with|bundled|free)[^.]{0,80}"
    d = {"tips": bool(re.search(inc + r"(?:ear ?tips?|tips)", t, re.I)),
         "tip_variety": bool(re.search(r"(?:\d+|multiple|several|variety)[^.]{0,15}(?:pairs?|sets?|sizes)[^.]{0,20}tips", t, re.I)),
         "case": bool(re.search(inc + r"(?:case|pouch|carrying bag)", t, re.I)),
         "cable": None,
         "adapter": bool(re.search(inc + r"(?:adapter|adaptor|dongle)", t, re.I))}
    # free-text mentions only prove presence; absence there is unknown
    return {k: (True if v else None) for k, v in d.items()}


# ---------- product-page extraction (s10 + Sonnet agents, raw/agent_pages/out_*.json) overrides feed text
PAGE = {}
for _f in sorted(__import__("glob").glob(os.path.join(RAW, "agent_pages", "out_*.json"))):
    PAGE.update(json.load(open(_f)))


def merge_bool(vals):
    vals = [v for v in vals if v is not None]
    return True if True in vals else (False if vals else None)


def page_info(r):
    ps = [PAGE[k] for k in r["listing_keys"] if k in PAGE]
    if not ps:
        return None
    out = {k: merge_bool([p.get(k) for p in ps]) for k in
           ("detachable", "mic", "dsp_or_eq_app", "case", "cable_in_box", "extra_cable_or_plug", "adapter")}
    out["box_listed"] = any(p.get("box_listed") for p in ps)
    for k in ("eartip_pairs", "eartip_kinds", "warranty_months"):
        v = [p[k] for p in ps if isinstance(p.get(k), (int, float))]
        out[k] = max(v) if v else None
    z = [p["impedance_ohm"] for p in ps if isinstance(p.get("impedance_ohm"), (int, float)) and 4 <= p["impedance_ohm"] <= 600]
    out["impedance_ohm"] = z[0] if z else None
    s = None
    for p in ps:  # sensitivity in dB/mW; dB/Vrms converted with the impedance: S_mW = S_V - 10*log10(1000/Z)
        v, u = p.get("sensitivity_db"), (p.get("sensitivity_unit") or "mW")
        if isinstance(v, (int, float)) and 80 <= v <= 135:
            if u in ("Vrms", "V") and out["impedance_ohm"]:
                v = v - 10 * math.log10(1000 / out["impedance_ohm"])
            elif u in ("Vrms", "V", "Pa"):
                continue
            s = round(v, 1)
            break
    out["sens_db_mw"] = s
    return out


def drive_from(z, s):
    if z is None and s is None:
        return None
    if z is not None:
        return z <= 32 and (s is None or s >= 98)
    return s >= 105


def hw_items_page(r, pg):
    d = hw_items(r)
    if pg is None:
        return d
    if pg["detachable"] is not None:
        d["detach"] = pg["detachable"]
    if pg["mic"] is True:
        d["mic"] = True
    if r["plug"] == "Type-C":
        if pg["dsp_or_eq_app"] is not None:
            d["dsp"] = pg["dsp_or_eq_app"]
    else:
        dv = drive_from(pg["impedance_ohm"], pg["sens_db_mw"])
        if dv is not None:
            d["drive"] = dv
    return d


def box_items_page(r, pg):
    if pg is None or not (pg["box_listed"] or any(pg[k] for k in ("case", "adapter", "extra_cable_or_plug")) or pg["eartip_pairs"]):
        return box_items(r)
    listed = pg["box_listed"]
    pairs, kinds = pg["eartip_pairs"], pg["eartip_kinds"]
    def b(v):  # with an explicit box list, anything not listed is absent
        return v if v is not None else (False if listed else None)
    return {"tips": True if (pairs or kinds) else b(None),
            "tip_variety": (bool((kinds or 0) >= 2 or (pairs or 0) >= 5) if (pairs or kinds) else b(None)),
            "case": b(pg["case"]),
            "cable": b(True if (pg["cable_in_box"] or pg["extra_cable_or_plug"]) else (pg["cable_in_box"] if pg["cable_in_box"] is not None else None)),
            "adapter": b(pg["adapter"])}


def frac(items, pts, rates):
    num = den = 0
    for it, v in items.items():
        p = pts[it]
        num += p * (rates[it] if v is None else (1 if v else 0))
        den += p
    return num / den


# ---------- availability
def pdate(s):
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def words(n):
    return re.findall(r"[a-z0-9\+]+", n.lower().replace("-", " "))


VER = re.compile(r"^(?:2|3|4|5|ii|iii|iv|v2|v3|mk2|mkii|2nd)$")
TOK = [words(r["name"]) for r in M]


def successor_in_stock(i):
    a = M[i]
    for j, b in enumerate(M):
        if i != j and a["brand"] == b["brand"] and b["in_stock"] and len(TOK[j]) > len(TOK[i]) \
                and TOK[j][:len(TOK[i])] == TOK[i] and all(VER.match(x) for x in TOK[j][len(TOK[i]):]):
            return b["name"]
    return None


def availability(i):
    r = M[i]
    if r["in_stock"]:
        return "In stock", ""
    tg, ages, backorder = set(), [], False
    for s, p in products(r):
        tg |= {t.lower() for t in tags(s, p)}
        if s == "hifinage":
            backorder |= bool(p.get("is_on_backorder"))
        elif pdate(p.get("published_at") or ""):
            ages.append((NOW - pdate(p["published_at"])).days)
    if tg & CLEAR:
        return "Discontinued", "store clearance tag"
    succ = successor_in_stock(i)
    if succ:
        return "Discontinued", f"newer version in stock: {succ}"
    why = [w for w, ok in (("'back in stock' tag", "back in stock" in tg), ("pre-order tag", bool(tg & PRE)),
                           ("on backorder", backorder), ("listed under 6 months ago", bool(ages) and min(ages) < 180)) if ok]
    return ("Sold out, restocking signs", "; ".join(why)) if why else ("Sold out, status unclear", "")


def pct(vals):
    order = sorted(range(len(vals)), key=lambda k: vals[k])
    out = [0.0] * len(vals)
    for rank, k in enumerate(order):
        out[k] = 100 * rank / max(1, len(vals) - 1)
    return out


def main():
    PG = [page_info(r) for r in M]
    HW = [hw_items_page(r, pg) for r, pg in zip(M, PG)]
    BX = [box_items_page(r, pg) for r, pg in zip(M, PG)]
    # imputation rates
    hw_rate = {}
    for plug in ("3.5mm", "Type-C"):
        for it in HWPTS:
            v = [HW[i][it] for i, r in enumerate(M) if r["plug"] == plug and HW[i].get(it) is not None]
            hw_rate[(plug, it)] = sum(v) / len(v) if v else 0.5
    mic_rate = sum(1 for h in HW if h["mic"]) / len(M)  # share of IEMs with a mic claimed (feed or product page)
    bx_rate = {it: (lambda v: sum(v) / len(v) if v else 0.5)([b[it] for b in BX if b[it] is not None]) for it in BXPTS}

    lb = {}
    for i, r in enumerate(M):
        if r["ppi"] is not None:
            lb[i] = r["ppi"] - math.sqrt(SIG2 / r["n_measurers"]) - (PROXY_PEN if r["status"].startswith("Proxy") else 0)
    bb_lb = sorted(lb.values())[len(lb) // 4]

    out = {}
    for i, r in enumerate(M):
        rates = {it: (mic_rate if it == "mic" else hw_rate[(r["plug"], it)]) for it in HW[i]}
        L = lb.get(i, bb_lb)
        avail, why = availability(i)
        out[f'{r["name"]}|{r["plug"]}'] = {
            "lb": round(L, 2), "sound_frac": round(min(1, max(0, (L - LO) / (HI - LO))), 4),
            "hw_frac": round(frac(HW[i], HWPTS, rates), 4), "box_frac": round(frac(BX[i], BXPTS, bx_rate), 4),
            "hw": HW[i], "box": BX[i], "box_known": sum(v is not None for v in BX[i].values()),
            "availability": avail, "availability_why": why,
            "page": PG[i],
        }
    # value (default weights), per plug
    W = (60, 30, 10)
    for plug in ("3.5mm", "Type-C"):
        sub = [(k, v) for k, v in out.items() if k.endswith("|" + plug) and v["availability"] != "Discontinued"
               and M[[f'{x["name"]}|{x["plug"]}' for x in M].index(k)]["ppi"] is not None]
        tot = [W[0] * v["sound_frac"] + W[1] * v["hw_frac"] + W[2] * v["box_frac"] for _, v in sub]
        price = {f'{x["name"]}|{x["plug"]}': x["best_price"] for x in M}
        ps, pp = pct(tot), pct([math.log(price[k]) for k, _ in sub])
        for (k, v), a, b in zip(sub, ps, pp):
            if a >= 50:
                v["value"] = round(a - b, 1)
    json.dump(out, open(os.path.join(RAW, "scores.json"), "w"), indent=1)
    c = collections.Counter(v["availability"] for v in out.values())
    print("availability:", dict(c))
    print("buyer-beware LB", round(bb_lb, 1), "| mic rate", round(mic_rate, 3), "| rows with any box info", sum(v["box_known"] > 0 for v in out.values()))
    print("value-ranked rows:", sum("value" in v for v in out.values()))


if __name__ == "__main__":
    main()
