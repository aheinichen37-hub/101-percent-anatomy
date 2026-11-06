import numpy as np
import pytest
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
