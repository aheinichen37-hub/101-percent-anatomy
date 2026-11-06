"""Review sheets for the identification pictures.

    python3 tools/idimg/sheets.py --decks ch11-abd,ch8-arm,ch19-anat     (or --all)

Writes, in tools/idimg/sheets/:
  <deck>.jpg      every card: pre-answer picture with its highlight, beside the after-answer picture
  fig-<n>.jpg     the figure on a coordinate grid with every label's traced tip marked and numbered, so a wrong
                  tip can be read off and corrected in tools/id-overrides.json ({"point": [x, y]})
"""
import argparse
import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.idimg.build import load_cards, id_decks, _figure  # noqa: E402
from tools.idimg.labels import trace_leader  # noqa: E402

OUT = ROOT / "tools" / "idimg" / "sheets"
TILE = 360


def _font(n):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, n)
        except OSError:
            pass
    return ImageFont.load_default()


def _thumb(img, w):
    return img.resize((w, max(1, round(img.height * w / img.width))))


def deck_sheet(deck, html=ROOT / "index.html", figs=ROOT / "figs" / "id", report=ROOT / "tools" / "idimg" / "report.json",
               outdir=OUT) -> pathlib.Path:
    figs, outdir = pathlib.Path(figs), pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    rep = json.loads(pathlib.Path(report).read_text()) if pathlib.Path(report).exists() else {}
    rows = []
    for c in load_cards(html, [deck]):
        r = rep.get(c.id, {})
        head = f"{c.id}  {c.answer}  [{r.get('status', '?')}{' ' + r['kind'] if r.get('kind') else ''}]  fig {c.fig}"
        if r.get("status") != "ok":
            head += f"  — {r.get('reason', '')}"
        q, m, a = (figs / f"{c.id}{s}" for s in ("-q.jpg", "-m.png", "-a.jpg"))
        if all(p.exists() for p in (q, m, a)):
            base = Image.open(q).convert("RGBA")
            hl = Image.open(m).convert("RGBA")
            hl.putalpha(hl.getchannel("A").point(lambda v: v * 6 // 10))
            pre = Image.alpha_composite(base, hl).convert("RGB")
            tiles = [_thumb(pre, TILE), _thumb(Image.open(a).convert("RGB"), TILE)]
        else:
            tiles = []
        rows.append((head, tiles))
    W = 2 * TILE + 30
    H = sum(28 + (max(t.height for t in ts) if ts else 0) + 14 for _, ts in rows) or 40
    sheet = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(sheet)
    y = 0
    for head, ts in rows:
        d.text((6, y + 6), head, fill=(0, 0, 0), font=_font(15))
        y += 28
        for i, t in enumerate(ts):
            sheet.paste(t, (6 + i * (TILE + 18), y))
        y += (max(t.height for t in ts) if ts else 0) + 14
        d.line([(0, y - 7), (W, y - 7)], fill=(200, 200, 200))
    out = outdir / f"{deck}.jpg"
    sheet.save(out, quality=82)
    return out


def figure_grid(fig, outdir=OUT) -> pathlib.Path:
    """The figure with a 50 px coordinate grid, every label numbered, and its traced tip drawn as a ring."""
    outdir = pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    img, labels, _ = _figure(fig)
    im = img.convert("RGB")
    d = ImageDraw.Draw(im)
    W, H = im.size
    small = _font(11)
    for x in range(0, W, 50):
        d.line([(x, 0), (x, H)], fill=(120, 190, 255) if x % 100 else (40, 110, 255), width=1)
        d.text((x + 2, 2), str(x), fill=(0, 0, 220), font=small)
    for y in range(0, H, 50):
        d.line([(0, y), (W, y)], fill=(120, 190, 255) if y % 100 else (40, 110, 255), width=1)
        d.text((2, y + 2), str(y), fill=(0, 0, 220), font=small)
    big = _font(16)
    for i, L in enumerate(labels, 1):
        x0, y0, x1, y1 = L.box
        d.text((x0 - 22, y0), str(i), fill=(220, 0, 160), font=big)
        tip = trace_leader(img, L, labels)
        if tip:
            tx, ty = tip
            d.ellipse([tx - 8, ty - 8, tx + 8, ty + 8], outline=(220, 0, 160), width=3)
            d.text((tx + 9, ty - 8), str(i), fill=(220, 0, 160), font=big)
    out = outdir / f"fig-{fig}.jpg"
    im.save(out, quality=85)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decks", default="")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    decks = id_decks(ROOT / "index.html") if a.all else [x for x in a.decks.split(",") if x]
    figs = set()
    for dk in decks:
        print(deck_sheet(dk))
        figs |= {c.fig for c in load_cards(ROOT / "index.html", [dk]) if c.fig and c.fig != "-"}
    for f in sorted(figs, key=lambda k: tuple(int(v) for v in k.split("."))):
        print(figure_grid(f))


if __name__ == "__main__":
    main()
