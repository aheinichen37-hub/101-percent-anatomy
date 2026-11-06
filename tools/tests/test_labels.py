import numpy as np
import pytest
from tools.idimg.labels import render_figure, find_labels, match_label, trace_leader
from tools.idimg.panel import panel_box, erase_labels, leader_pixels


@pytest.fixture(scope="module")
def abd():
    img = render_figure("11.16")
    return img, find_labels(img)


def _is_drawing(img, x, y):
    r, g, b = img.convert("RGB").getpixel((x, y))
    return min(r, g, b) < 235  # not page-white


def test_two_line_label(abd):
    img, labels = abd
    assert match_label(labels, ["Rectus abdominis"]) is not None


def test_alternate_name():
    img = render_figure("11.32")
    lab = match_label(find_labels(img), ["Calcaneal tendon", "achilles tendon"])
    assert lab is not None


def test_leader_lands_on_structure():
    img = render_figure("19.9")
    labels = find_labels(img)
    lab = match_label(labels, ["Left atrium"])
    assert lab is not None
    pt = trace_leader(img, lab)
    assert pt is not None
    x, y = pt
    assert _is_drawing(img, x, y)
    for L in labels:
        x0, y0, x1, y1 = L.box
        dx = max(x0 - x, 0, x - x1)
        dy = max(y0 - y, 0, y - y1)
        assert (dx * dx + dy * dy) ** 0.5 > 40


def test_panel_excludes_other_panels(abd):
    img, labels = abd
    lab = match_label(labels, ["Rectus abdominis"])
    pt = trace_leader(img, lab)
    x0, y0, x1, y1 = panel_box(img, pt, labels)
    W, H = img.size
    # panel (b), the pelvis, sits in the lower ~40% of this figure
    assert y1 < H * 0.66
    assert x0 <= pt[0] <= x1 and y0 <= pt[1] <= y1


def test_duplicate_label_deterministic():
    img = render_figure("8.6")
    labels = find_labels(img)
    a = match_label(labels, ["Ulna"])
    b = match_label(find_labels(img), ["Ulna"])
    assert a is not None and a.box == b.box


@pytest.fixture(scope="module")
def heart():
    img = render_figure("19.9")
    return img, find_labels(img)


def test_bent_leader_reaches_left_atrium(heart):
    # the left atrium leader runs left from its label, then bends down into the atrium
    img, labels = heart
    x, y = trace_leader(img, match_label(labels, ["Left atrium"]), labels)
    assert 590 < x < 760 and 200 < y < 300


def test_leader_pixels_cover_whole_bent_line(heart):
    img, labels = heart
    lab = match_label(labels, ["Left atrium"])
    x, y = trace_leader(img, lab, labels)
    m = leader_pixels(img, labels)
    assert m[y - 6:y + 7, x - 6:x + 7].any()


def test_heart_leaders_erased_from_margins(heart):
    # after erasing, the white space around the heart holds no leftover leader lines
    from tools.idimg.panel import drawing_mask
    img, labels = heart
    x0, y0, x1, y1 = panel_box(img, trace_leader(img, match_label(labels, ["Left atrium"]), labels), labels)
    clean = np.asarray(erase_labels(img, labels, leader_pixels(img, labels)).convert("L"))[y0:y1, x0:x1]
    margin = drawing_mask(img, labels)[y0:y1, x0:x1] == 0
    margin = np.asarray(__import__("cv2").erode(margin.astype(np.uint8), np.ones((9, 9), np.uint8))) > 0
    assert (clean[margin] < 110).mean() < 0.002


def test_line_art_panel_is_one_view():
    # 8.6 shows anterior and posterior views of outline-drawn forearm bones side by side
    img = render_figure("8.6")
    labels = find_labels(img)
    pt = trace_leader(img, match_label(labels, ["Ulna"]), labels)
    x0, y0, x1, y1 = panel_box(img, pt, labels)
    assert x1 - x0 < 0.6 * img.size[0]
    assert x0 <= pt[0] <= x1 and y0 <= pt[1] <= y1


def test_panel_not_a_scrap():
    img = render_figure("8.6")
    labels = find_labels(img)
    pt = trace_leader(img, match_label(labels, ["Ulna"]), labels)
    x0, y0, x1, y1 = panel_box(img, pt, labels)
    W, H = img.size
    assert (x1 - x0) * (y1 - y0) > 0.15 * W * H


