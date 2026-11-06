"""Read a figure's labels and follow a label's leader line to the structure it names.

OpenStax figures put label text in the margins and join each label to its structure with
a thin line. So the structure is found in three moves: read the text, match the card's
answer against it, then walk that label's line inward until it reaches the drawing.
"""
import re
import unicodedata
from dataclasses import dataclass

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageDraw

TESS_CONFIG = "--psm 11"
MIN_CONF = 55
DARK = 128               # a pixel this dark is ink
LEADER_REACH = 110       # a leader line starts 50-70 px from its label text
LEADER_MAX_WALK = 1400   # stop walking rather than wander the whole drawing


@dataclass(frozen=True)
class Label:
    text: str
    box: tuple           # (x0, y0, x1, y1)

    @property
    def center(self):
        x0, y0, x1, y1 = self.box
        return ((x0 + x1) // 2, (y0 + y1) // 2)


def _norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = s.replace("ﬁ", "fi").replace("ﬂ", "fl")
    return re.sub(r"[^a-z0-9]", "", s.lower())


_OCR_CONFUSABLE = str.maketrans({"l": "i", "1": "i", "|": "i", "0": "o"})


def _ocr_fold(s):
    """Fold the strokes text recognition mixes up, so 'Uina' can still read as 'Ulna'.

    Only the look-alike strokes are folded, which keeps genuinely different names apart:
    ilium and ileum differ in a letter this does not touch.
    """
    return s.translate(_OCR_CONFUSABLE)


def _levenshtein(a, b):
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _words(img):
    data = pytesseract.image_to_data(img, config=TESS_CONFIG,
                                     output_type=pytesseract.Output.DICT)
    out = []
    for i, text in enumerate(data["text"]):
        text = (text or "").strip()
        if not text or not any(c.isalpha() for c in text):
            continue
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            continue
        if conf < MIN_CONF:
            continue
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        out.append((text, (x, y, x + w, y + h)))
    return out


def _rows(words):
    """Group words sitting on the same baseline into one line."""
    rows = []
    for text, box in sorted(words, key=lambda w: (w[1][1], w[1][0])):
        x0, y0, x1, y1 = box
        h = y1 - y0
        placed = False
        for row in rows:
            rx0, ry0, rx1, ry1 = row["box"]
            overlap = min(y1, ry1) - max(y0, ry0)
            if overlap > 0.5 * min(h, ry1 - ry0) and x0 - rx1 < 1.4 * h and x1 > rx0 - 1.4 * h:
                row["parts"].append((x0, text))
                row["box"] = (min(rx0, x0), min(ry0, y0), max(rx1, x1), max(ry1, y1))
                placed = True
                break
        if not placed:
            rows.append({"parts": [(x0, text)], "box": box})
    for row in rows:
        row["text"] = " ".join(t for _, t in sorted(row["parts"]))
    return rows


def _is_continuation(text):
    """A wrapped line carries on a name, so it starts lower case.

    These figures set labels in sentence case — "Deltoid tuberosity" wraps to
    "tuberosity", "Right pulmonary veins" to "veins" — while the next label down starts
    with a capital. Leading cannot be trusted for this: a wrapped line sits 3 px below
    its first line in one figure and 7 px in another, where separate labels sit 12 px
    apart. Nor can "does this line have a leader line", because in figures where the
    labels crowd the drawing, the drawing's own ink answers yes.
    """
    stripped = (text or "").lstrip("([")
    return bool(stripped) and stripped[0].islower()


def find_labels(img):
    """Every label in the figure, with multi-line labels joined into one."""
    rows = _rows(_words(img))
    rows.sort(key=lambda r: (r["box"][1], r["box"][0]))
    used = [False] * len(rows)
    labels = []
    for i, row in enumerate(rows):
        if used[i]:
            continue
        box = row["box"]
        text = row["text"]
        used[i] = True
        changed = True
        while changed:                      # a label can run to three or more lines
            changed = False
            x0, y0, x1, y1 = box
            height = y1 - y0
            for j, other in enumerate(rows):
                if used[j]:
                    continue
                ox0, oy0, ox1, oy1 = other["box"]
                gap = oy0 - y1
                if (abs(ox0 - x0) <= 8 and 0 <= gap <= 0.9 * height
                        and _is_continuation(other["text"])):
                    text += " " + other["text"]
                    box = (min(x0, ox0), min(y0, oy0), max(x1, ox1), max(y1, oy1))
                    used[j] = True
                    changed = True
                    break
        labels.append(Label(text, box))
    return labels


def match_labels(labels, terms):
    """Every label matching one of `terms`, in a stable order."""
    wanted = [_norm(t) for t in terms if _norm(t)]
    if not wanted:
        return []
    exact, near = [], []
    for lab in labels:
        # A figure may gloss a name in brackets — "Calcaneal (Achilles) tendon" — so the
        # bracketed text and the text without it are both candidate readings of the label.
        variants = {_norm(lab.text),
                    _norm(re.sub(r"\([^)]*\)", " ", lab.text)),
                    _norm(" ".join(re.findall(r"\(([^)]*)\)", lab.text)))}
        variants.discard("")
        if not variants:
            continue
        if variants & set(wanted):
            exact.append(lab)
            continue
        hit = False
        for got in variants:
            for term in wanted:
                if len(term) > 6 and abs(len(got) - len(term)) <= 1 and _levenshtein(got, term) <= 1:
                    hit = True
                elif len(term) >= 4 and _ocr_fold(got) == _ocr_fold(term):
                    hit = True
                if hit:
                    break
            if hit:
                break
        if hit:
            near.append(lab)
    # Last resort: a figure often labels the short form of what the card asks for —
    # "Spine" for "Spine of the scapula", "Supraspinous" where the second line was not
    # read. Only consulted when nothing matched outright, and only for a leading run of
    # at least five characters, so "Ulna" cannot swallow "Ulnar notch".
    partial = []
    if not exact and not near:
        for lab in labels:
            got = _norm(lab.text)
            if len(got) < 5:
                continue
            for term in wanted:
                short, long = sorted((got, term), key=len)
                if len(short) >= 5 and long.startswith(short):
                    partial.append(lab)
                    break

    hits = exact or near or partial
    return sorted(hits, key=lambda l: (l.box[1], l.box[0]))


def match_label(labels, terms):
    """The first matching label, chosen the same way on every run."""
    hits = match_labels(labels, terms)
    return hits[0] if hits else None


def _ink_mask(img, labels):
    gray = np.array(img.convert("L"))
    mask = (gray < DARK).astype(np.uint8) * 255
    for lab in labels:                      # take the text itself out of the line mask
        x0, y0, x1, y1 = lab.box
        cv2.rectangle(mask, (x0 - 2, y0 - 2), (x1 + 2, y1 + 2), 0, -1)
    return mask


def leader_segments(img, labels):
    """Straight ink segments, which is what leader lines are."""
    mask = _ink_mask(img, labels)
    lines = cv2.HoughLinesP(mask, 1, np.pi / 360, threshold=40,
                            minLineLength=22, maxLineGap=4)
    if lines is None:
        return []
    return [tuple(int(v) for v in seg) for seg in np.asarray(lines).reshape(-1, 4)]


def _dist_to_box(point, box):
    x, y = point
    x0, y0, x1, y1 = box
    dx = max(x0 - x, 0, x - x1)
    dy = max(y0 - y, 0, y - y1)
    return (dx * dx + dy * dy) ** 0.5


def _start_pixel(ink, label, img_w):
    """The first ink of the leader line, found by looking inward from the label text.

    The line does not touch the text: in these figures it begins 50-70 px away, so a
    short search would find nothing and a long one would find a neighbour's line. Looking
    along the label's own middle rows, inward only, keeps it on this label's line.
    """
    x0, y0, x1, y1 = label.box
    cy = (y0 + y1) // 2
    inward = -1 if (x0 + x1) / 2 > img_w / 2 else 1      # margin labels point inward
    edge = x0 if inward < 0 else x1
    h = ink.shape[0]
    for dist in range(4, LEADER_REACH):
        x = edge + inward * dist
        if not (0 <= x < ink.shape[1]):
            break
        for dy in range(-(y1 - y0) // 2, (y1 - y0) // 2 + 1):
            y = cy + dy
            if 0 <= y < h and ink[y, x]:
                return (x, y)
    return None


def trace_leader(img, label, labels=None, segments=None):
    """Follow `label`'s leader line to the point where it reaches the drawing.

    Walks the ink outward from the label and stops as soon as the line touches filled
    artwork — that contact point is on the structure. Where the drawing has no fill
    (plain line art), it falls back to the far end of the line.
    """
    if label is None:
        return None
    labels = labels if labels is not None else [label]

    rgb = np.array(img.convert("RGB")).astype(np.int16)
    gray = np.array(img.convert("L"))
    ink = gray < DARK
    for lab in labels:                      # the text is not part of any line
        lx0, ly0, lx1, ly1 = lab.box
        ink[max(0, ly0 - 3):ly1 + 3, max(0, lx0 - 3):lx1 + 3] = False

    start = _start_pixel(ink, label, img.width)
    if start is None:
        return None

    # Filled artwork: not paper, not outline. Label text is excluded as well — its
    # anti-aliased edge is neither white nor ink, and would stop the walk on the spot.
    # Colour is what marks real artwork. A black line on white paper carries a grey
    # anti-aliased halo that is neither white nor ink, and testing only for "not white"
    # stopped the walk on the leader line's own edge, inches from the label.
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    white = (rgb.max(axis=2) > 240) & (chroma < 14)
    fill = (~white) & (gray >= DARK) & (chroma >= 25)
    for lab in labels:
        lx0, ly0, lx1, ly1 = lab.box
        fill[max(0, ly0 - 8):ly1 + 8, max(0, lx0 - 8):lx1 + 8] = False

    h, w = ink.shape
    seen = np.zeros_like(ink, dtype=bool)
    seen[start[1], start[0]] = True
    queue = [(start, 0)]
    far, far_d = start, 0
    head = 0
    while head < len(queue):
        (x, y), d = queue[head]
        head += 1
        if d > far_d:
            far, far_d = (x, y), d
        y0b, y1b = max(0, y - 3), min(h, y + 4)
        x0b, x1b = max(0, x - 3), min(w, x + 4)
        patch = fill[y0b:y1b, x0b:x1b]
        if patch.sum() >= 6:            # a real filled area, not a stray pixel
            ys, xs = np.nonzero(patch)
            return (int(x0b + xs[len(xs) // 2]), int(y0b + ys[len(ys) // 2]))
        if d > LEADER_MAX_WALK:
            break
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and ink[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    queue.append(((nx, ny), d + 1))
    return far


def cover_labels(img, labels):
    """Hide the label text under plain boxes, leaving everything else alone.

    Inpainting the text and the leader lines was smearing the artwork around them, which
    looked worse than the lines it removed. A box over the words is enough: the card must
    not name the structure, and the lines pointing at it do no harm.
    """
    out = img.convert("RGB").copy()
    draw = ImageDraw.Draw(out)
    for lab in labels:
        x0, y0, x1, y1 = lab.box
        draw.rectangle((x0 - 3, y0 - 3, x1 + 3, y1 + 3), fill=(255, 255, 255))
    return out
