"""Step 5: write the master list workbook with live scoring formulas.

Needs raw/master.json (s4) and raw/scores.json (s9). Run s9 first.
Score parts are formulas driven by the editable Weights sheet, so readers can try their own weights.
"""
import json, os, sys, datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment

ROOT = os.path.join(os.path.dirname(__file__), "..")
rows = json.load(open(os.path.join(ROOT, "raw", "master.json")))
SC = json.load(open(os.path.join(ROOT, "raw", "scores.json")))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "IEM_India_Master_List.xlsx")
DEFAULT_W = (60, 30, 10)


def yn(v):
    return "Yes" if v is True else ("No" if v is False else "Not listed")


for r in rows:
    s = SC[f'{r["name"]}|{r["plug"]}']
    r.update(lb=s["lb"], hw_frac=s["hw_frac"], box_frac=s["box_frac"], availability=s["availability"],
             availability_why=s["availability_why"], value=s.get("value"))
    r["detach"] = yn(s["hw"]["detach"])
    r["drive_or_dsp"] = yn(s["hw"].get("dsp") if r["plug"] == "Type-C" else s["hw"].get("drive"))
    r["box_list"] = ", ".join(k.replace("_", " ") for k, v in s["box"].items() if v) or ("Not listed" if not s["box_known"] else "None of these")
    pg = s.get("page") or {}
    r["impedance"] = pg.get("impedance_ohm")
    r["sens"] = pg.get("sens_db_mw")
    r["tip_pairs"] = pg.get("eartip_pairs")
    r["warranty"] = pg.get("warranty_months")
    # same arithmetic as the sheet formulas, so the row order matches the Rank column
    r["_default"] = DEFAULT_W[0] * max(0, min(1, (s["lb"] - 40) / 50)) + DEFAULT_W[1] * s["hw_frac"] + DEFAULT_W[2] * s["box_frac"]

F = "Arial"
HEAD = PatternFill("solid", fgColor="1F3A5F")
WARN = PatternFill("solid", fgColor="FDECEA")
SOLD = PatternFill("solid", fgColor="FFF6DD")
INPUT = PatternFill("solid", fgColor="FFFF00")
# (header, key, width); a key starting with "=" is a formula column
COLS = [
    ("Rank", "=rank", 6), ("IEM", "name", 34), ("Brand", "brand", 12),
    ("Total score (out of 100)", "=total", 10), ("Sound pts", "=sound", 9), ("Hardware pts", "=hw", 9), ("In-the-box pts", "=box", 9),
    ("Best price (₹)", "best_price", 11), ("Value: score-rank minus price-rank", "value", 12),
    ("Availability", "availability", 22), ("Availability note", "availability_why", 26),
    ("Status", "status", 24), ("Harman score (median)", "ppi", 10), ("Adjusted Harman (minus margin of error)", "lb", 12),
    ("Measurers", "n_measurers", 9), ("Score spread", "ppi_spread", 9),
    ("Tilt / slope (−warm, +bright)", "slope", 10), ("SD of error (dB)", "sd", 9), ("Mean error (dB)", "err", 9),
    ("Detachable cable", "detach", 10), ("Mic", "mic", 6), ("Easy to drive (3.5mm) / DSP-EQ app (Type-C)", "drive_or_dsp", 14),
    ("In the box (as listed)", "box_list", 26), ("Eartip pairs", "tip_pairs", 8),
    ("Impedance (Ω)", "impedance", 9), ("Sensitivity (dB/mW)", "sens", 10), ("Warranty (months)", "warranty", 9),
("Hardware share (0-1)", "hw_frac", 9), ("Box share (0-1)", "box_frac", 9),
    ("Collab edition", "collab", 9), ("MRP (₹)", "mrp", 9), ("Stores", "stores", 24),
    ("Match confidence", "match_confidence", 10), ("Sources", "sources", 36), ("Cheapest at", "best_url", 36), ("Notes", "notes", 40),
]
COL = {k: get_column_letter(i) for i, (_, k, _) in enumerate(COLS, 1)}
WS = "Weights"


def header(ws, cols):
    for c, (h, _, w) in enumerate(cols, 1):
        cell = ws.cell(1, c, h)
        cell.font = Font(name=F, bold=True, color="FFFFFF")
        cell.fill = HEAD
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(c)].width = w
    ws.row_dimensions[1].height = 54


