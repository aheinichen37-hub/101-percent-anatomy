"""Contact sheets, so a whole deck's pictures can be checked at a glance."""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from idimg import figures, highlight  # noqa: E402

REPO = figures.REPO
ID_DIR = os.path.join(REPO, "figs", "id")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sheets")
REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.json")

THUMB = 300
COLS = 4
CAPTION = 18


def _tile(card_id, kind):
    q = os.path.join(ID_DIR, card_id + "-q.jpg")
    m = os.path.join(ID_DIR, card_id + "-m.png")
    if not os.path.exists(q):
        return None
    base = Image.open(q).convert("RGBA")
    if os.path.exists(m):
        overlay = Image.open(m).convert("RGBA")
        alpha = overlay.getchannel("A").point(lambda v: int(v * 0.20))
        overlay.putalpha(alpha)
        base = Image.alpha_composite(base, overlay)
    base = base.convert("RGB")
    base.thumbnail((THUMB, THUMB))
    tile = Image.new("RGB", (THUMB, THUMB + CAPTION), "white")
    tile.paste(base, ((THUMB - base.width) // 2, (THUMB - base.height) // 2))
    ImageDraw.Draw(tile).text((2, THUMB + 2), f"{card_id}  {kind or ''}", fill=(20, 20, 20))
    return tile


def sheet_for(deck, rows):
    cards = [(cid, r.get("kind")) for cid, r in sorted(rows.items())
             if r.get("deck") == deck and r.get("status") == "ok"]
    tiles = [t for t in (_tile(cid, kind) for cid, kind in cards) if t]
    if not tiles:
        return None
    cols = min(COLS, len(tiles))
    rows_n = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * THUMB, rows_n * (THUMB + CAPTION)), "white")
    for i, tile in enumerate(tiles):
        sheet.paste(tile, ((i % cols) * THUMB, (i // cols) * (THUMB + CAPTION)))
    return sheet


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--decks", help="comma-separated deck ids")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args(argv)

    rows = json.load(open(REPORT))
    decks = (args.decks.split(",") if args.decks
             else sorted({r["deck"] for r in rows.values()}))
    os.makedirs(OUT_DIR, exist_ok=True)
    for deck in decks:
        sheet = sheet_for(deck, rows)
        if sheet is None:
            print("no pictures for", deck)
            continue
        path = os.path.join(OUT_DIR, deck + ".jpg")
        sheet.save(path, quality=82, optimize=True)
        print("wrote", path, sheet.size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
