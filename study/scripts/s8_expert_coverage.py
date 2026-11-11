"""Step 8 (coverage check only): how many of our IEMs appear in public reviewer ranking lists?

Lists (all opinion sources, fetched once from their published Google Sheets; robots rules checked):
  antdroid.csv  Antdroid / Audio Discourse IEM ranking (last update May 2024)
  nkt.csv       NKT / In-ear Gems ranking database
  phil.csv      Phil's Sheet of IEM Goodness (daemonxar.com)
Excluded on purpose: Crinacle, squig.link lists (Super* Review), IEMRanking.com (their robots.txt blocks Claude).

Matching is strict (same words after normalising), so counts are a floor, not an estimate.
Near misses are printed for a human check.
"""
import csv, difflib, json, os, re, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from s3_merge import norm, BRAND_ALIASES

ROOT = os.path.join(os.path.dirname(__file__), "..")
EXP = os.path.join(ROOT, "raw", "experts")
STOP = {"iem", "iems", "in", "ear", "monitor", "monitors", "earphones", "x", "and", "the", "edition"}


def canon(s):
    s = norm(s)
    for a, b in BRAND_ALIASES.items():
        if s.startswith(a + " "):
            s = b + s[len(a):]
    s = s.replace("-", " ")
    return " ".join(t for t in s.split() if t not in STOP)


def compact(s):
    return s.replace(" ", "")


def load():
    out = {}
    rows = list(csv.reader(open(os.path.join(EXP, "antdroid.csv"))))
    out["Antdroid"] = [r[1] for r in rows[2:] if len(r) > 1 and r[1].strip()]
    out["NKT"] = [f"{r['Brand']} {r['Model']}" for r in csv.DictReader(open(os.path.join(EXP, "nkt.csv"))) if r.get("Model")]
    rows = list(csv.reader(open(os.path.join(EXP, "phil.csv"))))
    out["Phil"] = [f"{r[2]} {r[3]}" for r in rows[3:] if len(r) > 3 and r[3].strip()]
    return out


def main():
    master = json.load(open(os.path.join(ROOT, "raw", "master.json")))
    lists = load()
    idx = {k: {compact(canon(n)): n for n in v} for k, v in lists.items()}
    hits, near = {}, []
    for m in master:
        c = compact(canon(m["name"]))
        found = []
        for k, d in idx.items():
            if c in d:
                found.append(k)
            else:
                best = difflib.get_close_matches(c, d.keys(), n=1, cutoff=0.88)
                if best:
                    near.append((m["name"], k, d[best[0]]))
        hits[f'{m["name"]}|{m["plug"]}'] = found

    print("List sizes:", {k: len(v) for k, v in lists.items()})
    n = len(master)
    dist = Counter(len(v) for v in hits.values())
    print(f"\nAll {n} rows: reviewers per IEM ->", dict(sorted(dist.items())))
    for k in lists:
        print(f"  in {k}: {sum(1 for v in hits.values() if k in v)}")

    def band(p):
        return "<= Rs 2k" if p <= 2000 else ("Rs 2-5k" if p <= 5000 else "Rs 5-10k")

    print("\nBy plug and price (rows with >=1 list / >=2 lists / total):")
    for plug in ("Type-C", "3.5mm"):
        for b in ("<= Rs 2k", "Rs 2-5k", "Rs 5-10k"):
            sub = [m for m in master if m["plug"] == plug and band(m["best_price"]) == b]
            h = [hits[f'{m["name"]}|{m["plug"]}'] for m in sub]
            print(f"  {plug:6} {b:9}: {sum(1 for x in h if x):3} / {sum(1 for x in h if len(x) >= 2):3} / {len(sub)}")

    print("\nMatched IEMs:")
    for k, v in hits.items():
        if v:
            print("  ", k, v)
    print(f"\nNear misses for a human check ({len(near)}):")
    for x in near[:60]:
        print("  ", x)
    json.dump(hits, open(os.path.join(EXP, "coverage.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