wb = Workbook()
wb.remove(wb.active)

# weights sheet first: the only cells a reader should edit
ws = wb.create_sheet(WS)
ws.column_dimensions["A"].width = 38
ws.column_dimensions["B"].width = 10
ws.column_dimensions["C"].width = 100
ws.cell(1, 1, "Edit the yellow cells to try your own weights; every score and rank updates.").font = Font(name=F, bold=True)
spec = [
    ("Sound weight", DEFAULT_W[0], "Harman in-ear preference score, adjusted for how many people measured it."),
    ("Hardware & practicality weight", DEFAULT_W[1], "Detachable cable 9, mic 6, easy to drive from a phone 4 (3.5mm) or DSP/EQ app 6 (Type-C). As claimed by the store."),
    ("In-the-box weight", DEFAULT_W[2], "Eartips 4, eartip variety 3, case 4, cable 2, adapter 2. As claimed by the store. Few stores list box contents yet."),
    ("Sound scale: score that earns 0 pts", 40, "Adjusted Harman score at or below this gets 0 sound points."),
    ("Sound scale: score that earns full pts", 90, "Adjusted Harman score at or above this gets full sound points."),
]
for i, (a, b, c) in enumerate(spec, 2):
    ws.cell(i, 1, a).font = Font(name=F)
    cell = ws.cell(i, 2, b)
    cell.font = Font(name=F, color="0000FF")
    cell.fill = INPUT
    ws.cell(i, 3, c).font = Font(name=F)
ws.cell(7, 1, "Total of the three weights").font = Font(name=F, bold=True)
ws.cell(7, 2, "=B2+B3+B4").font = Font(name=F, bold=True)
ws.cell(7, 3, "Keep this at 100 so the total stays out of 100.").font = Font(name=F)
ws["B2"].comment = Comment("Default 60/30/10, agreed in the proposer/critic debate (debate/proposal_v2.md).", "IEM study")

for plug in ("Type-C", "3.5mm"):
    ws = wb.create_sheet(f"{plug} IEMs")
    header(ws, COLS)
    sub = sorted([r for r in rows if r["plug"] == plug and r["availability"] != "Discontinued"], key=lambda r: -r["_default"])
    last = len(sub) + 1
    for i, r in enumerate(sub, 2):
        f = {
            "=sound": f"={WS}!$B$2*MAX(0,MIN(1,({COL['lb']}{i}-{WS}!$B$5)/({WS}!$B$6-{WS}!$B$5)))",
            "=hw": f"={WS}!$B$3*{COL['hw_frac']}{i}",
            "=box": f"={WS}!$B$4*{COL['box_frac']}{i}",
            "=total": f"={COL['=sound']}{i}+{COL['=hw']}{i}+{COL['=box']}{i}",
            "=rank": f"=RANK({COL['=total']}{i},${COL['=total']}$2:${COL['=total']}${last})",
        }
        for c, (_, k, _) in enumerate(COLS, 1):
            v = f[k] if k.startswith("=") else r.get(k)
            if isinstance(v, bool):
                v = "Yes" if v else "No"
            elif isinstance(v, list):
                v = ", ".join(v)
            cell = ws.cell(i, c, v)
            cell.font = Font(name=F, bold=(k == "=total"))
            if k in ("=total", "=sound", "=hw", "=box"):
                cell.number_format = "0.0"
            if k in ("best_price", "mrp"):
                cell.number_format = "#,##0"
            if k == "best_url" and v:
                cell.hyperlink = v
                cell.font = Font(name=F, color="1F5FAF", underline="single")
        fill = WARN if r["ppi"] is None else (SOLD if r["availability"] != "In stock" else None)
        if fill:
            for c in range(1, len(COLS) + 1):
                ws.cell(i, c).fill = fill
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLS))}{last}"

# removed rows, kept for transparency
gone = [r for r in rows if r["availability"] == "Discontinued"]
ws = wb.create_sheet("Removed (discontinued)")
RC = [("IEM", "name", 34), ("Plug", "plug", 8), ("Why removed", "availability_why", 44), ("Harman score", "ppi", 10), ("Last price (₹)", "best_price", 11)]
header(ws, RC)
for i, r in enumerate(sorted(gone, key=lambda r: r["name"]), 2):
    for c, (_, k, _) in enumerate(RC, 1):
        ws.cell(i, c, r.get(k)).font = Font(name=F)

