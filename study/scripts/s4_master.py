"""Step 4: build the curated master list.

Joins store models (raw/models.json) with the agents' measurement matches
(raw/agent/out_*.json) and the measurement metrics (squig-rank export),
then writes raw/master.json and IEM_India_Master_List.xlsx.

Harman in-ear predicted preference (Olive et al., AES 2017, rescaled form):
    PPI = 100.0795 - 8.5*SD - 6.796*|slope| - 3.475*mean_abs_error
Computed by us from each measurement's SD / slope / mean error.
Per product: median within each measurer's database, then median across measurers.
"""
import glob, json, os, statistics as st, sys
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(ROOT, "raw")
EXCLUDE_DOMAINS = {"graph.hangout.audio"}  # Crinacle: raw data not public, fetched via a protected proxy


def ppi(d):
    return 100.0795 - 8.5 * d["stdev"] - 6.796 * abs(d["slope"]) - 3.475 * d["avgError"]


def main():
    models = json.load(open(os.path.join(RAW, "models.json")))
    matches = {}
    for f in sorted(glob.glob(os.path.join(RAW, "agent", "out_*.json"))):
        matches.update(json.load(open(f)))
    meas = json.load(open(os.path.join(RAW, "squigrank", "results_latest_iem_harman.json")))["devices"]
    by_name = defaultdict(list)
    for d in meas:
        if d["sourceDomain"] not in EXCLUDE_DOMAINS:
            by_name[d["name"]].append(d)

    missing = [m["key"] for m in models if m["key"] not in matches]
    if missing:
        print("WARNING no agent decision for", len(missing), "keys, e.g.", missing[:5])

    rows = {}
    for m in models:
        a = matches.get(m["key"], {})
        if a.get("not_iem"):
            continue
        canon = a.get("canonical") or m["display"]
        plug = m["plug"]
        r = rows.setdefault((canon, plug), {
            "name": canon, "brand": m["brand"], "plug": plug,
            "collab": bool(a.get("is_collab_edition") or m["collab"]),
            "listings": [], "match": set(), "proxy": set(), "confidence": set(), "notes": set(),
        })
        r["listings"] += m["listings"]
        r["match"] |= set(a.get("match", []))
        r["proxy"] |= set(a.get("proxy_match", []))
        if a.get("confidence"):
            r["confidence"].add(a["confidence"])
        if a.get("note"):
            r["notes"].add(a["note"])

    out = []
    for r in rows.values():
        ls = r["listings"]
        stock = [x for x in ls if x["in_stock"]]
        best = min(stock or ls, key=lambda x: x["price"])
        per_domain = defaultdict(list)
        is_proxy = not r["match"] and bool(r["proxy"])
        for n in (r["match"] or r["proxy"]):
            for d in by_name.get(n, []):
                per_domain[d["sourceDomain"]].append(d)
        dom_med = {k: {
            "ppi": st.median(ppi(d) for d in v),
            "sd": st.median(d["stdev"] for d in v),
            "slope": st.median(d["slope"] for d in v),
            "err": st.median(d["avgError"] for d in v),
        } for k, v in per_domain.items()}
        n = len(dom_med)
        conf = "high" if r["confidence"] == {"high"} else ("low" if "low" in r["confidence"] else "medium")
        rec = {
            "name": r["name"], "brand": r["brand"], "plug": r["plug"], "collab": r["collab"],
            "best_price": best["price"], "best_store": best["store"], "best_url": best["url"],
            "mrp": max((x["mrp"] or 0) for x in ls) or None,
            "in_stock": bool(stock), "mic": any(x["mic"] for x in ls),
            "stores": sorted({x["store"] for x in ls}),
            "n_measurers": n,
            "ppi": round(st.median(v["ppi"] for v in dom_med.values()), 1) if n else None,
            "ppi_spread": round(max(v["ppi"] for v in dom_med.values()) - min(v["ppi"] for v in dom_med.values()), 1) if n > 1 else None,
            "sd": round(st.median(v["sd"] for v in dom_med.values()), 2) if n else None,
            "slope": round(st.median(v["slope"] for v in dom_med.values()), 2) if n else None,
            "err": round(st.median(v["err"] for v in dom_med.values()), 2) if n else None,
            "sources": sorted(dom_med),
            "status": ("Proxy: base model measured, collab tuning unverified" if is_proxy else "Measured") if n else "Buyer beware: no measurement",
            "match_confidence": conf if n else None,
            "notes": "; ".join(sorted(r["notes"]))[:300],
            "store_titles": sorted({x["title"] for x in ls}),
            "listing_keys": sorted({f'{x["store"]}:{x["handle"]}' for x in ls}),
        }
        out.append(rec)
    out.sort(key=lambda x: (x["ppi"] is None, -(x["ppi"] or 0), x["best_price"]))
    json.dump(out, open(os.path.join(RAW, "master.json"), "w"), indent=1)
    meas_n = sum(1 for x in out if x["ppi"] is not None)
    print(len(out), "rows;", meas_n, "measured;", len(out) - meas_n, "buyer beware")
    for plug in ("Type-C", "3.5mm"):
        sub = [x for x in out if x["plug"] == plug]
        print(plug, len(sub), "rows,", sum(1 for x in sub if x["ppi"] is not None), "measured")


if __name__ == "__main__":
    main()
