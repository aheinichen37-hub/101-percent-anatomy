"""Build the identification pictures and register them in the app.

Per card: find its textbook figure in the PDF, read the labels, follow the card answer's
leader line to the structure, crop to that drawing, cover the label text, and write
    figs/id/<card-id>-q.jpg   the picture shown before answering
    figs/id/<card-id>-m.png   the highlight, laid over it by the app
    figs/id/<card-id>-a.jpg   the same picture with the structure named

Usage:
    python3 tools/idimg/build.py --decks ch11-abd,ch8-arm,ch19-anat
    python3 tools/idimg/build.py --all
"""
import argparse
import json
import os
import re
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from idimg import figures, highlight, labels as labels_mod, panel  # noqa: E402

REPO = figures.REPO
INDEX = os.path.join(REPO, "index.html")
OUT_DIR = os.path.join(REPO, "figs", "id")
OVERRIDES = os.path.join(REPO, "tools", "id-overrides.json")
REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.json")

MAX_WIDTH = 1000
JPEG_QUALITY = 78

# Quality gates. A card that fails one keeps no picture and falls back to the clue,
# which is better than a card showing a scrap of a drawing or a patch hanging off its
# edge. Reviewing hundreds of pictures by eye is not realistic, so the build throws out
# what it cannot vouch for.
# A long bone is a legitimately narrow strip, so the test is on the drawing's longest
# side and its area, not on its narrowest side.
MIN_LONG_SIDE = 280
MIN_SHORT_SIDE = 90
MIN_AREA = 60000
EDGE_MARGIN = 30         # the marked spot must sit inside the crop, not on its rim
MIN_INK_FRACTION = 0.06  # a crop that is nearly all paper is not a drawing


def load_overrides():
    try:
        with open(OVERRIDES) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def read_cards(deck_ids=None, page=None):
    """Card data straight from the app, so the build and the app always agree.

    Parsing index.html with a regex would be a second, drifting copy of the card format;
    the page already has a parser, so this runs it. Pass `page` to reuse a browser that
    is already open — a second sync Playwright cannot start inside the first.
    """
    from playwright.sync_api import sync_playwright
    script = """() => {
        const out = [];
        for (const id of IDDECKS) {
            const d = DECKS[id];
            if (!d) continue;
            for (const it of d.items) {
                out.push({card: it.id, deck: id, name: it.name,
                          accept: it.accept, fig: it.fig});
            }
        }
        return out;
    }"""
    if page is not None:
        cards = page.evaluate(script)
    else:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            pg = browser.new_page()
            pg.goto("file://" + INDEX)
            pg.wait_for_timeout(200)
            cards = pg.evaluate(script)
            browser.close()
    if deck_ids:
        wanted = set(deck_ids)
        cards = [c for c in cards if c["deck"] in wanted]
    return cards


def _usable_figure(fig):
    return bool(fig) and fig != "-" and os.path.exists(figures.fig_path(fig))


def window_box(size, point, frac=0.55):
    """A square window around a hand-placed spot, for when the drawing's own outline is
    too small to crop to (thin muscles, labels on the rim). Only used for hand-set spots,
    because there the spot is known to be on the structure."""
    w, h = size
    half = int(min(w, h) * frac / 2)
    x, y = point
    x0 = max(0, min(w - 2 * half, x - half))
    y0 = max(0, min(h - 2 * half, y - half))
    return (x0, y0, min(w, x0 + 2 * half), min(h, y0 + 2 * half))


