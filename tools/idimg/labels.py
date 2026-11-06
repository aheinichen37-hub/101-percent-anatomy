"""Find labels in an OpenStax figure and follow their leader lines.

Coordinates are pixels of render_figure(fig, scale) output.
"""
import functools
import json
import os
import pathlib
import re
from dataclasses import dataclass, field

import cv2
import numpy as np
import pytesseract
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
PDF_CANDIDATES = [
    os.environ.get("AP_PDF", ""),
    "/home/claude/figwork/ap.pdf",
    "/mnt/user-data/uploads/Claude/a&p open stax 1-100.pdf",
]


@dataclass
class Label:
    text: str
    box: tuple  # (x0, y0, x1, y1)
    lines: list = field(default_factory=list)  # [(text, (x0,y0,x1,y1)), ...]


@functools.lru_cache(maxsize=1)
def _pdf():
    import pdfplumber
    import pypdfium2 as pdfium
    path = next(p for p in PDF_CANDIDATES if p and os.path.exists(p))
    return pdfplumber.open(path), pdfium.PdfDocument(path)


@functools.lru_cache(maxsize=1)
def _caps():
    return json.load(open(HERE / "caps.json"))


@functools.lru_cache(maxsize=64)
def render_figure(fig: str, scale: float = 3.0) -> Image.Image:
    """Render the figure's image region (above its caption) from the PDF."""
    pl, doc = _pdf()
    pno = _caps()[fig]["page"] - 1
    page = pl.pages[pno]
    words = page.extract_words()
    cap = None
    for i, w in enumerate(words[:-1]):
        if w["text"] == "FIGURE" and re.fullmatch(re.escape(fig) + r"\D?", words[i + 1]["text"]):
            cap = w
            break
    imgs = [im for im in page.images if im["x1"] - im["x0"] > 20 and im["bottom"] - im["top"] > 20]
    above = sorted([im for im in imgs if cap is None or im["bottom"] <= cap["top"] + 4], key=lambda im: -im["bottom"])
    if not above:
        above = sorted(imgs, key=lambda im: abs(im["top"] - (cap["top"] if cap else 0)))[:1]
    sel, top = [above[0]], above[0]["top"]
    for im in above[1:]:
        if im["bottom"] >= top - 30:
            sel.append(im)
            top = min(top, im["top"])
    x0 = min(i["x0"] for i in sel) - 4
    x1 = max(i["x1"] for i in sel) + 4
    y0 = min(i["top"] for i in sel) - 4
    y1 = max(i["bottom"] for i in sel) + 4
    if cap is not None:
        y1 = min(y1, cap["top"] - 2)
    bmp = doc[pno].render(scale=scale).to_pil().convert("RGB")
    W, H = bmp.size
    return bmp.crop((max(0, int(x0 * scale)), max(0, int(y0 * scale)), min(W, int(x1 * scale)), min(H, int(y1 * scale))))


def find_labels(img: Image.Image) -> list:
    """OCR words -> lines -> multi-line labels (left-aligned, close together)."""
    d = pytesseract.image_to_data(img, config="--psm 11", output_type=pytesseract.Output.DICT)
    words = []
    for i, t in enumerate(d["text"]):
        if t.strip() and float(d["conf"][i]) >= 55:
            words.append(dict(t=t.strip(), x=d["left"][i], y=d["top"][i], w=d["width"][i], h=d["height"][i]))
    words.sort(key=lambda w: (w["y"], w["x"]))
    lines = []
    for w in words:
        for L in lines:
            if abs(L["y"] - w["y"]) < 0.6 * w["h"] and -2 <= w["x"] - L["x1"] < 1.3 * w["h"]:
                L["t"] += " " + w["t"]
                L["x1"] = w["x"] + w["w"]
                L["y1"] = max(L["y1"], w["y"] + w["h"])
                break
        else:
            lines.append(dict(t=w["t"], x=w["x"], y=w["y"], x1=w["x"] + w["w"], y1=w["y"] + w["h"], h=w["h"]))
    lines.sort(key=lambda L: (L["y"], L["x"]))
    labs = []
    for L in lines:
        for B in labs:
            last = B["lines"][-1]
            aligned = abs(B["x"] - L["x"]) <= 8 or abs(B["x1"] - L["x1"]) <= 8 or abs((B["x"] + B["x1"]) / 2 - (L["x"] + L["x1"]) / 2) <= 10
            # a continuation line starts lowercase or with "("; a capital starts a new, stacked label
            cont = L["t"][:1].islower() or L["t"][:1] == "("
            if aligned and cont and 0 <= L["y"] - last["y1"] < 1.6 * L["h"]:
                B["t"] += " " + L["t"]
                B["x"], B["x1"], B["y1"] = min(B["x"], L["x"]), max(B["x1"], L["x1"]), L["y1"]
                B["lines"].append(L)
                break
        else:
            labs.append(dict(t=L["t"], x=L["x"], y=L["y"], x1=L["x1"], y1=L["y1"], lines=[L]))
    # OCR reads stray line art as "\" or "|"; a real label has at least two letters
    labs = [B for B in labs if sum(c.isalpha() for c in B["t"]) >= 2]
    return [Label(B["t"], (B["x"], B["y"], B["x1"], B["y1"]),
                  [(L["t"], (L["x"], L["y"], L["x1"], L["y1"])) for L in B["lines"]]) for B in labs]


