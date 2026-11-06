"""Task 3: marking the structure with a simple patch of colour."""
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
    clean = labels.cover_labels(img, found)
    return panel.crop(clean, box), (point[0] - box[0], point[1] - box[1])


def _area(mask, pan):
    return mask.point(lambda v: 255 if v > 0 else 0).histogram()[255] / (pan.width * pan.height)


def test_blob_sits_on_the_point():
    pan, point = _panel_and_point("11.16", ["Rectus abdominis"])
    mask, kind = highlight.make_mask(pan, point)
    assert kind == "blob"
    assert mask.load()[point[0], point[1]] > 0


def test_blob_marks_one_thing_not_the_panel():
    pan, point = _panel_and_point("19.9", ["Left atrium"])
    mask, _ = highlight.make_mask(pan, point)
    assert 0.002 <= _area(mask, pan) <= 0.20


def test_force_kind_for_overrides():
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
    assert rgba.mode == "RGBA" and rgba.size == pan.size
    px = rgba.load()
    lit = [px[x, y] for y in range(0, rgba.height, 7) for x in range(0, rgba.width, 7)
           if px[x, y][3] > 0]
    assert lit and all(p[:3] == highlight.HILITE_RGB for p in lit)
