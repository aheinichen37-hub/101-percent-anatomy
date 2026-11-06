"""Build the identification-card pictures: pre-answer (-q.jpg), highlight mask (-m.png), after-answer (-a.jpg).

    python3 tools/idimg/build.py --decks ch11-abd,ch8-arm,ch19-anat
    python3 tools/idimg/build.py --all
"""
import argparse
import functools
import json
import pathlib
import re
import sys
from dataclasses import dataclass

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.idimg.labels import render_figure, find_labels, match_label, trace_leader, Label, _caps  # noqa: E402
from tools.idimg.panel import panel_box, erase_labels, leader_pixels  # noqa: E402
from tools.idimg.highlight import make_mask, mask_png, answer_image  # noqa: E402

MAX_W = 1000   # px: pictures are scaled down to at most this wide
JPEG_Q = 78


@dataclass
class Card:
    id: str
    deck: str
    answer: str
    alts: list
    fig: str


DECK_RE = re.compile(r'D\("([^"]+)","(ch\d+)","[^"]*","[^"]*","([^"]*)",`(.*?)`\)', re.S)


def load_cards(html, decks) -> list:
    """Cards of the given decks, ids as the app makes them (`<deck>-<index>`), figure = card's own or deck's."""
    s = pathlib.Path(html).read_text()
    out = []
    for m in DECK_RE.finditer(s):
        did, _, deckfig, body = m.groups()
        if did not in decks:
            continue
        for i, ln in enumerate(body.strip().split("\n")):
            p = [x.strip() for x in ln.split("|")]
            fig = p[3] if len(p) > 3 and p[3] else deckfig
            alts = [a.strip() for a in p[1].split(";") if a.strip()] if len(p) > 1 else []
            out.append(Card(f"{did}-{i}", did, p[0], alts, fig))
    return out


def id_decks(html) -> list:
    m = re.search(r"const IDDECKS=new Set\((\[.*?\])\)", pathlib.Path(html).read_text(), re.S)
    return json.loads(m.group(1))


@functools.lru_cache(maxsize=4)
def _figure(fig):
    """Rendered figure, its labels, the erased version and the leader-line mask (shared by a figure's cards)."""
    img = render_figure(fig)
    labels = find_labels(img)
    lines = leader_pixels(img, labels)
    return img, labels, erase_labels(img, labels, lines)


LABEL_CACHE = ROOT / "tools" / "idimg" / "labels-cache.json"


def _chapter_labels(chapter: int) -> dict:
    """{fig: [label text, ...]} for every figure in a chapter, read once and cached on disk."""
    cache = json.loads(LABEL_CACHE.read_text()) if LABEL_CACHE.exists() else {}
    figs = [f for f in _caps() if int(f.split(".")[0]) == chapter]
    missing = [f for f in figs if f not in cache]
    for f in missing:
        try:
            cache[f] = [L.text for L in find_labels(render_figure(f))]
        except Exception:
            cache[f] = []
    if missing:
        LABEL_CACHE.write_text(json.dumps(cache, indent=0, sort_keys=True))
    return {f: cache[f] for f in sorted(figs, key=lambda k: int(k.split(".")[1]))}


def candidate_figures(card: Card, terms: list) -> list:
    """The card's own figure first, then every other figure in its chapter that labels the structure."""
    own = [card.fig] if card.fig and card.fig != "-" else []
    chapter = int(card.deck.split("-")[0][2:])
    labelled = [f for f, texts in _chapter_labels(chapter).items()
                if f not in own and match_label([Label(t, (0, 0, 0, 0)) for t in texts], terms) is not None]
    return own + labelled


def _fit(img):
    if img.width <= MAX_W:
        return img
    return img.resize((MAX_W, round(img.height * MAX_W / img.width)))


def build_card(card: Card, ov: dict, outdir: pathlib.Path, fullfigs: pathlib.Path = None) -> dict:
    rep = {"fig": card.fig, "answer": card.answer}
    if ov.get("skip"):
        return {**rep, "status": "skip", "reason": "override"}
    terms = [ov["label"]] if "label" in ov else [card.answer] + card.alts
    figs = [ov["fig"]] if "fig" in ov else candidate_figures(card, terms)
    if not figs:
        return {**rep, "status": "fail", "reason": "no figure labels it"}
    why = "label not found"
    for fig in figs:
        img, labels, clean = _figure(fig)
        if "point" in ov:
            pt = tuple(ov["point"])
        else:
            lab = match_label(labels, terms)
            if lab is None:
                continue
            pt = trace_leader(img, lab, labels)
            if pt is None:
                why = "no leader line"
                continue
        break
    else:
        return {**rep, "status": "fail", "reason": why, "tried": figs}
    box = tuple(ov["crop"]) if "crop" in ov else panel_box(img, pt, labels)
    panel = clean.crop(box)
    local = (pt[0] - box[0], pt[1] - box[1])
    mask, kind = make_mask(panel, local, force=ov.get("kind"))
    after = answer_image(panel, mask, kind, card.answer)
    q, m, a = _fit(panel.convert("RGB")), _fit(mask_png(mask)), _fit(after.convert("RGB"))
    q.save(outdir / f"{card.id}-q.jpg", quality=JPEG_Q, optimize=True, progressive=True)
    m.save(outdir / f"{card.id}-m.png", optimize=True)
    a.save(outdir / f"{card.id}-a.jpg", quality=JPEG_Q, optimize=True, progressive=True)
    if fullfigs is not None and not (fullfigs / f"{fig}.jpg").exists():  # tap-to-enlarge needs the whole figure
        full = img.convert("RGB")
        if full.width > 1400:
            full = full.resize((1400, round(full.height * 1400 / full.width)))
        full.save(fullfigs / f"{fig}.jpg", quality=80, optimize=True, progressive=True)
    return {**rep, "fig": fig, "status": "ok", "kind": kind, "point": [int(pt[0]), int(pt[1])],
            "crop": [int(v) for v in box]}