def _norm(s: str) -> str:
    s = s.lower().replace("ﬁ", "fi").replace("ﬂ", "fl")
    return re.sub(r"[^a-z0-9]", "", s)


def _lev(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _fold(s: str) -> str:
    """Collapse letters OCR commonly confuses (l/i/1, 0/o) so 'Uina' still matches 'Ulna'."""
    return s.translate(str.maketrans("i1|0", "lllo"))


def _keys(text: str) -> set:
    """Ways a label can name a structure: whole, before '(', without '(...)', or with '(alt)' swapped in."""
    keys = {text, re.split(r"\(", text)[0], re.sub(r"\([^)]*\)", " ", text)}
    m = re.match(r"(.*?)(\w+)\s*\(([^)]*)\)(.*)", text)
    if m:  # "Calcaneal (Achilles) tendon" -> "Achilles tendon"
        keys.add(m.group(1) + m.group(3) + m.group(4))
    return {_fold(_norm(k)) for k in keys if _norm(k)}


def match_label(labels: list, terms: list):
    """Label naming one of `terms`: exact first (after OCR folding), then a 1-typo match for terms longer than 6."""
    nterms = {_fold(_norm(t)) for t in terms if _norm(t)}
    exact = [L for L in labels if _keys(L.text) & nterms]
    pool = exact or [L for L in labels if any(len(t) > 6 and any(_lev(k, t) <= 1 for k in _keys(L.text)) for t in nterms)]
    if not pool:
        return None
    # deterministic: the label whose leader is longest wins later; here prefer leftmost-topmost
    return sorted(pool, key=lambda L: (L.box[1], L.box[0]))[0]


def _dark_mask(img: Image.Image, labels: list) -> np.ndarray:
    g = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2GRAY)
    dark = (g < 110).astype(np.uint8) * 255
    for L in labels:
        for _, (x0, y0, x1, y1) in L.lines:
            dark[max(0, y0 - 3):y1 + 3, max(0, x0 - 3):x1 + 3] = 0
    return dark


def leader_segments(img: Image.Image, labels: list, label: Label):
    """Straight leader segments that start next to `label`: [(ax,ay,bx,by)], a = label end."""
    dark = _dark_mask(img, labels)
    segs = cv2.HoughLinesP(dark, 1, np.pi / 360, threshold=35, minLineLength=35, maxLineGap=4)
    segs = [] if segs is None else np.asarray(segs).reshape(-1, 4)
    x0, y0, x1, y1 = label.box
    out = []
    for sx, sy, ex, ey in segs:
        for ax, ay, bx, by in ((sx, sy, ex, ey), (ex, ey, sx, sy)):
            dx = max(x0 - ax, 0, ax - x1)
            dy = max(y0 - ay, 0, ay - y1)
            if dx <= 45 and dy <= 14 and np.hypot(bx - ax, by - ay) > 35:
                # must point away from the label box
                if np.hypot(bx - (x0 + x1) / 2, by - (y0 + y1) / 2) > np.hypot(ax - (x0 + x1) / 2, ay - (y0 + y1) / 2):
                    out.append((int(ax), int(ay), int(bx), int(by)))
    return out


LINE_CONTRAST = 25  # a line pixel is this much darker than the pixels SIDE px to either side of it
SIDE = 4
WHITE_GAP = 6       # px a line may fade before it counts as ended, in white space
DRAWING_GAP = 14    # ... over the drawing, where it crosses outlines
BEND_MIN, BEND_MAX = 15, 85
MAX_BENDS = 2       # leaders bend in white space, rarely more than once


