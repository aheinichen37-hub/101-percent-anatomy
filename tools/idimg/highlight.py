"""Mark one structure inside a panel.

A fill is the clearest marker: the whole muscle or chamber glows and its shape is the
answer. It only works where the structure is its own colour region. A bony landmark is a
named spot on a single uniformly coloured bone, so a fill there floods the whole bone —
those fall back to a local outline, then a circle, then an arrow.
"""
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HILITE_RGB = (79, 212, 255)      # #4fd4ff
MAX_FILL_FRACTION = 0.35         # above this the fill has leaked out of the structure
MIN_FILL_FRACTION = 0.004
OUTLINE_RADIUS = 70
CIRCLE_RADIUS = 28
CIRCLE_WIDTH = 6
ARROW_LEN = 60
DARK_L = 89                      # L* < 35 on a 0-100 scale, in OpenCV's 0-255 encoding
TOL = 14                         # per-channel Lab tolerance, standing in for dE <= 14

_FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
          "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def _font(size):
    for path in _FONTS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _flood(panel_img, point):
    """Grow a region from the point, stopped by the drawing's own dark outlines."""
    bgr = cv2.cvtColor(np.array(panel_img.convert("RGB")), cv2.COLOR_RGB2BGR)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    h, w = lab.shape[:2]
    x = int(max(0, min(w - 1, point[0])))
    y = int(max(0, min(h - 1, point[1])))

    barrier = (lab[:, :, 0] < DARK_L).astype(np.uint8)
    ff = np.zeros((h + 2, w + 2), np.uint8)
    ff[1:-1, 1:-1] = barrier

    # Seed on real artwork colour. Erasing the leader line inpaints its tip with the
    # background around it, so the point the trace returned can be pale by the time the
    # fill runs — and a fill seeded on pale paper escapes into the whole page.
    rgb = np.array(panel_img.convert("RGB")).astype(np.int16)
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    if chroma[y, x] < 25 or barrier[y, x]:
        r = 26
        y0b, y1b = max(0, y - r), min(h, y + r + 1)
        x0b, x1b = max(0, x - r), min(w, x + r + 1)
        good = (chroma[y0b:y1b, x0b:x1b] >= 25) & (barrier[y0b:y1b, x0b:x1b] == 0)
        ys, xs = np.nonzero(good)
        if len(xs):
            d = (ys + y0b - y) ** 2 + (xs + x0b - x) ** 2
            i = int(np.argmin(d))
            y, x = int(ys[i] + y0b), int(xs[i] + x0b)
        elif barrier[y, x]:
            return np.zeros((h, w), bool)

    # Fixed range: every pixel is compared with the seed's colour, not its neighbour's,
    # so the fill cannot walk a gradient out of the structure.
    cv2.floodFill(lab.copy(), ff, (x, y), 0,
                  (TOL, TOL, TOL), (TOL, TOL, TOL),
                  4 | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (255 << 8))
    region = (ff[1:-1, 1:-1] == 255)

    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    region = cv2.morphologyEx(region.astype(np.uint8), cv2.MORPH_CLOSE, k)
    region = cv2.dilate(region, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    return region.astype(bool)


def _touches_border(region):
    return (region[0, :].any() or region[-1, :].any()
            or region[:, 0].any() or region[:, -1].any())


def _disk(shape, point, radius):
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    return (xx - point[0]) ** 2 + (yy - point[1]) ** 2 <= radius * radius


def _ring(shape, point):
    m = np.zeros(shape, np.uint8)
    cv2.circle(m, (int(point[0]), int(point[1])), CIRCLE_RADIUS, 255, CIRCLE_WIDTH)
    return m.astype(bool)


def _arrow(shape, point):
    """An arrow coming in from whichever side has the most room."""
    h, w = shape
    x, y = int(point[0]), int(point[1])
    room = {"left": x, "right": w - x, "up": y, "down": h - y}
    side = max(room, key=room.get)
    dx, dy = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}[side]
    tail = (x + dx * ARROW_LEN, y + dy * ARROW_LEN)
    m = np.zeros(shape, np.uint8)
    cv2.arrowedLine(m, tail, (x, y), 255, 7, tipLength=0.35)
    return m.astype(bool)


def blob_radius(panel_img):
    """How big the patch should be: enough to read, small enough to point at one thing."""
    return int(max(26, min(90, min(panel_img.width, panel_img.height) * 0.10)))


def make_mask(panel_img, point, force=None):
    """A soft patch of colour over the structure at `point`.

    Chasing the structure's exact outline was the wrong trade: a flood fill that strays
    onto the sheath beside a muscle teaches the wrong thing, and it is not worth the
    effort it costs. A patch centred on the spot the leader line reaches says "this one"
    without claiming a shape it cannot verify.

    Returns (PIL 'L' image, kind) where kind is blob | circle | arrow.
    """
    shape = (panel_img.height, panel_img.width)

    def finish(region, kind):
        return Image.fromarray((region.astype(np.uint8) * 255), mode="L"), kind

    if force == "circle":
        return finish(_ring(shape, point), "circle")
    if force == "arrow":
        return finish(_arrow(shape, point), "arrow")
    return finish(_disk(shape, point, blob_radius(panel_img)), "blob")


def mask_png(mask):
    """The mask as a transparent overlay in the highlight colour."""
    alpha = mask.convert("L")
    rgba = Image.new("RGBA", alpha.size, HILITE_RGB + (0,))
    rgba.putalpha(alpha)
    return rgba


def answer_image(panel_img, mask, kind, name, point):
    """The same panel with the highlight shown and the structure named beside it."""
    base = panel_img.convert("RGB").copy()
    overlay = Image.new("RGBA", base.size, HILITE_RGB + (0,))
    overlay.putalpha(mask.convert("L").point(lambda v: int(v * 0.45)))
    base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(base)
    font = _font(28)
    pad = 8
    tw = draw.textlength(name, font=font)
    th = 34
    x, y = int(point[0]), int(point[1])

    # put the plate in whichever margin has room, then lead the eye back to the point
    if x + 40 + tw + pad * 2 < base.width:
        bx = x + 40
    else:
        bx = max(0, x - 40 - int(tw) - pad * 2)
    by = max(0, min(base.height - th - pad * 2, y - th // 2))

    box = (bx, by, bx + int(tw) + pad * 2, by + th + pad)
    draw.line((max(0, min(base.width - 1, bx)), by + (th + pad) // 2, x, y),
              fill=(20, 20, 20), width=2)
    draw.rounded_rectangle(box, radius=8, fill=(255, 255, 255), outline=(20, 20, 20), width=2)
    draw.text((bx + pad, by + pad // 2), name, font=font, fill=(10, 10, 10))
    return base