def test_erase_leaves_no_text(abd):
    img, labels = abd
    lab = match_label(labels, ["Rectus abdominis"])
    pt = trace_leader(img, lab)
    box = panel_box(img, pt, labels)
    clean = erase_labels(img, labels, leader_pixels(img, labels)).crop(box)
    left = [L for L in find_labels(clean) if sum(c.isalpha() for c in L.text) >= 3]
    assert left == []


def test_erase_does_not_punch_white_holes(heart):
    # labels printed on top of the drawing must be inpainted with drawing color, not blanked to white
    from scipy.ndimage import binary_fill_holes
    from tools.idimg.panel import drawing_mask
    img, labels = heart
    orig = np.asarray(img.convert("RGB"))
    clean = np.asarray(erase_labels(img, labels, leader_pixels(img, labels)).convert("RGB"))
    inside = binary_fill_holes(drawing_mask(img, labels) > 0)
    inside = __import__("cv2").erode(inside.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    new_white = (clean.min(axis=2) >= 250) & (orig.min(axis=2) < 235) & inside
    assert new_white.sum() < 200


def test_erase_keeps_line_art():
    # 8.5 draws the humerus as thin black outlines; erasing labels must not erase the bone itself
    from tools.idimg.panel import _text_mask
    img = render_figure("8.5")
    labels = find_labels(img)
    lines = leader_pixels(img, labels)
    keep = (_text_mask(img, labels) == 0) & (np.asarray(__import__("cv2").dilate(lines, np.ones((9, 9), np.uint8))) == 0)
    before = (np.asarray(img.convert("L")) < 110) & keep
    after = (np.asarray(erase_labels(img, labels, lines).convert("L")) < 110) & keep
    assert after.sum() >= 0.9 * before.sum()


# true leader tips read off Figure 19.9 at render scale 3.0 (1104x776)
HEART_TIPS = {
    "Moderator band": (545, 545),
    "Endocardium": (680, 568),
    "Pulmonary valve": (530, 340),
    "Tricuspid valve": (420, 427),
    "Fossa ovalis": (443, 342),
}


HAND_FIXED = {  # leaders the general rules can't follow; corrected by hand in tools/id-overrides.json
    "Fossa ovalis": "override ch19-anat Fossa ovalis: bent part runs over pale pink, too faint to detect",
    "Pulmonary valve": "override ch19-anat Pulmonary valve: leader bends over the drawing, tracer only bends in white space",
}


@pytest.mark.parametrize("term", [
    pytest.param(t, marks=pytest.mark.xfail(reason=HAND_FIXED[t], strict=True)) if t in HAND_FIXED else t
    for t in sorted(HEART_TIPS)])
def test_leader_tip_matches_figure(heart, term):
    # leaders are gray; the trace must follow the gray line, not slide onto colored outlines
    img, labels = heart
    x, y = trace_leader(img, match_label(labels, [term]), labels)
    tx, ty = HEART_TIPS[term]
    assert abs(x - tx) <= 25 and abs(y - ty) <= 25, (x, y)



def test_words_only_erase_leaves_no_white_box_on_the_drawing():
    # OCR reads a false "Vi" on 8.2's spine: blanking it to white punches a rectangle into the skeleton
    import numpy as np
    from tools.idimg.build import _figure
    from tools.idimg.panel import words_only_erased
    img, labels, _ = _figure("8.2")
    out = np.asarray(words_only_erased(img, labels).convert("L"))
    x0, y0, x1, y1 = 288, 412, 336, 458  # where OCR read "Vi"
    assert out[y0:y1, x0:x1].mean() < 235


def test_words_only_erase_skips_ocr_junk_on_line_art():
    # OCR reads bone shading on 8.7's wrist as "wa": that is drawing, not a label, and must stay untouched
    import numpy as np
    from tools.idimg.build import _figure
    from tools.idimg.panel import words_only_erased
    img, labels, _ = _figure("8.7")
    wa = next(L for L in labels if L.text == "wa")
    x0, y0, x1, y1 = wa.box
    before = np.asarray(img.convert("L"))[y0:y1, x0:x1].astype(int)
    after = np.asarray(words_only_erased(img, labels).convert("L"))[y0:y1, x0:x1].astype(int)
    assert np.abs(before - after).mean() < 2


def test_ocr_junk_on_the_drawing_is_not_a_label():
    # OCR reads 19.2's great vessels as "UB": every drawn line leaving that "label" got erased as a leader
    from tools.idimg.labels import render_figure, find_labels
    texts = [L.text for L in find_labels(render_figure("19.2"))]
    assert "UB" not in texts and "Mediastinum" in texts and "1st rib" in texts
