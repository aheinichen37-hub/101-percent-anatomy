"""Task 4: the build runner, its overrides, and the picture check."""
import json
import os

import numpy as np
import pytest
from PIL import Image

import check_id_images
from idimg import build, figures

needs_pdf = pytest.mark.skipif(not figures.pdf_available(),
                               reason="source PDF not staged in this session")


@pytest.fixture
def a_card(page):
    """Reuse the suite's browser: a second sync Playwright cannot start inside it."""
    cards = build.read_cards(["ch11-abd"], page=page)
    assert cards, "no cards in ch11-abd"
    return cards[0]


def test_set_idimg_replaces_the_registry():
    html = 'x\nconst IDIMG=new Set([]);\ny'
    out = build.set_idimg(html, ["b-2", "a-1"])
    assert 'const IDIMG=new Set(["a-1","b-2"]);' in out
    assert check_id_images.registered_ids(out) == ["a-1", "b-2"]
    assert check_id_images.registered_ids(build.set_idimg(out, [])) == []


@needs_pdf
def test_override_skip(a_card):
    row = build.build_card(a_card, {"skip": True})
    assert row["status"] == "skip"
    assert not os.path.exists(os.path.join(build.OUT_DIR, a_card["card"] + "-q.jpg")) \
        or row["kind"] is None


@needs_pdf
def test_override_kind(a_card):
    row = build.build_card(a_card, {"kind": "circle"})
    assert row["status"] == "ok"
    assert row["kind"] == "circle"


def test_check_detects_blank(tmp_path):
    cid = "blank-0"
    Image.new("RGB", (1000, 600), "white").save(tmp_path / f"{cid}-q.jpg")
    Image.new("RGBA", (1000, 600), (79, 212, 255, 255)).save(tmp_path / f"{cid}-m.png")
    Image.new("RGB", (1000, 600), "white").save(tmp_path / f"{cid}-a.jpg")
    problems = check_id_images.check([cid], id_dir=str(tmp_path))
    assert problems and "blank" in problems[0]


def test_check_detects_missing_and_empty_mask(tmp_path):
    noise = (np.random.default_rng(0).integers(0, 255, (300, 300, 3))).astype("uint8")
    Image.fromarray(noise).save(tmp_path / "c-0-q.jpg")
    Image.new("RGBA", (300, 300), (0, 0, 0, 0)).save(tmp_path / "c-0-m.png")
    Image.fromarray(noise).save(tmp_path / "c-0-a.jpg")
    assert any("marks nothing" in p for p in
               check_id_images.check(["c-0"], id_dir=str(tmp_path)))
    assert any("missing" in p for p in
               check_id_images.check(["gone-1"], id_dir=str(tmp_path)))


# ---- hand fixes: a card can borrow another figure and be pointed at by eye ----

def test_window_box_stays_inside_the_figure_and_around_the_spot():
    box = build.window_box((1000, 800), (30, 790))
    assert 0 <= box[0] < box[2] <= 1000 and 0 <= box[1] < box[3] <= 800
    assert box[0] <= 30 < box[2] and box[1] <= 790 < box[3]


def test_hand_overrides_name_real_cards_and_spots_inside_the_figure(page):
    overrides = build.load_overrides()
    ids = {c["card"] for c in build.read_cards(page=page)}
    for card, o in overrides.items():
        assert card in ids, f"override for unknown card {card}"
        if "point" in o:
            assert len(o["point"]) == 2 and all(v >= 0 for v in o["point"]), card
            assert o.get("fig"), f"{card}: a hand spot is only meaningful with its figure"