def _trace_gray(img: Image.Image, labels: list) -> np.ndarray:
    """Grayscale with label text blanked to white, so a trace never runs into another label's words."""
    g = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2GRAY).astype(np.float32)
    for L in labels:
        for _, (x0, y0, x1, y1) in L.lines:
            g[max(0, y0 - 3):y1 + 3, max(0, x0 - 3):x1 + 3] = 255
    return g


def _whiteness(img: Image.Image) -> np.ndarray:
    """Share of page-white pixels around each pixel (15 px box): ~1 in the margins, ~0 over the drawing."""
    white = (np.asarray(img.convert("RGB")).min(axis=2) >= 235).astype(np.float32)
    return cv2.blur(white, (15, 15))


def _linelike(g, x, y, ang) -> bool:
    H, W = g.shape
    c, s = np.cos(np.radians(ang)), np.sin(np.radians(ang))
    nx, ny = -s, c  # perpendicular

    def at(dx, dy):
        px, py = int(round(x + dx)), int(round(y + dy))
        return g[py, px] if 0 <= px < W and 0 <= py < H else 255.0
    center = min(at(k * nx, k * ny) for k in (-1, 0, 1))
    sides = (at(SIDE * nx, SIDE * ny) + at(-SIDE * nx, -SIDE * ny) + at((SIDE + 1) * nx, (SIDE + 1) * ny)
             + at(-(SIDE + 1) * nx, -(SIDE + 1) * ny)) / 4
    return center < 210 and sides - center >= LINE_CONTRAST


def _run_frac(g, x, y, ang, n=14) -> float:
    c, s = np.cos(np.radians(ang)), np.sin(np.radians(ang))
    return sum(_linelike(g, x + r * c, y + r * s, ang) for r in range(3, n + 1)) / (n - 2)


def _angle(x0, y0, x1, y1):
    return float(np.degrees(np.arctan2(y1 - y0, x1 - x0)))


def leader_path(img: Image.Image, labels: list, label: Label, dark=None, start=None, gray=None, white=None) -> list:
    """Polyline [(x,y), ...] of a leader from `label` to its far end.

    In white space a leader is a clean gray line and may bend; once over the drawing it only runs straight.
    A pixel counts as line if it is darker than the pixels a few px to either side, which works for faint
    gray over pale areas and for lines tinted by the color under them. `start` picks one of
    leader_segments() (default: the longest).
    """
    segs = leader_segments(img, labels, label)
    if not segs:
        return []
    ax, ay, bx, by = start or max(segs, key=lambda s: np.hypot(s[2] - s[0], s[3] - s[1]))
    g = _trace_gray(img, labels) if gray is None else gray
    wh = _whiteness(img) if white is None else white
    H, W = g.shape
    ang = _angle(ax, ay, bx, by)
    pts = [(ax, ay)]
    x, y = float(bx), float(by)
    last = (int(bx), int(by))
    inside, gap, bends = False, 0, 0
    for _ in range(4000):
        nx, ny = x + np.cos(np.radians(ang)), y + np.sin(np.radians(ang))
        if not (0 <= nx < W - 1 and 0 <= ny < H - 1):
            break
        if wh[int(ny), int(nx)] < 0.6:
            inside = True
        if _linelike(g, nx, ny, ang):
            x, y, gap = nx, ny, 0
            last = (int(round(x)), int(round(y)))
            continue
        if not inside and bends < MAX_BENDS and gap == 0:
            lx, ly = last
            options = [(d, _run_frac(g, lx, ly, ang + d)) for d in range(-BEND_MAX, BEND_MAX + 1, 5)
                       if abs(d) >= BEND_MIN]
            options = [o for o in options if o[1] >= 0.8]
            if options:
                d = min(options, key=lambda o: (abs(o[0]), -o[1]))[0]
                pts.append(last)
                ang += d
                bends += 1
                x, y = float(lx), float(ly)
                continue
        gap += 1
        x, y = nx, ny
        if gap > (DRAWING_GAP if inside else WHITE_GAP):
            break
    pts.append(last)
    return pts


def trace_leader(img: Image.Image, label: Label, labels: list = None):
    """Far end (x, y) of the label's leader line, following bends, or None if it has no leader."""
    labels = labels if labels is not None else find_labels(img)
    path = leader_path(img, labels, label)
    return path[-1] if path else None
