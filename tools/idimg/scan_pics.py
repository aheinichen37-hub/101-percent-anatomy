"""Scan the built identification pictures for the two faults Andrew found on his phone, v1.0.0.

1. Label leaks: text still readable in the before-answer picture (figs/id/<card>-q.jpg).
   "answer" = the card's own answer shows (a giveaway); "label" = some other label shows
   (a giveaway for a sibling card, e.g. "Pterion" on the skull pictures).
2. Misplaced highlights: the blue spot (figs/id/<card>-m.png) sits on the picture's rim, where a
   leader line meets its label, or mostly over blank paper rather than drawing.

Usage: python3 tools/idimg/scan_pics.py [--sheet] [--cards id,id]
Writes tools/idimg/scan-report.json; --sheet also writes contact sheets of flagged cards to
tools/review/out/ for checking by eye. 3D renders (tools/anat3d/report3d.json) are skipped.
"""
import argparse
import json
import os
import re
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pytesseract
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
ID = os.path.join(REPO, "figs", "id")
OUT = os.path.join(HERE, "scan-report.json")
SHEETS = os.path.join(REPO, "tools", "review", "out")
MIN_CONF = 60
EDGE_FRAC = 0.07      # spot centre within 7% of the shorter side from the rim
PAPER_FRAC = 0.55     # more than this share of the spot over near-white paper


def norm(s):  # noqa: E302
    return re.sub(r"[^a-z]", "", s.lower())


def close(a, b):
    if a == b:
        return True
    if min(len(a), len(b)) < 4:
        return False
    if a in b or b in a:
        return True
    # one slip per 5 letters, as OCR misreads
    m, n = len(a), len(b)
    if abs(m - n) > 2:
        return False
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i]
        for j in range(1, n + 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] != b[j - 1])))
        prev = cur
    return prev[-1] <= max(1, len(a) // 5)


def words(img):
    """Labels are small in these crops, so read the picture 4x larger at two contrast cut-offs."""
    g = img.convert("L")
    big = g.resize((g.width * 4, g.height * 4), Image.LANCZOS)
    out = []
    for th in (160, 120):
        d = pytesseract.image_to_data(big.point(lambda v: 255 if v > th else 0), config="--psm 11",
                                      output_type=pytesseract.Output.DICT)
        for i, t in enumerate(d["text"]):
            t = (t or "").strip()
            try:
                conf = float(d["conf"][i])
            except (TypeError, ValueError):
                continue
            if conf < MIN_CONF or len(norm(t)) < 3:
                continue
            box = [d["left"][i] // 4, d["top"][i] // 4,
                   (d["left"][i] + d["width"][i]) // 4, (d["top"][i] + d["height"][i]) // 4]
            if not any(norm(o[0]) == norm(t) and abs(o[1][0] - box[0]) < 6 and abs(o[1][1] - box[1]) < 6 for o in out):
                out.append([t, box])
    return out


def scan(args):
    cid, answer = args
    q = Image.open(os.path.join(ID, f"{cid}-q.jpg")).convert("RGB")
    m = np.array(Image.open(os.path.join(ID, f"{cid}-m.png")).convert("RGBA"))[..., 3]
    faults = []

    ans = [norm(w) for w in answer.split() if len(norm(w)) >= 4] or [norm(answer)]
    for t, box in words(q):
        n = norm(t)
        if any(close(n, a) for a in ans):
            faults.append({"kind": "answer", "text": t, "box": box})
        elif len(n) >= 4 and n.isalpha():
            faults.append({"kind": "label", "text": t, "box": box})

    ys, xs = np.nonzero(m > 20)
    if len(xs):
        cx, cy = float(xs.mean()), float(ys.mean())
        h, w = m.shape
        edge = min(cx, cy, w - cx, h - cy)
        if edge < EDGE_FRAC * min(w, h):
            faults.append({"kind": "rim", "at": [round(cx), round(cy)]})
        g = np.array(q.convert("L"))[ys, xs]
        paper = float((g > 238).mean())
        if paper > PAPER_FRAC:
            faults.append({"kind": "paper", "at": [round(cx), round(cy)], "share": round(paper, 2)})
    return cid, answer, faults


def sheet(rows, name):
    tiles = []
    for cid, answer, faults in rows:
        q = Image.open(os.path.join(ID, f"{cid}-q.jpg")).convert("RGB")
        m = Image.open(os.path.join(ID, f"{cid}-m.png")).convert("RGBA")
        q.paste(m, (0, 0), m)
        q.thumbnail((360, 360))
        t = Image.new("RGB", (380, 420), "white")
        t.paste(q, (10, 10))
        d = ImageDraw.Draw(t)
        d.text((10, 375), f"{cid}  {answer}", fill="black")
        d.text((10, 392), ", ".join(sorted({f['kind'] for f in faults}))[:60], fill="red")
        tiles.append(t)
    for k in range(0, len(tiles), 20):
        page = Image.new("RGB", (380 * 5, 420 * 4), "white")
        for i, t in enumerate(tiles[k:k + 20]):
            page.paste(t, ((i % 5) * 380, (i // 5) * 420))
        os.makedirs(SHEETS, exist_ok=True)
        page.save(os.path.join(SHEETS, f"{name}-{k // 20 + 1}.jpg"), quality=80)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", action="store_true")
    ap.add_argument("--cards")
    a = ap.parse_args()
    ids = json.load(open(os.path.join(REPO, "tools", "card-ids.json"), encoding="utf-8"))["cards"]
    three_d = set(json.load(open(os.path.join(REPO, "tools", "anat3d", "report3d.json"), encoding="utf-8")))
    built = sorted({f[:-6] for f in os.listdir(ID) if f.endswith("-q.jpg")})
    if a.cards:
        built = [c for c in built if c in a.cards.split(",")]
    todo = [(c, ids[c]["answer"]) for c in built if c in ids and c not in three_d]
    with ProcessPoolExecutor() as ex:
        rows = list(ex.map(scan, todo))
    flagged = [r for r in rows if r[2]]
    rep = {c: {"answer": ans, "faults": f} for c, ans, f in flagged}
    json.dump(rep, open(OUT, "w"), indent=1)
    count = lambda k: sum(any(f["kind"] == k for f in fs) for _, _, fs in flagged)
    print(f"{len(todo)} textbook pictures scanned ({len(built) - len(todo)} 3D renders skipped)")
    for k in ("answer", "label", "rim", "paper"):
        print(f"  {k:7s}{count(k)}")
    if a.sheet:
        for k in ("answer", "label", "rim", "paper"):
            sheet([r for r in flagged if any(f["kind"] == k for f in r[2])], f"scan-{k}")
        print("contact sheets in", os.path.relpath(SHEETS, REPO))


if __name__ == "__main__":
    main()
