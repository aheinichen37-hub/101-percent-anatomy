"""The light-blue structure highlight and the labeled after-answer picture."""
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from skimage.color import rgb2lab

HL = (0x4F, 0xD4, 0xFF)  # highlight color #4fd4ff
DELTA_E = 14             # fill tolerance (CIE76) around the structure's color
OUTLINE_L = 35           # Lab lightness below this is a drawing outline: the fill stops there
MAX_SHARE = 0.35         # a fill covering more of the drawing than this has bled (or lit a whole bone)
MIN_AREA = 300           # px: a smaller fill would be invisible, use a circle instead
OUTLINE_R = 70           # px radius of the local outline used for landmarks
RING_R, RING_W = 28, 6
ARROW_LEN = 60
WHITE = 235
WHITE_L = 93             # Lab lightness of near-white: the inside of a bone drawn in outline


def _drawing(arr):
    return arr.min(axis=2) < WHITE


def _seed(lab, x, y):
    """Reference Lab color at (x, y): median of the non-outline pixels in a 9x9 window (tips can sit on a line)."""
    H, W = lab.shape[:2]
    win = lab[max(0, y - 4):y + 5, max(0, x - 4):x + 5].reshape(-1, 3)
    ok = win[win[:, 0] >= OUTLINE_L]
    return np.median(ok if len(ok) else win, axis=0)


def _region(arr, point, limit=None):
    """Connected pixels near the seed color and not outline, containing (or nearest to) the point."""
    lab = rgb2lab(arr)
    x, y = point
    ref = _seed(lab, x, y)
    de = np.sqrt(((lab - ref) ** 2).sum(axis=2))
    cand = ((de <= DELTA_E) & (lab[..., 0] >= OUTLINE_L) & _drawing(arr)).astype(np.uint8)
    if limit is not None:
        cand &= limit
    n, lab_cc = cv2.connectedComponents(cand, connectivity=4)
    k = lab_cc[y, x]
    if k == 0:
        ys, xs = np.nonzero(cand)
        if not len(xs):
            return np.zeros(cand.shape, np.uint8)
        i = np.argmin((xs - x) ** 2 + (ys - y) ** 2)
        if (xs[i] - x) ** 2 + (ys[i] - y) ** 2 > 12 ** 2:
            return np.zeros(cand.shape, np.uint8)
        k = lab_cc[ys[i], xs[i]]
    m = (lab_cc == k).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    return cv2.dilate(m, np.ones((5, 5), np.uint8))  # 2 px each side


def _ring(shape, point):
    m = np.zeros(shape, np.uint8)
    cv2.circle(m, tuple(int(v) for v in point), RING_R, 255, RING_W)
    return m


