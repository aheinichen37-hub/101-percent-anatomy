"""Hand fixes for built identification pictures, v1.0.0 (3.8.3).

Reads tools/id-fixes.json, {card id: {"cover": [...], "spot": [x, y], "note": "..."}}, in before-answer
picture pixels. A cover is [x0,y0,x1,y1] (a white box) or {"poly": [[x,y], ...], "fill": "auto" | "#rrggbb"}
for slanted text on a coloured shape ("auto" takes the shape's own colour from under the polygon). It rebuilds that card's three files from the 3.8.2 originals:
    figs/id/<card>-q.jpg  original + white boxes over the listed text
    figs/id/<card>-m.png  the blue patch at "spot" (or where it was, if no spot is given)
    figs/id/<card>-a.jpg  the covered picture with the patch and the name plate, drawn by the build's own code
Starting from the originals every time makes the result repeatable: run it as often as you like.

Usage: python3 tools/idimg/patch_pics.py [--cards id,id] [--check]
"""
import argparse
import io
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from idimg import highlight  # noqa: E402

FIXES = os.path.join(TOOLS, "id-fixes.json")
ID = os.path.join(REPO, "figs", "id")
BASE = "5f2682eaf86dccbc5b554e488aa73ebf65796d0a"           # 3.8.2: the pictures as the v2.7-v3.0 builds left them
PAD = 2


def ensure_base():
    """A shallow clone may not hold the 3.8.2 commit; fetch just that commit when it is missing."""
    have = subprocess.run(["git", "-C", REPO, "cat-file", "-e", BASE + "^{commit}"], capture_output=True)
    if have.returncode:
        got = subprocess.run(["git", "-C", REPO, "fetch", "--depth=1", "origin", BASE + ":refs/patch-base"],
                             capture_output=True, text=True)
        if got.returncode:
            sys.exit(f"needs the 3.8.2 pictures from commit {BASE}; fetching it failed:\n{got.stderr}")


def original(cid, kind):
    ext = "png" if kind == "m" else "jpg"
    raw = subprocess.run(["git", "-C", REPO, "show", f"{BASE}:figs/id/{cid}-{kind}.{ext}"],
                         check=True, capture_output=True).stdout
    return Image.open(io.BytesIO(raw))


def built_kind(cid):
    """Keep the look the build gave the card (a ring for small targets), unless the fix says otherwise."""
    try:
        with open(os.path.join(HERE, "report.json"), encoding="utf-8") as f:
            k = json.load(f).get(cid, {}).get("kind")
    except OSError:
        return None
    return k if k in ("circle", "arrow") else None


def old_spot(m):
    a = np.array(m.convert("RGBA"))[..., 3]
    ys, xs = np.nonzero(a > 20)
    return (int(round(xs.mean())), int(round(ys.mean())))


def poly_fill(img, pts, fill):
    """The colour to paint a slanted cover: the light (non-text) pixels under it, by median."""
    if fill != "auto":
        return fill
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    px = np.array(img)[np.array(m) > 0]
    light = px[px.mean(axis=1) > 120]
    return tuple(int(v) for v in np.median(light if len(light) else px, axis=0))


def load():
    with open(FIXES, encoding="utf-8") as f:
        fixes = json.load(f)
    return {k: v for k, v in fixes.items() if not k.startswith("_")}


def patch(cid, fix, answer, out=ID):
    q = original(cid, "q").convert("RGB")
    d = ImageDraw.Draw(q)
    for c in fix.get("cover", []):
        if isinstance(c, dict):
            pts = [tuple(p) for p in c["poly"]]
            d.polygon(pts, fill=poly_fill(q, pts, c.get("fill", "auto")))
            continue
        x0, y0, x1, y1 = c
        d.rectangle((max(0, x0 - PAD), max(0, y0 - PAD), min(q.width - 1, x1 + PAD), min(q.height - 1, y1 + PAD)),
                    fill=(255, 255, 255))
    spot = tuple(fix["spot"]) if fix.get("spot") else old_spot(original(cid, "m"))
    mask, kind = highlight.make_mask(q, spot, force=fix.get("kind") or built_kind(cid))
    a = highlight.answer_image(q, mask, kind, answer, spot)
    q.save(os.path.join(out, f"{cid}-q.jpg"), quality=78, optimize=True)
    highlight.mask_png(mask).save(os.path.join(out, f"{cid}-m.png"), optimize=True)
    a.convert("RGB").save(os.path.join(out, f"{cid}-a.jpg"), quality=78, optimize=True)


def problems(fixes, names):
    out = []
    for cid, fix in fixes.items():
        if cid not in names:
            out.append(f"{cid}: not a card")
            continue
        if not os.path.exists(os.path.join(ID, f"{cid}-q.jpg")):
            out.append(f"{cid}: has no built picture")
            continue
        w, h = Image.open(os.path.join(ID, f"{cid}-q.jpg")).size
        for b in fix.get("cover", []):
            if isinstance(b, dict):
                if not all(0 <= x <= w and 0 <= y <= h for x, y in b.get("poly", [])) or len(b.get("poly", [])) < 3:
                    out.append(f"{cid}: cover shape {b} is not a polygon inside the {w}x{h} picture")
            elif not (len(b) == 4 and 0 <= b[0] < b[2] <= w and 0 <= b[1] < b[3] <= h):
                out.append(f"{cid}: cover box {b} is outside the {w}x{h} picture")
        s = fix.get("spot")
        if s and not (0 <= s[0] < w and 0 <= s[1] < h):
            out.append(f"{cid}: spot {s} is outside the {w}x{h} picture")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards")
    ap.add_argument("--check", action="store_true", help="only validate tools/id-fixes.json")
    a = ap.parse_args()
    names = {k: v["answer"] for k, v in
             json.load(open(os.path.join(TOOLS, "card-ids.json"), encoding="utf-8"))["cards"].items()}
    fixes = load()
    bad = problems(fixes, names)
    for b in bad:
        print("problem:", b)
    if bad or a.check:
        sys.exit(1 if bad else 0)
    ensure_base()
    todo = a.cards.split(",") if a.cards else list(fixes)
    todo = [c for c in todo if fixes[c].get("cover") or fixes[c].get("spot")]   # a note alone changes nothing
    for cid in todo:
        patch(cid, fixes[cid], names[cid])
    print(f"patched {len(todo)} cards")


if __name__ == "__main__":
    main()
