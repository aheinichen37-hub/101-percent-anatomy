"""Export a review batch for the review page (tools/review/page/index.html).

Writes tools/review/out/cards-<batch>.json: one entry per card with a small marked picture (data URI)
and the crop box, so a tap on the picture can be turned back into a point in figure coordinates.

Usage: python3 tools/review/export.py <batch> [--ids a,b,c | --hand]
  --hand   every card with a hand-placed point in tools/id-overrides.json that has built pictures (default)
"""
import argparse, base64, io, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from PIL import Image
from idimg import build, figures, labels as L, panel

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
WIDTH, QUALITY = 640, 60


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch")
    ap.add_argument("--ids")
    a = ap.parse_args()
    ov = build.load_overrides()
    cards = {c["card"]: c for c in build.read_cards()}
    if a.ids:
        ids = a.ids.split(",")
    else:
        ids = [k for k, v in ov.items() if v.get("point") and not v.get("skip")
               and os.path.exists(os.path.join(build.OUT_DIR, k + "-a.jpg"))]
    ids = sorted(i for i in ids if i in cards)
    figcache, out = {}, []
    for cid in ids:
        c, o = cards[cid], ov.get(cid, {})
        fig = o.get("fig") or c["fig"]
        if fig not in figcache:
            img = figures.render_figure(fig, scale=3.0)
            figcache[fig] = (img, L.find_labels(img))
        img, found = figcache[fig]
        pt = o.get("point")
        if pt is None:
            continue
        box = tuple(o["crop"]) if o.get("crop") else panel.panel_box(img, tuple(pt), found)
        if not o.get("crop"):
            bw, bh = box[2] - box[0], box[3] - box[1]
            if max(bw, bh) < build.MIN_LONG_SIDE or min(bw, bh) < build.MIN_SHORT_SIDE:
                box = build.window_box(img.size, tuple(pt))
        im = Image.open(os.path.join(build.OUT_DIR, cid + "-a.jpg")).convert("RGB")
        if im.width > WIDTH:
            im = im.resize((WIDTH, round(im.height * WIDTH / im.width)))
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=QUALITY, optimize=True)
        out.append({"id": cid, "deck": c["deck"], "name": c["name"], "fig": fig,
                    "box": [int(x) for x in box], "point": [int(pt[0]), int(pt[1])],
                    "img": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()})
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"cards-{a.batch}.json")
    json.dump({"batch": a.batch, "cards": out}, open(path, "w"), separators=(",", ":"))
    print(len(out), "cards,", round(os.path.getsize(path) / 1e6, 1), "MB ->", path)


main()
