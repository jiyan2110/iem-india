"""Step 2: keep new, wired IEMs <= Rs 10,000 from each store and split by plug.

One output row per (store, product, plug) where plug is 'Type-C' or '3.5mm'.
Sold-out variants are kept (in_stock=False) because the study includes them.
Output: raw/listings.json
"""
import html, json, os, re, sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(ROOT, "raw")
BUDGET = 10000

TC = re.compile(r"type\s*-?\s*c\b|usb\s*-?\s*c\b|\bdsp\b|with dac", re.I)
NOT_IEM = re.compile(
    r"\bcable\b|ear\s*tips?|eartips|\btips\b|\bcase\b|pouch|adapter|dongle|\bdac\b|\bamp\b|amplifier|"
    r"\btws\b|true wireless|wireless|bluetooth|\bbt\d|neckband|filter|nozzle|foam|stand\b|"
    r"speaker|gift card|warranty|bundle|combo|cleaning|earhook|ear hook|bone conduction|open[- ]ear|"
    r"\bear ?buds?\b|earbuds|sports earphone",
    re.I)
USED = re.compile(r"pre[- ]?owned|refurb|open[- ]?box|\bdemo\b|\bused\b|b[- ]stock|renewed", re.I)


def plug_of(text):
    return "Type-C" if TC.search(text) else "3.5mm"


def shopify_rows(store, prods, keep):
    rows = []
    for p in prods:
        if not keep(p):
            continue
        title = html.unescape(p["title"]).strip()
        if NOT_IEM.search(title) or USED.search(title):
            continue
        groups = {}
        for v in p["variants"]:
            vt = v.get("title") or ""
            # plug comes from the variant title first, then the product title / tags
            if re.search(r"3\.5|4\.4|2\.5\s*mm", vt) and not TC.search(vt):
                plug = "3.5mm"
            elif TC.search(vt):
                plug = "Type-C"
            else:
                plug = plug_of(title + " " + " ".join(p.get("tags", [])))
            if USED.search(vt):
                continue
            g = groups.setdefault(plug, [])
            g.append((float(v["price"]), bool(v.get("available")), vt))
        for plug, vs in groups.items():
            stock = [x for x in vs if x[1]]
            price = min(x[0] for x in (stock or vs))
            mrp = max(float(v.get("compare_at_price") or 0) for v in p["variants"]) or None
            if price > BUDGET or price < 300:
                continue
            rows.append({
                "store": store, "title": title, "vendor": p.get("vendor", ""),
                "plug": plug, "price": price, "mrp": mrp, "in_stock": bool(stock),
                "mic": bool(re.search(r"\bmic\b|microphone", title + " " + " ".join(x[2] for x in vs), re.I)),
                "url": f"{STORE_URL[store]}/products/{p['handle']}",
                "handle": p["handle"], "product_type": p.get("product_type", ""),
            })
    return rows


STORE_URL = {
    "headphonezone": "https://www.headphonezone.in",
    "theaudiostore": "https://www.theaudiostore.in",
    "conceptkart": "https://conceptkart.com",
}

KEEP = {
    "headphonezone": lambda p: True,  # already the in-ear-monitors collection
    "theaudiostore": lambda p: p.get("product_type") in ("IEMs", "Earphone"),
    "conceptkart": lambda p: p.get("product_type") == "In Ear Monitors",
}


def woo_rows(prods):
    rows = []
    for p in prods:
        cats = " ".join(c.get("name", "") for c in p.get("categories", []))
        if not re.search(r"earphone|iem|in-ear", cats, re.I) or re.search(r"opened box", cats, re.I):
            continue
        title = html.unescape(p["name"]).strip()
        if NOT_IEM.search(title) or USED.search(title):
            continue
        pr = p.get("prices", {})
        unit = 10 ** int(pr.get("currency_minor_unit", 2))
        rng = pr.get("price_range") or {}
        price = int(rng.get("min_amount") or pr.get("price") or 0) / unit
        reg = int(pr.get("regular_price") or 0) / unit or None
        if not (300 <= price <= BUDGET):
            continue
        plugs = {plug_of(title)}
        for a in p.get("attributes", []):
            for t in a.get("terms", []):
                plugs.add(plug_of(t.get("name", "")) if TC.search(t.get("name", "")) or re.search(r"3\.5", t.get("name", "")) else None)
        plugs.discard(None)
        for plug in plugs:
            rows.append({
                "store": "hifinage", "title": title, "vendor": "", "plug": plug, "price": price,
                "mrp": reg, "in_stock": bool(p.get("is_in_stock")),
                "mic": bool(re.search(r"\bmic\b|microphone", title, re.I)),
                "url": p.get("permalink"), "handle": p.get("slug"), "product_type": cats,
            })
    return rows


if __name__ == "__main__":
    rows = []
    for store in STORE_URL:
        f = os.path.join(RAW, f"catalogue_{store}.json")
        if os.path.exists(f):
            r = shopify_rows(store, json.load(open(f)), KEEP[store])
            print(store, len(r))
            rows += r
    # HiFiNage dropped 2026-11-10 (robots.txt blocks Claude's crawlers); woo_rows kept only for reference.
    json.dump(rows, open(os.path.join(RAW, "listings.json"), "w"), indent=1)
    print("total listings", len(rows))
