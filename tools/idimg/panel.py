"""Panel cropping and label/leader erasing for OpenStax figures."""
import cv2
import numpy as np
from PIL import Image

from .labels import leader_segments, leader_path, _trace_gray, _whiteness

WHITE = 235  # a pixel with every channel >= this is page background
MIN_PANEL = 0.04  # a drawing smaller than this share of the figure is a scrap, not a panel
STUB_AREA, STUB_SPAN = 600, 60  # leftover leader stubs are smaller than this (px area, px longest side)
LINE_ART_COLOR = 0.15  # a figure with fewer colored non-white pixels than this is line art


def leader_pixels(img: Image.Image, labels: list) -> np.ndarray:
    """uint8 mask (255 = leader line) of every label's leader lines, bends included."""
    W, H = img.size
    mask = np.zeros((H, W), np.uint8)
    gray, white = _trace_gray(img, labels), _whiteness(img)
    for L in labels:
        for seg in leader_segments(img, labels, L):  # every line leaving the label: forked leaders too
            path = leader_path(img, labels, L, start=seg, gray=gray, white=white)
            for p, q in zip(path, path[1:]):
                cv2.line(mask, p, q, 255, 9)
            if len(path) >= 2:  # cover the line's last few faint pixels past where the trace stopped
                (px, py), (qx, qy) = path[-2], path[-1]
                n = max(1e-6, np.hypot(qx - px, qy - py))
                tip = (int(qx + 8 * (qx - px) / n), int(qy + 8 * (qy - py) / n))
                cv2.line(mask, (qx, qy), tip, 255, 9)
    return mask


def _text_mask(img: Image.Image, labels: list, pad: int = 4) -> np.ndarray:
    W, H = img.size
    mask = np.zeros((H, W), np.uint8)
    for L in labels:
        for _, (x0, y0, x1, y1) in L.lines:
            mask[max(0, y0 - pad):y1 + pad, max(0, x0 - pad):x1 + pad] = 255
    return mask


def is_line_art(img: Image.Image) -> bool:
    """True for figures drawn in black outlines (bones, cells), where almost no non-white pixel is colored."""
    a = np.asarray(img.convert("RGB")).astype(int)
    drawn = a.min(axis=2) < WHITE
    sat = a.max(axis=2) - a.min(axis=2)
    return drawn.any() and (sat[drawn] >= 40).mean() < LINE_ART_COLOR


def _ink(img: Image.Image) -> np.ndarray:
    a = np.asarray(img.convert("RGB"))
    return (a.min(axis=2) < WHITE).astype(np.uint8) * 255


def drawing_mask(img: Image.Image, labels: list, lines: np.ndarray = None) -> np.ndarray:
    """uint8 mask of drawing pixels: non-white with outline drawings filled in, minus text and thin lines."""
    from scipy.ndimage import binary_fill_holes
    ink = _ink(img)
    ink[_text_mask(img, labels) > 0] = 0
    ink[(leader_pixels(img, labels) if lines is None else lines) > 0] = 0
    # close small gaps in outlines, then fill enclosed shapes (white bones drawn in outline)
    ink = cv2.dilate(ink, np.ones((5, 5), np.uint8))
    ink = binary_fill_holes(ink > 0).astype(np.uint8) * 255
    ink = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((11, 11), np.uint8))
    return cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))


def panel_box(img: Image.Image, point, labels: list, pad: int = 12):
    """Bounding box of the complete drawing that contains (or is nearest to) `point`."""
    W, H = img.size
    m = drawing_mask(img, labels)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    big = [k for k in range(1, n) if stats[k][4] >= MIN_PANEL * W * H]
    if not big:
        return (0, 0, W, H)
    x, y = point
    k = lab[min(max(y, 0), H - 1), min(max(x, 0), W - 1)]
    if k not in big:
        keep = np.isin(lab, big)
        ys, xs = np.nonzero(keep)
        i = np.argmin((xs - x) ** 2 + (ys - y) ** 2)
        k = lab[ys[i], xs[i]]
    bx, by, bw, bh, _ = stats[k]
    return (max(0, bx - pad), max(0, by - pad), min(W, bx + bw + pad), min(H, by + bh + pad))


def erase_labels(img: Image.Image, labels: list, lines: np.ndarray) -> Image.Image:
    """Inpaint label text and leader lines from the surrounding background."""
    a = np.asarray(img.convert("RGB")).copy()
    mask = cv2.bitwise_or(_text_mask(img, labels), lines)
    # any thin ink left in the white space around drawings is leftover line art: erase it too
    keep = cv2.dilate(drawing_mask(img, labels, lines), np.ones((7, 7), np.uint8))
    stray = cv2.bitwise_and(_ink(img), cv2.bitwise_not(keep))
    # In colored art every drawing pixel is inside `keep`, so white-space ink joined to a label (through traced
    # lines too) is leader. In line art the outlines themselves sit in the white space and touch the leaders, so
    # only tiny fragments go. Tiny fragments are stubs in either style.
    leader_ink = np.zeros(stray.shape, bool)
    if not is_line_art(img):
        text = _text_mask(img, labels, pad=12)
        joined = cv2.bitwise_or(cv2.bitwise_or(stray, lines), text)
        n, lab = cv2.connectedComponents(joined, connectivity=8)
        to_label = np.zeros(n, bool)
        to_label[np.unique(lab[text > 0])] = True
        to_label[0] = False
        leader_ink = to_label[lab] & (stray > 0)
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(stray, 8)
    tiny = np.isin(lab2, [k for k in range(1, n2) if st2[k][4] < STUB_AREA and max(st2[k][2], st2[k][3]) < STUB_SPAN])
    stray = (leader_ink | tiny).astype(np.uint8) * 255
    mask = cv2.bitwise_or(mask, cv2.dilate(stray, np.ones((5, 5), np.uint8)))
    out = cv2.inpaint(a, mask, 3, cv2.INPAINT_TELEA)
    # inpainting next to a drawing smears its outline into the margin: erased pixels in white space become white
    from scipy.ndimage import binary_fill_holes
    drawing = binary_fill_holes(drawing_mask(img, labels, lines) > 0)  # labels on the drawing leave holes: keep them inside
    out[(mask > 0) & ~drawing] = 255
    return Image.fromarray(out)
