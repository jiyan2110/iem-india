"""Step 1: download full product catalogues from Indian stores (politely, cached).

Shopify stores: paginate /products.json?limit=250&page=N.
HiFiNage (WooCommerce): Store API /wp-json/wc/store/v1/products.
Output: raw/catalogue_<store>.json (list of raw product dicts).
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from polite import fetch

ROOT = os.path.join(os.path.dirname(__file__), "..")
CACHE = os.path.join(ROOT, "raw", "cache")

SHOPIFY = {
    "headphonezone": "https://www.headphonezone.in/collections/in-ear-monitors/products.json",
    "theaudiostore": "https://www.theaudiostore.in/products.json",
    "conceptkart": "https://conceptkart.com/products.json",
}


def shopify(name, base):
    out = []
    for page in range(1, 60):
        data = fetch(f"{base}?limit=250&page={page}", CACHE)
        if not data:
            print(f"{name}: no data on page {page}", flush=True)
            break
        prods = json.loads(data).get("products", [])
        print(f"{name}: page {page} -> {len(prods)}", flush=True)
        if not prods:
            break
        out.extend(prods)
    return out


def woo(name, base):
    out = []
    for page in range(1, 40):
        data = fetch(f"{base}?per_page=100&page={page}", CACHE)
        if not data:
            break
        try:
            prods = json.loads(data)
        except ValueError:
            print(f"{name}: non-JSON on page {page}", flush=True)
            break
        print(f"{name}: page {page} -> {len(prods)}", flush=True)
        if not prods:
            break
        out.extend(prods)
    return out


if __name__ == "__main__":
    only = sys.argv[1:]
    for name, base in SHOPIFY.items():
        if only and name not in only:
            continue
        prods = shopify(name, base)
        json.dump(prods, open(os.path.join(ROOT, "raw", f"catalogue_{name}.json"), "w"))
        print(f"DONE {name}: {len(prods)} products", flush=True)
    # HiFiNage dropped 2026-11-10: its robots.txt blocks Claude's crawlers, so we don't collect from it at all.