ws = wb.create_sheet("Notes & Sources")
notes = [
    "IEM India Master List: curated data set and score (stage 2)",
    f"Built {datetime.date.today():%d %b %Y}. Scope: new wired IEMs sold in India at or under ₹10,000. Type-C and 3.5mm listed and ranked separately.",
    "Stores: Headphone Zone, The Audio Store, Concept Kart (public product feeds and product pages, fetched slowly). Specs and box contents are as claimed on each store's product page.",
    "Excluded on purpose: Amazon (its terms forbid scraping) and HiFiNage (its robots.txt blocks AI crawlers). Every site's crawl rules were checked and respected.",
    "Best price = cheapest in-stock listing for that plug type across stores, or the cheapest listing if sold out everywhere.",
    "",
    "HOW THE SCORE WORKS (out of 100; weights editable on the Weights sheet)",
    "Sound (60): Harman in-ear predicted preference, Olive, Welti & Khonsaripour (AES 2017, papers 9840/9878), rescaled form:",
    "    Harman score = 100.08 − 8.5 × SD − 6.80 × |slope| − 3.48 × mean error   (error = measured response − Harman IE target)",
    "    Adjusted = Harman score − √(24.4 / number of measurers). 24.4 is how much different measurers disagree on the same IEM (pooled over 206 IEMs).",
    "    Collab editions where only the base model is measured: −5. No measurement at all ('Buyer beware', pink): set to the bottom-quarter value of measured IEMs (66.8).",
    "    Sound points = weight × (Adjusted − 40) / (90 − 40), capped between 0 and the full weight.",
    "Hardware & practicality (30) and In the box (10): taken from store listings AS CLAIMED BY THE STORE, not verified.",
    "    If a store does not mention an item, it gets the average rate for that item (so stores that write less don't sink their IEMs).",
    "Price is NOT in the score. 'Value' is a separate column: score percentile minus price percentile, among measured IEMs (in stock or sold out) in the top half by score.",
    "    Price barely predicts sound in this list (R² ≈ 0.01), so there is no fitted price curve; Value mostly means 'cheapest of the good half'.",
    "Comfort and fit are not scored: they depend on your ears, and stores rarely list nozzle size or weight.",
    "",
    "AVAILABILITY",
    "Removed: sold out everywhere AND a store clearance tag, or a newer version of the same model is in stock (see 'Removed (discontinued)').",
    "Kept but flagged (yellow): sold out everywhere with restocking signs ('back in stock' or pre-order tags, backorder, listed under 6 months ago), or status unclear.",
    "There is no stock history, so 'status unclear' items may in fact be discontinued.",
    "",
    "MEASUREMENTS",
    "Public squig.link databases on 711-type couplers, compiled by the open-source Squig-Rank project (github.com/PEQHUB/Squig-Rank). We recompute the score from SD / slope / mean error.",
    "Per IEM: median within each measurer's database, then median across measurers. 'Score spread' = max − min across measurers.",
    "Crinacle (graph.hangout.audio) measurements are excluded: his raw data is not public.",
    "Rigs, eartips and insertion depth all change results. Treat ±3 points as noise.",
    "Tilt / slope: negative = warmer (more bass, less treble) than the Harman target; positive = brighter.",
    "About 28% of listeners in later Harman research preferred about 2 dB less bass and 1–2 dB more treble than the target; if that is you, favour IEMs with a slightly positive tilt.",
    "Matching store names to measurements was done by Claude agents with rules: generations (Pro, X, 2, Plus) and tuned editions (collabs, DSP) are never merged.",
    "The scoring rules were argued out by two agents (a proposer and a critic) working only from this data; the full debate is in the project's debate/ folder.",
    "Raw curves are not redistributed; only derived numbers. Credit: every measurer listed in the Sources column.",
]
for i, t in enumerate(notes, 1):
    c = ws.cell(i, 1, t)
    c.font = Font(name=F, bold=(i == 1 or t.isupper()), size=12 if i == 1 else 10)
ws.column_dimensions["A"].width = 150
wb.save(OUT)
print("wrote", OUT)
