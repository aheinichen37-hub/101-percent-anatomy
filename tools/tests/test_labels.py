"""Task 2: reading a figure's labels, following a leader line, cropping its panel."""
import numpy as np
import pytest

from idimg import figures, labels, panel

pytestmark = pytest.mark.skipif(not figures.pdf_available(),
                                reason="source PDF not staged in this session")


@pytest.fixture(scope="module")
def fig1116():
    img = figures.render_figure("11.16", scale=3.0)
    return img, labels.find_labels(img)


@pytest.fixture(scope="module")
def fig199():
    img = figures.render_figure("19.9", scale=3.0)
    return img, labels.find_labels(img)


def test_two_line_label(fig1116):
    """'Rectus abdominis' is set over two lines and must still match as one label."""
    _, found = fig1116
    assert labels.match_label(found, ["Rectus abdominis"]) is not None


def test_alternate_name(fig199):
    img = figures.render_figure("11.32", scale=3.0)
    found = labels.find_labels(img)
    assert labels.match_label(found, ["Calcaneal tendon", "achilles tendon"]) is not None


def test_leader_lands_on_structure(fig199):
    img, found = fig199
    lab = labels.match_label(found, ["Left atrium"])
    assert lab is not None
    point = labels.trace_leader(img, lab, found)
    assert point is not None
    x, y = point
    arr = np.array(img.convert("L"))
    assert arr[y, x] < 245, "leader endpoint landed on blank paper"
    for other in found:
        x0, y0, x1, y1 = other.box
        dx = max(x0 - x, 0, x - x1)
        dy = max(y0 - y, 0, y - y1)
        assert (dx * dx + dy * dy) ** 0.5 > 40, f"endpoint sits on label {other.text!r}"


def test_duplicate_label_deterministic():
    """'Ulna' is labelled twice in 8.6; the same one must win every run."""
    img = figures.render_figure("8.6", scale=3.0)
    found = labels.find_labels(img)
    a = labels.match_label(found, ["Ulna"])
    b = labels.match_label(labels.find_labels(img), ["Ulna"])
    assert a is not None and b is not None
    assert a.box == b.box


def test_panel_excludes_other_panels(fig1116):
    img, found = fig1116
    lab = labels.match_label(found, ["Rectus abdominis"])
    point = labels.trace_leader(img, lab, found)
    assert point is not None
    box = panel.panel_box(img, point, found)
    x0, y0, x1, y1 = box
    assert x0 <= point[0] <= x1 and y0 <= point[1] <= y1
    others = panel.other_panel_centers(img, found, box)
    for cx, cy in others:
        assert not (x0 <= cx <= x1 and y0 <= cy <= y1), "crop swallowed another panel"


def test_cover_hides_text_and_keeps_the_drawing(fig199):
    img, found = fig199
    covered = labels.cover_labels(img, found)
    left = [l for l in labels.find_labels(covered)
            if sum(c.isalpha() for c in l.text) >= 3]
    assert left == [], f"text survived covering: {[l.text for l in left]}"
    # the artwork itself must be untouched — only the words go
    import numpy as np
    a, b = np.array(img.convert("L")), np.array(covered.convert("L"))
    changed = (a != b)
    for lab in found:
        x0, y0, x1, y1 = lab.box
        changed[max(0, y0 - 4):y1 + 4, max(0, x0 - 4):x1 + 4] = False
    assert changed.sum() == 0, "covering altered pixels outside the label boxes"
