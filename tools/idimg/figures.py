"""Find a textbook figure in the OpenStax PDF and re-render it at higher resolution.

The app ships each figure as a JPEG under figs/, cropped from the PDF during the v2.4
build at render scale 2.4. Text recognition needs more pixels than that, so the build
re-renders from the PDF — which means knowing each figure's page and region again.

The captions give the page, but not reliably: the extracted text layer puts
"Figure 11.16" on page 443 while the drawing is on 444. So the caption index is only a
hint. The region is settled by matching the stored crop against the rendered page, which
reproduces the v2.4 framing exactly instead of re-deriving the heuristic that made it.
"""
import json
import os
from dataclasses import dataclass

import cv2
import numpy as np
import pypdfium2 as pdfium
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
FIGS = os.path.join(REPO, "figs")
CAPS_PATH = os.path.join(HERE, "caps.json")
CACHE_PATH = os.path.join(HERE, "boxes.json")

PDF_PATH = os.environ.get(
    "ANATOMY_PDF", "/mnt/user-data/uploads/Claude/a&p open stax 1-100.pdf")

# Matching at the same scale the comparison is made at keeps correlation high:
# downscaling the stored JPEG to probe more cheaply cost ~0.2 of the match score.
PROBE_SCALE = 3.0
PAGE_WINDOW = 3            # captions can sit a page off from the drawing
MIN_SCORE = 0.90           # below this the figure counts as unresolved
RATIOS = np.arange(1.10, 1.41, 0.025)   # stored crop is scale 2.4; 3.0/2.4 = 1.25


@dataclass(frozen=True)
class Loc:
    """Where a figure lives: page index and region in PDF points."""
    page: int
    box: tuple          # (x0, y0, x1, y1) in points
    score: float
    scale: float        # render scale the stored crop was made at


def pdf_available():
    return os.path.exists(PDF_PATH)


def fig_path(fig):
    return os.path.join(FIGS, f"{fig}.jpg")


_doc = None


def _doc_handle():
    global _doc
    if _doc is None:
        if not pdf_available():
            raise FileNotFoundError(f"source PDF not found at {PDF_PATH}")
        _doc = pdfium.PdfDocument(PDF_PATH)
    return _doc


def _caps():
    if not hasattr(_caps, "data"):
        _caps.data = json.load(open(CAPS_PATH))
    return _caps.data


def _cache():
    if not hasattr(_cache, "data"):
        try:
            _cache.data = json.load(open(CACHE_PATH))
        except (OSError, ValueError):
            _cache.data = {}
    return _cache.data


def _save_cache():
    tmp = CACHE_PATH + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(_cache.data, fh, indent=0, sort_keys=True)
    os.replace(tmp, CACHE_PATH)


def render_page(page_no, scale):
    page = _doc_handle()[page_no]
    try:
        return page.render(scale=scale).to_pil()
    finally:
        page.close()


def candidate_pages(fig):
    caps = _caps()
    if fig not in caps:
        raise KeyError(f"no page recorded for figure {fig}")
    pages = set()
    for p in caps[fig]:
        pages.update(range(max(0, p - PAGE_WINDOW), p + PAGE_WINDOW + 1))
    return sorted(pages)


def resolve(fig, force=False):
    """Locate `fig` in the PDF. Cached, so a rebuild doesn't re-search."""
    cache = _cache()
    if not force and fig in cache:
        c = cache[fig]
        return Loc(c["page"], tuple(c["box"]), c["score"], c["scale"])

    path = fig_path(fig)
    if not os.path.exists(path):
        raise KeyError(f"no stored crop for figure {fig}")
    pages = candidate_pages(fig)          # raises KeyError for an unknown figure

    tpl0 = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    best = None
    for pno in pages:
        big = np.array(render_page(pno, PROBE_SCALE).convert("L"))
        for r in RATIOS:
            w, h = int(tpl0.shape[1] * r), int(tpl0.shape[0] * r)
            if w < 40 or h < 40 or h > big.shape[0] or w > big.shape[1]:
                continue
            tpl = cv2.resize(tpl0, (w, h), interpolation=cv2.INTER_AREA)
            _, mx, _, loc = cv2.minMaxLoc(cv2.matchTemplate(big, tpl, cv2.TM_CCOEFF_NORMED))
            if best is None or mx > best[0]:
                best = (float(mx), pno, float(r), loc, (w, h))

    if best is None:
        raise KeyError(f"figure {fig} could not be searched")
    score, pno, r, (x, y), (w, h) = best
    box = (x / PROBE_SCALE, y / PROBE_SCALE,
           (x + w) / PROBE_SCALE, (y + h) / PROBE_SCALE)
    loc = Loc(pno, box, round(score, 4), round(PROBE_SCALE / r, 3))
    cache[fig] = {"page": loc.page, "box": list(loc.box),
                  "score": loc.score, "scale": loc.scale}
    _save_cache()
    return loc


def render_figure(fig, scale=3.0):
    """The figure re-rendered from the PDF at `scale`, framed as the app's crop is."""
    loc = resolve(fig)
    if loc.score < MIN_SCORE:
        raise ValueError(f"figure {fig} not located confidently (score {loc.score})")
    page = render_page(loc.page, scale)
    x0, y0, x1, y1 = (int(round(v * scale)) for v in loc.box)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(page.width, x1), min(page.height, y1)
    return page.crop((x0, y0, x1, y1)).convert("RGB")


def stored_figure(fig):
    """The already-extracted crop the app ships, for figures the PDF search can't place."""
    return Image.open(fig_path(fig)).convert("RGB")
