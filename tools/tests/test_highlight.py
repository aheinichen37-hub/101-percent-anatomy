import numpy as np
import pytest
from PIL import Image
from tools.idimg.labels import render_figure, find_labels, match_label, trace_leader
from tools.idimg.panel import panel_box, erase_labels, leader_pixels
from tools.idimg.highlight import make_mask, mask_png, answer_image


def panel_for(fig, terms):
    """The erased, cropped panel holding the card's structure, and the traced point in panel coordinates."""
    img = render_figure(fig)
    labels = find_labels(img)
    pt = trace_leader(img, match_label(labels, terms), labels)
    x0, y0, x1, y1 = panel_box(img, pt, labels)
    clean = erase_labels(img, labels, leader_pixels(img, labels)).crop((x0, y0, x1, y1))
    return clean, (pt[0] - x0, pt[1] - y0)


@pytest.fixture(scope="module")
def rectus():
    return panel_for("11.16", ["Rectus abdominis"])


def test_fill_bounded(rectus):
    panel, pt = rectus
    mask, kind = make_mask(panel, pt)
    share = (np.asarray(mask) > 127).mean()
    assert kind == "fill"
    assert 0.02 <= share <= 0.35


def test_fill_covers_the_point(rectus):
    panel, (x, y) = rectus
    mask, _ = make_mask(panel, (x, y))
    assert np.asarray(mask)[y, x] > 127


def test_landmark_falls_back():
    panel, pt = panel_for("8.5", ["Deltoid tuberosity"])
    _, kind = make_mask(panel, pt)
    assert kind in {"outline", "circle", "arrow"}


@pytest.mark.parametrize("kind", ["fill", "outline", "circle", "arrow"])
def test_force_kind(rectus, kind):
    panel, pt = rectus
    mask, got = make_mask(panel, pt, force=kind)
    assert got == kind
    assert (np.asarray(mask) > 127).any()


def test_mask_png_color(rectus):
    panel, pt = rectus
    mask, _ = make_mask(panel, pt)
    png = np.asarray(mask_png(mask))
    on = png[..., 3] > 127
    assert png.shape[:2] == np.asarray(mask).shape
    assert on.any() and (png[on][:, :3] == [0x4F, 0xD4, 0xFF]).all()


def test_answer_image_size(rectus):
    panel, pt = rectus
    mask, kind = make_mask(panel, pt)
    out = answer_image(panel, mask, kind, "Rectus abdominis")
    assert out.size == panel.size


def test_answer_image_shows_highlight(rectus):
    panel, pt = rectus
    mask, kind = make_mask(panel, pt)
    out = np.asarray(answer_image(panel, mask, kind, "Rectus abdominis").convert("RGB")).astype(int)
    m = np.asarray(mask) > 127
    hl = np.array([0x4F, 0xD4, 0xFF])
    before = np.linalg.norm(np.asarray(panel.convert("RGB")).astype(int)[m] - hl, axis=1).mean()
    after = np.linalg.norm(out[m] - hl, axis=1).mean()
    # the highlighted pixels move toward light blue (also on near-white structures, where blue is already high)
    assert after < 0.75 * before


def _box_cols(img):
    """x-range of the name box's dark border/text in an otherwise white picture."""
    a = np.asarray(img.convert("L")) < 128
    xs = np.nonzero(a.any(axis=0))[0]
    ys = np.nonzero(a.any(axis=1))[0]
    return xs.min(), xs.max(), ys.min(), ys.max()


def test_name_box_fits_a_narrow_panel():
    from tools.idimg.highlight import answer_image
    panel = Image.new("RGB", (240, 700), "white")
    mask = Image.new("L", (240, 700), 0)
    out = answer_image(panel, mask, "leader", "Coronoid process", at=(150, 300, 239, 320))
    x0, x1, _, _ = _box_cols(out)
    assert x0 >= 2 and x1 <= 237


def test_name_box_matches_the_textbook_label_size():
    from tools.idimg.highlight import answer_image
    panel = Image.new("RGB", (800, 700), "white")
    mask = Image.new("L", (800, 700), 0)
    out = answer_image(panel, mask, "leader", "Olecranon", at=(100, 300, 190, 320))
    _, _, y0, y1 = _box_cols(out)
    assert y1 - y0 <= 36          # label line was 20 px tall: the box stays near that, not a 28 px headline


def test_name_box_anchors_at_the_leader_end():
    from tools.idimg.highlight import answer_image
    panel = Image.new("RGB", (800, 700), "white")
    mask = Image.new("L", (800, 700), 0)
    out = answer_image(panel, mask, "leader", "Olecranon process", at=(500, 300, 560, 320), anchor="right")
    _, x1, _, _ = _box_cols(out)
    assert abs(x1 - 566) <= 4     # leader leaves the label's right side: the box ends there


def test_after_answer_highlight_reads_blue_on_red_muscle():
    # at 45% the light blue over heart-red mixed to gray: the lit structure must still look blue
    from tools.idimg.highlight import answer_image
    panel = Image.new("RGB", (400, 400), (220, 80, 70))
    mask = Image.new("L", (400, 400), 255)
    r, g, b = answer_image(panel, mask, "fill", "Aorta").getpixel((20, 380))
    assert b > r + 30



def test_name_box_never_covers_the_highlight():
    # Pulmonary valve's circle in 19.9 sits near the label column: the name box landed on top of it
    from tools.idimg.highlight import answer_image, make_mask
    img = render_figure("19.9").convert("RGB")
    panel = img.crop((263, 6, 793, 653))
    mask, kind = make_mask(panel, (530 - 263, 340 - 6), force="circle")
    out = np.asarray(answer_image(panel, mask, kind, "Pulmonary valve").convert("RGB")).astype(int)
    ring = np.asarray(mask) > 127
    hl = np.array([0x4F, 0xD4, 0xFF])
    near = ((np.abs(out - hl).sum(axis=2) < 200) & ring).mean() / ring.mean()
    assert near > 0.9      # nearly all the ring still shows its blue
