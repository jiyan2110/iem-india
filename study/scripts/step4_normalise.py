"""Step 4: merge inconsistent spec labels into standard columns and derive scoring inputs."""
import json, os, re, sys

raw = sys.argv[1]
prods = json.load(open(os.path.join(raw, "products.json")))

CANON = [  # (column, regex on lowercase label)
    ("Driver Configuration", r"^(driver|drivers|driver type|driver config\w*|unit configuration|dynamic driver|planar magnetic driver|structure)$"),
    ("Diaphragm", r"diaphragm|coil|magnet"),
    ("Impedance", r"^imped"),
    ("Sensitivity", r"^(sen\w*sitivity|senitivity|spl|max spl|sound pressure level)"),
    ("Frequency Response", r"^(effective )?freq"),
    ("THD / Distortion", r"thd|distortion"),
    ("Channel Balance", r"channel difference|^balance$"),
    ("Connector", r"^(connector|connectors|pin type)$"),
    ("Plug", r"^(plug|plug type|plug connector|wired connectivity)$"),
    ("Microphone", r"^(microphone|remote|functions)$"),
    ("Detachable Cable", r"^detachable cable$"),
    ("Cable", r"^(cable|cable type|cable material|wire material)$"),
    ("Cable Length", r"^cable length$"),
    ("Shell / Housing", r"housing|shell|cavity|earphone material"),
    ("Weight", r"weight"),
    ("Wearing Style", r"wearing|earphone style"),
    ("Box Contents", r"^box content"),
]
OTHER_SKIP = r"^(colou?rs?|compatibility|decoding support|package weight|dimensions)$"


def yes_no(s):
    s = (s or "").lower()
    if re.search(r"\b(no|not available|without|non-detachable|fixed)\b", s) and not re.search(r"\b(with|yes)\b", s):
        return "No"
    if re.search(r"\b(yes|with|available|inline|in-line)\b", s):
        return "Yes"
    return ""