def build_card(card, override=None):
    """Make one card's three files. Returns a report row."""
    override = override or {}
    row = {"deck": card["deck"], "fig": card.get("fig"), "kind": None,
           "status": "fail", "reason": ""}

    if override.get("skip"):
        row.update(status="skip", reason="skipped by override")
        return row
    if override.get("fig"):                 # a card can borrow a better drawing
        card = dict(card, fig=override["fig"])
        row["fig"] = card["fig"]
    if not _usable_figure(card.get("fig")):
        row.update(status="skip", reason="card has no textbook figure")
        return row

    try:
        img = figures.render_figure(card["fig"], scale=3.0)
    except (KeyError, ValueError):
        # 24 figures have no caption the text layer exposes, and a few never match
        # confidently. The crop the app already ships is the same framing at lower
        # resolution, which is still worth trying rather than dropping the card.
        img = figures.stored_figure(card["fig"])
    found = labels_mod.find_labels(img)

    point = override.get("point")
    if point is None:
        terms = [card["name"]] + list(card.get("accept") or [])
        if override.get("label"):
            terms.insert(0, override["label"])
        lab = labels_mod.match_label(found, terms)
        if lab is None:
            row.update(status="fail", reason="no label matched the answer")
            return row
        point = labels_mod.trace_leader(img, lab, found)
        if point is None:
            row.update(status="fail", reason="leader line not found")
            return row
    point = (int(point[0]), int(point[1]))

    hand = bool(override.get("point") or override.get("crop"))   # placed by eye: trusted
    box = tuple(override["crop"]) if override.get("crop") else panel.panel_box(img, point, found)
    if hand and not override.get("crop"):
        bw, bh = box[2] - box[0], box[3] - box[1]
        if max(bw, bh) < MIN_LONG_SIDE or min(bw, bh) < MIN_SHORT_SIDE:
            box = window_box(img.size, point)
    covered = labels_mod.cover_labels(img, found)
    pan = panel.crop(covered, box)
    local = (point[0] - box[0], point[1] - box[1])
    if not (0 <= local[0] < pan.width and 0 <= local[1] < pan.height):
        row.update(status="fail", reason="structure fell outside the crop")
        return row

    if not hand:                          # a hand-set spot or crop is trusted as given
        if (max(pan.width, pan.height) < MIN_LONG_SIDE
                or min(pan.width, pan.height) < MIN_SHORT_SIDE
                or pan.width * pan.height < MIN_AREA):
            row.update(status="fail", reason=f"crop is only {pan.width}x{pan.height}")
            return row
        if (local[0] < EDGE_MARGIN or local[1] < EDGE_MARGIN
                or pan.width - local[0] < EDGE_MARGIN
                or pan.height - local[1] < EDGE_MARGIN):
            row.update(status="fail", reason="structure sits on the edge of the crop")
            return row
        import numpy as _np
        ink = (_np.array(pan.convert("L")) < 245).mean()
        if ink < MIN_INK_FRACTION:
            row.update(status="fail", reason=f"crop is mostly blank ({ink:.0%} drawing)")
            return row

    mask, kind = highlight.make_mask(pan, local, force=override.get("kind"))
    answer = highlight.answer_image(pan, mask, kind, card["name"], local)

    if pan.width > MAX_WIDTH:                 # keep the download small
        ratio = MAX_WIDTH / pan.width
        size = (MAX_WIDTH, max(1, int(pan.height * ratio)))
        pan = pan.resize(size)
        mask = mask.resize(size)
        answer = answer.resize(size)

    os.makedirs(OUT_DIR, exist_ok=True)
    base = os.path.join(OUT_DIR, card["card"])
    pan.convert("RGB").save(base + "-q.jpg", quality=JPEG_QUALITY, optimize=True)
    highlight.mask_png(mask).save(base + "-m.png", optimize=True)
    answer.convert("RGB").save(base + "-a.jpg", quality=JPEG_QUALITY, optimize=True)

    row.update(status="ok", kind=kind, reason="")
    return row


def set_idimg(html, card_ids):
    """The page source with its IDIMG set replaced by `card_ids`."""
    ids = ",".join(json.dumps(c) for c in sorted(card_ids))
    new = f"const IDIMG=new Set([{ids}]);"
    out, n = re.subn(r"const IDIMG=new Set\(\[[^\]]*\]\);", new, html, count=1)
    if n != 1:
        raise RuntimeError("could not find the IDIMG set in index.html")
    return out


def write_idimg(card_ids):
    """Register the built cards in the app's IDIMG set."""
    with open(INDEX) as fh:
        html = fh.read()
    with open(INDEX, "w") as fh:
        fh.write(set_idimg(html, card_ids))
    return len(card_ids)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--decks", help="comma-separated deck ids")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--cards", help="comma-separated card ids, or 'overrides' for every card with a hand fix")
    ap.add_argument("--limit", type=int, help="stop after this many cards (for a trial run)")
    ap.add_argument("--no-register", action="store_true",
                    help="write the pictures but leave index.html alone")
    args = ap.parse_args(argv)
    if not args.decks and not args.all:
        ap.error("pass --decks or --all")

    deck_ids = args.decks.split(",") if args.decks else None
    overrides = load_overrides()
    cards = read_cards(deck_ids)
    if args.cards:
        want = set(overrides) if args.cards == "overrides" else set(args.cards.split(","))
        cards = [c for c in cards if c["card"] in want]
    if args.limit:
        cards = cards[:args.limit]
    print(f"{len(cards)} cards", flush=True)

    report = {}
    try:
        report = json.load(open(REPORT))
    except (OSError, ValueError):
        pass

    ok = 0
    for i, card in enumerate(cards, 1):
        try:
            row = build_card(card, overrides.get(card["card"]))
        except Exception as exc:                     # one bad card must not stop the run
            row = {"deck": card["deck"], "fig": card.get("fig"), "kind": None,
                   "status": "fail", "reason": f"{type(exc).__name__}: {exc}"}
            if os.environ.get("IDIMG_TRACE"):
                traceback.print_exc()
        report[card["card"]] = row
        ok += row["status"] == "ok"
        if i % 25 == 0 or i == len(cards):
            print(f"  {i}/{len(cards)} built, {ok} with pictures", flush=True)

    with open(REPORT, "w") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)

    built = sorted(cid for cid, r in report.items() if r["status"] == "ok")
    if not args.no_register:
        write_idimg(built)
    fails = [(c, r["reason"]) for c, r in report.items() if r["status"] == "fail"]
    print(f"done: {ok}/{len(cards)} this run; {len(built)} registered in total; "
          f"{len(fails)} failed")
    for cid, why in fails[:12]:
        print("  fail", cid, "-", why)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
