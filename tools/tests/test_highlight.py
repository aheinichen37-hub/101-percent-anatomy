"""Task 3: marking the structure — a fill where it works, a fallback where it doesn't."""
import pytest

from idimg import figures, highlight, labels, panel

pytestmark = pytest.mark.skipif(not figures.pdf_available(),
                                reason="source PDF not staged in this session")


def _panel_and_point(fig, terms):
    img = figures.render_figure(fig, scale=3.0)
    found = labels.find_labels(img)
    lab = labels.match_label(found, terms)
    assert lab is not None, f"{terms} not found in {fig}"
    point = labels.trace_leader(img, lab, found)
    assert point is not None
    box = panel.panel_box(img, point, found)
    clean = labels.erase_labels(img, found)
    return panel.crop(clean, box), (point[0] - box[0], point[1] - box[1])


def test_fill_bounded():
    """A muscle is a clean colour region, so the fill should take it and stop there."""
    pan, point = _panel_and_point("11.16", ["Rectus abdominis"])
    mask, kind = highlight.make_mask(pan, point)
    assert kind == "fill"
    area = (mask.point(lambda v: 255 if v > 0 else 0)
            .convert("L").histogram()[255]) / (pan.width * pan.height)
    assert 0.02 <= area <= 0.35, f"fill covered {area:.1%} of the panel"


def test_landmark_falls_back():
    """A bony landmark has no colour boundary of its own, so a fill would flood the bone."""
    pan, point = _panel_and_point("8.5", ["Deltoid tuberosity"])
    _, kind = highlight.make_mask(pan, point)
    assert kind in {"outline", "circle", "arrow"}


def test_force_kind():
    pan, point = _panel_and_point("11.16", ["Rectus abdominis"])
    assert highlight.make_mask(pan, point, force="circle")[1] == "circle"
    assert highlight.make_mask(pan, point, force="arrow")[1] == "arrow"


def test_answer_image_size():
    pan, point = _panel_and_point("11.16", ["Rectus abdominis"])
    mask, kind = highlight.make_mask(pan, point)
    out = highlight.answer_image(pan, mask, kind, "Rectus abdominis", point)
    assert out.size == pan.size


def test_mask_png_is_the_highlight_colour():
    pan, point = _panel_and_point("11.16", ["Rectus abdominis"])
    mask, _ = highlight.make_mask(pan, point)
    rgba = highlight.mask_png(mask)
    assert rgba.mode == "RGBA"
    assert rgba.size == pan.size
    px = rgba.load()
    found = [px[x, y] for y in range(0, rgba.height, 7) for x in range(0, rgba.width, 7)
             if px[x, y][3] > 0]
    assert found, "mask is empty"
    assert all(p[:3] == highlight.HILITE_RGB for p in found)
