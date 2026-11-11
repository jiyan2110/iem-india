"""Step 11: export the website's data bundle (derived numbers only, no raw curves).

Writes ../site/data/{iems.json, removed.json, meta.json}.
Run after s9 (scores) and s4 (master).
"""
import datetime, json, math, os, re

ROOT = os.path.join(os.path.dirname(__file__), "..")
SITE = os.path.join(ROOT, "..", "site", "data")
M = json.load(open(os.path.join(ROOT, "raw", "master.json")))
S = json.load(open(os.path.join(ROOT, "raw", "scores.json")))
W = {"sound": 60, "hardware": 30, "box": 10}
LO, HI = 40.0, 90.0


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def r1(x, n=1):
    return None if x is None else round(x, n)


rows, removed = [], []
for m in M:
    s = S[f'{m["name"]}|{m["plug"]}']
    pg = s.get("page") or {}
    sound_frac = max(0.0, min(1.0, (s["lb"] - LO) / (HI - LO)))
    rec = {
        "id": slug(f'{m["name"]}-{m["plug"]}'),
        "name": m["name"], "brand": m["brand"], "plug": m["plug"], "collab": m["collab"],
        "price_inr": m["best_price"], "mrp_inr": m["mrp"], "cheapest_store": m["best_store"], "url": m["best_url"],
        "stores": m["stores"], "availability": s["availability"], "availability_note": s["availability_why"],
        "measurement_status": ("measured" if m["status"] == "Measured" else "proxy" if m["status"].startswith("Proxy") else "buyer_beware"),
        "harman_score": m["ppi"], "harman_adjusted": r1(s["lb"], 2), "n_measurers": m["n_measurers"], "score_spread": m["ppi_spread"],
        "sd_db": m["sd"], "tilt_slope": m["slope"], "mean_error_db": m["err"], "measurers": m["sources"],
        "match_confidence": m["match_confidence"],
        "parts": {"sound_frac": round(sound_frac, 4), "hardware_frac": s["hw_frac"], "box_frac": s["box_frac"]},
        "score_default": round(W["sound"] * sound_frac + W["hardware"] * s["hw_frac"] + W["box"] * s["box_frac"], 2),
        "value_score": s.get("value"),
        "hardware": s["hw"], "box": s["box"],
        "specs_as_claimed": {"impedance_ohm": pg.get("impedance_ohm"), "sensitivity_db_mw": pg.get("sens_db_mw"),
                             "eartip_pairs": pg.get("eartip_pairs"), "eartip_kinds": pg.get("eartip_kinds"),
                             "warranty_months": pg.get("warranty_months"), "connector": None},
    }
    (removed if s["availability"] == "Discontinued" else rows).append(rec)

for plug in ("Type-C", "3.5mm"):
    sub = sorted([r for r in rows if r["plug"] == plug], key=lambda r: -r["score_default"])
    for i, r in enumerate(sub, 1):
        r["rank_default"] = i

os.makedirs(SITE, exist_ok=True)
json.dump(rows, open(os.path.join(SITE, "iems.json"), "w"), indent=1, ensure_ascii=False)
json.dump([{k: r[k] for k in ("id", "name", "plug", "availability_note", "harman_score", "price_inr")} for r in removed],
          open(os.path.join(SITE, "removed.json"), "w"), indent=1, ensure_ascii=False)

meta = {
    "built": str(datetime.date.today()),
    "scope": "New wired IEMs sold in India at or under Rs 10,000; Type-C and 3.5mm ranked separately; sold-out kept unless discontinued.",
    "counts": {"listed": len(rows), "type_c": sum(r["plug"] == "Type-C" for r in rows), "3_5mm": sum(r["plug"] == "3.5mm" for r in rows),
               "removed_discontinued": len(removed),
               "measured": sum(r["measurement_status"] == "measured" for r in rows),
               "proxy": sum(r["measurement_status"] == "proxy" for r in rows),
               "buyer_beware": sum(r["measurement_status"] == "buyer_beware" for r in rows),
               "in_stock": sum(r["availability"] == "In stock" for r in rows)},
    "weights_default": W,
    "formulas": {
        "harman_score": "100.08 - 8.5*SD - 6.80*|slope| - 3.48*mean_abs_error (error vs Harman IE target, 20 Hz-10 kHz)",
        "harman_adjusted": "harman_score - sqrt(24.4 / n_measurers); proxy -5; buyer beware = 25th percentile of measured (66.9)",
        "sound_frac": "clip((harman_adjusted - 40) / (90 - 40), 0, 1)",
        "hardware_frac": "points share: detachable 9, mic 6, easy to drive 4 (3.5mm) or DSP/EQ app 6 (Type-C); unknown items imputed at the average rate",
        "box_frac": "points share: eartips 4, eartip variety 3, case 4, cable 2, adapter 2; unknown imputed at the average rate",
        "score": "W_sound*sound_frac + W_hardware*hardware_frac + W_box*box_frac (weights sum to 100)",
        "value_score": "percentile(score) - percentile(ln price), per plug, measured IEMs (in stock or sold out) in the top half by score only",
    },
    "key_numbers": {"between_measurer_variance": 24.4, "between_measurer_sd": 4.94, "harman_vs_log_price_r2": {"3.5mm": 0.001, "Type-C": 0.008}, "median_harman_3.5mm": {"price_le_2000": 78.7, "price_ge_7000": 79.2},
                    "harman_listener_split": "about 72% prefer Harman-like tuning; about 28% prefer ~2 dB less bass and 1-2 dB more treble"},
    "sources": [
        {"name": "Olive, Welti & Khonsaripour, AES 2017 (papers 9840 / 9878)", "type": "evidence", "used_for": "Harman in-ear preference model and target"},
        {"name": "Squig-Rank (github.com/PEQHUB/Squig-Rank)", "type": "data", "used_for": "per-measurement SD / slope / mean error from public squig.link databases (711-type couplers)"},
        {"name": "Headphone Zone, The Audio Store, Concept Kart product feeds and pages", "type": "data (store claims)", "used_for": "prices, stock, specs, box contents"},
        {"name": "Judge.me and Reddit policies; store robots.txt files", "type": "evidence (docs)", "used_for": "decisions on what not to collect"},
    ],
    "exclusions": ["Amazon (terms forbid scraping)", "HiFiNage (robots.txt blocks AI crawlers)",
                   "Crinacle / graph.hangout.audio (raw data not public)", "Crinacle ranking list, squig.link lists, IEMRanking.com (robots.txt blocks Claude)",
                   "Reddit (bulk collection needs approval; research outside its programme not allowed)", "Store star ratings and reviews (dropped: about 10% coverage, fake-review risk)"],
    "disclaimers": ["Specs, sound tags and box contents are as claimed by the store, not verified.",
                    "Rigs, eartips and insertion depth change measurements; treat +/-3 points as noise.",
                    "'Sold out, status unclear' items may in fact be discontinued; there is no stock history.",
                    "Raw frequency-response curves are not redistributed; only derived numbers, with credit to each measurer."],
}
json.dump(meta, open(os.path.join(SITE, "meta.json"), "w"), indent=1, ensure_ascii=False)
print("wrote", len(rows), "IEMs,", len(removed), "removed ->", os.path.abspath(SITE))
print(json.dumps(meta["counts"]))