WORDS = {"single": 1, "one": 1, "dual": 2, "two": 2, "triple": 3, "three": 3, "quad": 4,
         "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "ten": 10}
NUM = r"(?<![\w-])(\d{1,2}(?!\d)|" + "|".join(WORDS) + r")"
KINDS = {
    "dd": r"(?<![a-z])(?:dynamic|dd)\b",
    "ba": r"(?<![a-z])(?:balanced armatures?|ba)\b",
    "pl": r"\bplanar",
    "est": r"\b(?:electrostatic|est)\b",
    "pz": r"\b(?:piezo\w*|bone conduction)",
}
TRAIL = r"(?:\s+(?:drivers?|units?|driver unit))*\s*x\s*(\d)\b"
# Page text checked by hand where the wording defeats the rules above.
OVERRIDE = {"CrinEar - Nightfall": ("Multi-DD", 2)}  # "10mm full-range DD | 8mm subwoofer DD"


def _seg_counts(seg):
    seg = re.sub(r"\d+(\.\d+)?\s*mm\S*", " ", seg)          # strip sizes like 10mm, 6.4mmΦ
    seg = re.sub(r"dual[\s-]?(magnetic|magnet|chamber|cavity)\w*", " ", seg)  # one driver, two magnets
    seg = re.sub(r"\b\d+(st|nd|rd|th)\b|multi-dynamic|\bdiaphragm\b", " ", seg)  # ordinals / descriptive words
    res = {}
    for k, pat in KINDS.items():
        n = 0
        for m in re.finditer(r"(?:" + NUM + r"\s*(?:x\s*)?(?:[a-z\-+]+\s+){0,2}?)?" + pat + r"(?:" + TRAIL + r")?", seg):
            q, t = m.group(1), m.group(2)
            if q:
                n += int(q) if q.isdigit() else WORDS[q]
            elif t:
                n += int(t)
            else:
                n += 1
        res[k] = n
    return res


def drivers(cfg):
    s = (cfg or "").lower()
    best = {k: 0 for k in KINDS}
    for seg in re.split(r"\s;\s|；|\|", s):            # take max per kind across spec lines
        c = _seg_counts(seg)
        for k in best:
            best[k] = max(best[k], c[k])
    dd, ba, pl, est, pz = (best[k] for k in KINDS)
    total = dd + ba + pl + est + pz
    kinds = sum(1 for k in (dd, ba, pl, est, pz) if k)
    if "hybrid" in s and kinds < 2:
        kinds, total = 2, max(total, 2)
    if not total:
        total = 1
    if kinds >= 3:
        t = "Tribrid"
    elif kinds == 2:
        t = "Hybrid"
    elif pl:
        t = "Planar"
    elif ba:
        t = "All-BA"
    elif dd > 1:
        t = "Multi-DD"
    else:
        t = "Single DD"
    return t, total


out = []
for x in prods:
    sp = x["specs"]
    row = {c: "" for c, _ in CANON}
    other = []
    for k, v in sp.items():
        lk = k.lower().strip()
        for col, pat in CANON:
            if re.search(pat, lk):
                row[col] = (row[col] + " ; " + v) if row[col] else v
                break
        else:
            if not re.search(OTHER_SKIP, lk):
                other.append(f"{k}: {v}")
    box = row["Box Contents"].lower()
    allv = [v for v in x["variants"] if v["available"]]
    vt = " ".join(v["title"] for v in x["variants"]).lower()
    blob = " ".join([row["Plug"], row["Cable"], row["Box Contents"], vt]).lower()

    TC = r"type\s*-?\s*c\b|usb\s*-?\s*c\b|\bdsp\b|with dac"   # 'with dac' = Meze Alba's USB-C DAC variant
    tc_all = [v for v in x["variants"] if re.search(TC, v["title"], re.I)]
    tc_variant = [v for v in tc_all if v["available"]]
    if tc_variant:
        typec = "Yes (variant)"
    elif tc_all:
        typec = "Sold out"          # a Type-C version exists but every one is out of stock
    elif re.search(r"type\s*-?\s*c\b|usb\s*-?\s*c\b", " ".join([row["Plug"], row["Cable"], row["Box Contents"]]).lower()):
        typec = "Yes (in box)"      # no Type-C variants; the listed plug/cable/adapter covers it
    else:
        typec = "No"

    mic = yes_no(row["Microphone"])
    if re.search(r"with mic|w/ mic|mic\)", vt):
        mic = "Yes"
    if not mic:
        mic = "Yes" if re.search(r"\bmic", blob) and not re.search(r"without mic|no mic", blob) else "No"

    det = "" if re.fullmatch(r"\s*(na|n/a)\s*", row["Detachable Cable"], re.I) else yes_no(row["Detachable Cable"])
    if not det:
        conn = (row["Connector"] + " " + row["Cable"] + " " + box).lower()
        if re.search(r"2[\s-]?pin|mmcx|0\.7[58]\s*mm|qdc|detachable", conn):
            det = "Yes"
        elif re.search(r"fixed|non-detachable", conn):
            det = "No"
        elif re.fullmatch(r"\s*(na|n/a)\s*", row["Detachable Cable"], re.I) or not row["Connector"]:
            det = "Not stated"
        else:
            det = "No"

    case = "Yes" if re.search(r"case|pouch|bag|box\b.*storage|storage", box) else "No"
    tip_lines = len(re.findall(r"tip", box))
    tips = "Yes" if (tip_lines >= 2 or re.search(r"foam|sets|\b[2-9] pairs|x\s?[2-9]\b.*tip|tip.*x\s?[2-9]", box)) else "No"
    extra = "Yes" if re.search(r"modular|interchangeable|nozzle|filter|4\.4mm.*3\.5mm|3\.5mm.*4\.4mm|adapter|dongle|tuning", box) else "No"

    dtype, dcount = OVERRIDE.get(x["title"]) or drivers(row["Driver Configuration"] or x["title"])

    pick = (sorted(tc_variant, key=lambda v: v["price"]) or sorted(allv, key=lambda v: v["price"]))[0]
    rec = {
        "IEM": x["title"].split(" - ", 1)[-1] if " - " in x["title"] else x["title"],
        "Brand": x["vendor"],
        "Full name": x["title"],
        **row,
        "Other Specs": " ; ".join(other),
        "Driver Type": dtype, "Driver Count": dcount,
        "Type-C": typec, "Mic": mic, "Detachable": det,
        "Case": case, "Extra Tips": tips, "Extra Plugs/Nozzles": extra,
        "Rating": x["rating"], "Reviews": x["reviews"],
        "Variants": " | ".join(f"{v['title']} ₹{v['price']:,.0f}{'' if v['available'] else ' (sold out)'}" for v in x["variants"]),
        "Priced variant": pick["title"], "MRP": pick["mrp"], "Price": pick["price"],
        "URL": x["url"],
    }
    if pick["price"] > 10000:
        continue
    out.append(rec)

json.dump(out, open(os.path.join(raw, "clean.json"), "w"), indent=1, ensure_ascii=False)
print(len(out), "rows")
for r in out:
    print(f"{r['Full name'][:34]:34} | {r['Driver Type']:9} {r['Driver Count']:>2} | C:{r['Type-C']:13} M:{r['Mic']:3} D:{r['Detachable']:3} | case {r['Case']:3} tips {r['Extra Tips']:3} xtra {r['Extra Plugs/Nozzles']:3} | {r['Rating']} ({r['Reviews']}) | ₹{r['Price']:,.0f} {r['Priced variant'][:20]}")
