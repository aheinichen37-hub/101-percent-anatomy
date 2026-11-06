"""Crop a figure down to the one drawing that contains the structure.

Many OpenStax figures carry several drawings side by side. Showing all of them while
only one is highlighted makes the card harder to read than it needs to be, so the build
keeps the panel the structure sits in and drops the rest — without clipping that drawing.
"""
import cv2
import numpy as np

from . import labels as labels_mod

PAD = 12
BG = 245                 # lighter than this is page, not drawing
MIN_PANEL_AREA = 0.01    # ignore specks when looking for other panels


def _drawing_mask(img, labels):
    """Everything that is drawing: ink and fill, with text and leader lines removed."""
    gray = np.array(img.convert("L"))
    mask = (gray < BG).astype(np.uint8) * 255
    for lab in labels or []:
        x0, y0, x1, y1 = lab.box
        cv2.rectangle(mask, (x0 - 3, y0 - 3), (x1 + 3, y1 + 3), 0, -1)
    for x0, y0, x1, y1 in labels_mod.leader_segments(img, labels or []):
        cv2.line(mask, (x0, y0), (x1, y1), 0, 7)
    # Close hard, so one drawing reads as one region. A heart's chambers are separated
    # by their own outlines; closing timidly split them and cropped into the heart
    # instead of keeping the whole organ with one part marked.
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)


def _components(mask):
    n, lab, stats, cents = cv2.connectedComponentsWithStats(mask, 8)
    out = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        out.append({"id": i, "box": (x, y, x + w, y + h), "area": int(area),
                    "center": (int(cents[i][0]), int(cents[i][1]))})
    out.sort(key=lambda c: -c["area"])
    return lab, out


def panel_box(img, point, labels=None):
    """The box of the drawing containing `point`, padded and clamped to the image."""
    mask = _drawing_mask(img, labels)
    lab, comps = _components(mask)
    x, y = point
    h, w = mask.shape
    x = max(0, min(w - 1, x))
    y = max(0, min(h - 1, y))

    cid = int(lab[y, x])
    if cid == 0:                      # the point fell in a gap; take the nearest region
        best = None
        for c in comps:
            cx0, cy0, cx1, cy1 = c["box"]
            dx = max(cx0 - x, 0, x - cx1)
            dy = max(cy0 - y, 0, y - cy1)
            d = (dx * dx + dy * dy) ** 0.5
            if best is None or d < best[0]:
                best = (d, c)
        if best is None:
            return (0, 0, w, h)
        bx0, by0, bx1, by1 = best[1]["box"]
        # the point sat in a gap, so widen to cover it rather than crop it away
        box = (min(bx0, x), min(by0, y), max(bx1, x), max(by1, y))
    else:
        box = next(c["box"] for c in comps if c["id"] == cid)

    x0, y0, x1, y1 = box
    return (max(0, x0 - PAD), max(0, y0 - PAD), min(w, x1 + PAD), min(h, y1 + PAD))


def other_panel_centers(img, labels=None, exclude_box=None):
    """Centers of the other substantial drawings, used to check a crop isn't too greedy."""
    mask = _drawing_mask(img, labels)
    _, comps = _components(mask)
    total = mask.shape[0] * mask.shape[1]
    out = []
    for c in comps:
        if c["area"] < MIN_PANEL_AREA * total:
            continue
        if exclude_box:
            x0, y0, x1, y1 = exclude_box
            cx, cy = c["center"]
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                continue
        out.append(c["center"])
    return out


def crop(img, box):
    return img.crop(tuple(int(v) for v in box))