def _arrow(arr, point):
    """A 60 px arrow pointing at the point from the side with the most white space."""
    H, W = arr.shape[:2]
    x, y = point
    white = ~_drawing(arr)
    best, tail = -1, None
    for ang in range(0, 360, 15):
        tx = int(x + ARROW_LEN * np.cos(np.radians(ang)))
        ty = int(y + ARROW_LEN * np.sin(np.radians(ang)))
        if not (0 <= tx < W and 0 <= ty < H):
            continue
        n = 40
        free = sum(white[int(y + r / n * (ty - y)), int(x + r / n * (tx - x))] for r in range(n // 2, n + 1))
        if free > best:
            best, tail = free, (tx, ty)
    m = np.zeros((H, W), np.uint8)
    if tail is None:
        tail = (min(W - 1, x + ARROW_LEN), y)
    cv2.arrowedLine(m, tail, (int(x), int(y)), 255, 7, tipLength=0.35)
    return m


def make_mask(panel_img: Image.Image, point, force: str = None):
    """(mask 'L' image, kind). Tries fill → outline → circle unless `force` names one of fill/outline/circle/arrow."""
    arr = np.asarray(panel_img.convert("RGB"))
    H, W = arr.shape[:2]
    x = min(max(int(point[0]), 0), W - 1)
    y = min(max(int(point[1]), 0), H - 1)
    drawing_px = max(1, int(_drawing(arr).sum()))

    def fill():
        return _region(arr, (x, y))

    def outline():
        disc = np.zeros((H, W), np.uint8)
        cv2.circle(disc, (x, y), OUTLINE_R, 1, -1)
        return _region(arr, (x, y), limit=disc)

    makers = {"fill": fill, "outline": outline, "circle": lambda: _ring((H, W), (x, y)),
              "arrow": lambda: _arrow(arr, (x, y))}
    if force:
        return Image.fromarray(makers[force]()), force

    # line art (bones drawn in black outline) has no color regions to fill: circle the spot instead
    from .panel import is_line_art
    if is_line_art(panel_img) or _seed(rgb2lab(arr[max(0, y - 4):y + 5, max(0, x - 4):x + 5]), 4, 4)[0] >= WHITE_L:
        return Image.fromarray(_ring((H, W), (x, y))), "circle"

    m = fill()
    area = int((m > 0).sum())
    touches_edge = m[0].any() or m[-1].any() or m[:, 0].any() or m[:, -1].any()
    if MIN_AREA <= area <= MAX_SHARE * drawing_px and not touches_edge:
        return Image.fromarray(m), "fill"
    m = outline()
    if (m > 0).sum() >= MIN_AREA:
        return Image.fromarray(m), "outline"
    return Image.fromarray(_ring((H, W), (x, y))), "circle"


LEADER_W = 11      # px width of the glow drawn over a leader line
TIP_R = 22         # px radius of the ring at the leader's tip


def leader_mask(size, path) -> Image.Image:
    """Mask lighting a leader line along `path` (panel coordinates) and ringing its tip."""
    W, H = size
    m = np.zeros((H, W), np.uint8)
    pts = [tuple(int(v) for v in p) for p in path]
    for p, q in zip(pts, pts[1:]):
        cv2.line(m, p, q, 255, LEADER_W)
    if pts:
        cv2.circle(m, pts[-1], TIP_R, 255, RING_W)
    return Image.fromarray(m)


def mask_png(mask: Image.Image) -> Image.Image:
    a = np.asarray(mask.convert("L"))
    out = np.zeros(a.shape + (4,), np.uint8)
    out[..., :3] = HL
    out[..., 3] = a
    return Image.fromarray(out, "RGBA")


def _font(size):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def answer_image(panel_img: Image.Image, mask: Image.Image, kind: str, name: str, at=None,
                 anchor: str = "left") -> Image.Image:
    """The panel with the highlight at 65% (still blue over red muscle) and the structure's name in a box joined to it by a line.

    `at` (x0, y0, x1, y1): put the name there instead, with no joining line (line art keeps the textbook's own leader),
    in about the textbook label's own type size. `anchor` is the label side its leader leaves from: the box ends there.
    """
    base = panel_img.convert("RGB")
    arr = np.asarray(base).astype(np.float32)
    m = np.asarray(mask.convert("L")).astype(np.float32)[..., None] / 255 * 0.65
    arr = arr * (1 - m) + np.array(HL, np.float32) * m
    out = Image.fromarray(arr.astype(np.uint8))
    W, H = out.size
    ys, xs = np.nonzero(np.asarray(mask) > 127)
    if len(xs):
        cx, cy = int(np.median(xs)), int(np.median(ys))
    else:
        cx, cy = W // 2, H // 2
    d = ImageDraw.Draw(out)
    size = 28 if at is None else int(min(28, max(14, at[3] - at[1])))
    pad_x, pad_y = (12, 8) if at is None else (6, 4)
    while True:  # shrink until the box fits the picture's width
        font = _font(size)
        tw, th = d.textbbox((0, 0), name, font=font)[2:]
        bw, bh = tw + 2 * pad_x, th + 2 * pad_y
        if bw <= W - 8 or size <= 10:
            break
        size -= 1
    white = ~_drawing(np.asarray(base))
    # candidate spots around the structure at two distances; pick the one on the most white space that never
    # covers the highlight itself (spots near an edge get pushed back inside, which can land them on it)
    lit = cv2.dilate((np.asarray(mask.convert("L")) > 60).astype(np.uint8), np.ones((17, 17), np.uint8)) > 0
    spots = []
    for r in (70, 130):
        spots += [(cx - bw // 2, cy - bh - r), (cx - bw // 2, cy + r), (cx - bw - r - 20, cy - bh // 2),
                  (cx + r + 20, cy - bh // 2), (cx - bw - r, cy - bh - r), (cx + r, cy - bh - r),
                  (cx - bw - r, cy + r), (cx + r, cy + r)]
    best, bx, by = -1e9, None, None
    for i, (sx, sy) in enumerate(spots):
        sx = int(min(max(sx, 4), max(4, W - bw - 4)))
        sy = int(min(max(sy, 4), max(4, H - bh - 4)))
        if bh <= 0 or bw <= 0:
            continue
        score = white[sy:sy + bh, sx:sx + bw].mean() - 5 * lit[sy:sy + bh, sx:sx + bw].mean() - 0.01 * (i >= 8)
        if score > best:
            best, bx, by = score, sx, sy
    if at is not None:
        ax0, ay0, ax1, ay1 = at
        want = ax1 + 6 - bw if anchor == "right" else ax0 - 6
        bx = int(min(max(want, 4), max(4, W - bw - 4)))
        by = int(min(max((ay0 + ay1) / 2 - bh / 2, 4), max(4, H - bh - 4)))
    else:
        near = (min(max(cx, bx), bx + bw), min(max(cy, by), by + bh))
        d.line([near, (cx, cy)], fill=(20, 20, 20), width=2)
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=min(10, bh // 3), fill=(255, 255, 255),
                        outline=(20, 20, 20), width=2)
    d.text((bx + pad_x, by + pad_y), name, font=font, fill=(0, 0, 0))
    return out