SHARED_IOU = 0.5  # two structures' highlights overlapping this much are really one highlight


def _shared_highlights(rep, outdir, scope) -> list:
    """Pairs of card ids (in `scope`) whose fill/outline highlights in the same figure overlap >= SHARED_IOU."""
    from PIL import Image
    import numpy as np
    by_fig = {}
    for cid in scope:
        r = rep.get(cid, {})
        if r.get("status") == "ok" and r.get("kind") in ("fill", "outline"):
            by_fig.setdefault(r["fig"], []).append(cid)
    pairs = []
    for fig, ids in by_fig.items():
        masks = {}
        for cid in ids:
            x0, y0, x1, y1 = rep[cid]["crop"]
            m = np.asarray(Image.open(pathlib.Path(outdir) / f"{cid}-m.png").resize((x1 - x0, y1 - y0)))[..., 3] > 127
            ys, xs = np.nonzero(m)
            xs, ys = xs + x0, ys + y0  # figure coordinates
            keep = (xs % 3 == 0) & (ys % 3 == 0)  # sample on a fixed grid so different masks line up
            masks[cid] = set(zip(xs[keep].tolist(), ys[keep].tolist()))
        ids = sorted(ids)
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                if rep[a]["answer"] == rep[b]["answer"]:
                    continue
                inter = len(masks[a] & masks[b])
                if inter / max(len(masks[a] | masks[b]), 1) >= SHARED_IOU:
                    pairs.append((a, b))
    return pairs


def write_idimg(html, ids: dict):
    """Rewrite the app's `const IDIMG=new Map([...])` with {card id: figure the pictures came from}."""
    p = pathlib.Path(html)
    s = p.read_text()
    new = "const IDIMG=new Map(" + json.dumps(sorted(ids.items())) + ");"
    s, n = re.subn(r"const IDIMG=new Map\(\[.*?\]\);", lambda _: new, s, count=1, flags=re.S)
    assert n == 1, "IDIMG declaration not found"
    p.write_text(s)


def build(decks, html=ROOT / "index.html", outdir=ROOT / "figs" / "id", overrides=ROOT / "tools" / "id-overrides.json",
          report=ROOT / "tools" / "idimg" / "report.json", only=None, fullfigs=ROOT / "figs") -> dict:
    outdir = pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    ovs = json.loads(pathlib.Path(overrides).read_text()) if pathlib.Path(overrides).exists() else {}
    rp = pathlib.Path(report)
    rep = json.loads(rp.read_text()) if rp.exists() else {}
    for card in load_cards(html, decks):
        if only and card.id not in only:
            continue
        for suffix in ("-q.jpg", "-m.png", "-a.jpg"):  # never leave a stale picture behind
            (outdir / f"{card.id}{suffix}").unlink(missing_ok=True)
        try:
            rep[card.id] = build_card(card, ovs.get(card.id, {}), outdir, pathlib.Path(fullfigs))
        except Exception as e:  # one broken figure must not stop the build
            rep[card.id] = {"fig": card.fig, "answer": card.answer, "status": "fail", "reason": repr(e)[:200]}
    # Same-colored neighbors (muscles drawn in one salmon tone) can make two different structures' fills identical.
    # A highlight must belong to one structure: overlapping fills both fall back to a circle on their own point.
    cards = {c.id: c for c in load_cards(html, decks)}
    for a, b in _shared_highlights(rep, outdir, set(cards)):
        for cid in (a, b):
            if rep[cid].get("kind") in ("fill", "outline") and "kind" not in ovs.get(cid, {}):
                rep[cid] = build_card(cards[cid], {**ovs.get(cid, {}), "kind": "circle"}, outdir, pathlib.Path(fullfigs))
                rep[cid]["reason"] = "shared highlight with " + (b if cid == a else a)
    rp.write_text(json.dumps(rep, indent=1, sort_keys=True))
    ok = {cid: rep[cid]["fig"] for cid in rep if rep[cid]["status"] == "ok"
          and all((outdir / f"{cid}{s}").exists() for s in ("-q.jpg", "-m.png", "-a.jpg"))}
    write_idimg(html, ok)
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decks", default="")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    decks = id_decks(ROOT / "index.html") if a.all else [d for d in a.decks.split(",") if d]
    rep = build(decks)
    mine = {k: v for k, v in rep.items() if any(k.startswith(d + "-") for d in decks)}
    from collections import Counter
    print(Counter(v["status"] for v in mine.values()), Counter(v.get("kind") for v in mine.values() if v.get("kind")))


if __name__ == "__main__":
    main()
