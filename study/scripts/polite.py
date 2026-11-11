"""Polite fetcher: honours Retry-After, waits between requests, caches to disk."""
import hashlib, os, sys, time, urllib.request, urllib.error

UA = "Mozilla/5.0 (personal price comparison; low rate)"
GAP = float(os.environ.get("GAP", "4"))
_last = [0.0]


def fetch(url, cache_dir, max_tries=6):
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, hashlib.sha1(url.encode()).hexdigest()[:16])
    if os.path.exists(path):
        return open(path, "rb").read()
    for attempt in range(max_tries):
        wait = _last[0] + GAP - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            open(path, "wb").write(data)
            return data
        except urllib.error.HTTPError as e:
            if e.code == 429:
                ra = int(e.headers.get("Retry-After", "60") or 60)
                print(f"429 on {url}; sleeping {ra + 5}s", file=sys.stderr, flush=True)
                time.sleep(ra + 5)
                continue
            if e.code == 404:
                return None
            print(f"HTTP {e.code} on {url}", file=sys.stderr, flush=True)
            time.sleep(10)
        except Exception as e:  # network hiccup
            print(f"error {e!r} on {url}", file=sys.stderr, flush=True)
            time.sleep(10)
    return None
