import json
import pathlib
import shutil
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture
def site(tmp_path):
    """A scratch copy of the app so builds never touch the real index.html or figs/."""
    shutil.copy(ROOT / "index.html", tmp_path / "index.html")
    (tmp_path / "figs" / "id").mkdir(parents=True)
    return tmp_path


def _run(site, overrides, only):
    from tools.idimg.build import build
    ov = site / "overrides.json"
    ov.write_text(json.dumps(overrides))
    return build(decks=["ch11-abd"], only=only, html=site / "index.html", outdir=site / "figs" / "id",
                 overrides=ov, report=site / "report.json", fullfigs=site / "figs")


def _idimg(site):
    import re
    m = re.search(r"const IDIMG=new Map\((\[.*?\])\);", (site / "index.html").read_text(), re.S)
    return {cid for cid, _ in json.loads(m.group(1))}


def test_load_cards_reads_ids_and_figures():
    from tools.idimg.build import load_cards
    cards = {c.id: c for c in load_cards(ROOT / "index.html", ["ch11-abd"])}
    assert cards["ch11-abd-0"].answer == "Rectus abdominis"
    assert cards["ch11-abd-0"].fig == "11.16"


def test_build_writes_three_files(site):
    rep = _run(site, {}, ["ch11-abd-0"])
    assert rep["ch11-abd-0"]["status"] == "ok"
    for suffix in ("-q.jpg", "-m.png", "-a.jpg"):
        assert (site / "figs" / "id" / f"ch11-abd-0{suffix}").exists()
    assert "ch11-abd-0" in _idimg(site)


def test_override_skip(site):
    rep = _run(site, {"ch11-abd-0": {"skip": True}}, ["ch11-abd-0"])
    assert rep["ch11-abd-0"]["status"] == "skip"
    assert "ch11-abd-0" not in _idimg(site)


def test_override_kind(site):
    rep = _run(site, {"ch11-abd-0": {"kind": "circle"}}, ["ch11-abd-0"])
    assert rep["ch11-abd-0"]["kind"] == "circle"


def test_override_point_moves_highlight(site):
    rep = _run(site, {"ch11-abd-0": {"point": [700, 500], "kind": "circle"}}, ["ch11-abd-0"])
    assert rep["ch11-abd-0"]["point"] == [700, 500]


def test_check_detects_blank(site):
    Image.new("RGB", (1000, 600), "white").save(site / "figs" / "id" / "x-1-q.jpg")
    Image.new("RGBA", (1000, 600), (79, 212, 255, 255)).save(site / "figs" / "id" / "x-1-m.png")
    Image.new("RGB", (1000, 600), "white").save(site / "figs" / "id" / "x-1-a.jpg")
    html = (site / "index.html").read_text().replace("const IDIMG=new Map([", 'const IDIMG=new Map([["x-1","1.1"]', 1)
    (site / "index.html").write_text(html)
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "check_id_images.py"), "--html", str(site / "index.html"),
                        "--figs", str(site / "figs" / "id")], capture_output=True, text=True)
    assert r.returncode == 1


def test_check_passes_good_build(site):
    _run(site, {}, ["ch11-abd-0"])
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "check_id_images.py"), "--html", str(site / "index.html"),
                        "--figs", str(site / "figs" / "id")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_sheets_written(site):
    from tools.idimg.sheets import deck_sheet, figure_grid
    _run(site, {}, ["ch11-abd-0"])
    out = deck_sheet("ch11-abd", html=site / "index.html", figs=site / "figs" / "id", report=site / "report.json",
                     outdir=site / "sheets")
    assert out.exists() and Image.open(out).size[0] > 400
    g = figure_grid("11.16", outdir=site / "sheets")
    assert g.exists()


def _run_deck(site, deck, only):
    from tools.idimg.build import build
    ov = site / "overrides.json"
    ov.write_text("{}")
    return build(decks=[deck], only=only, html=site / "index.html", outdir=site / "figs" / "id",
                 overrides=ov, report=site / "report.json", fullfigs=site / "figs")


def _idimg_map(site):
    import re
    m = re.search(r"const IDIMG=new Map\((\[.*?\])\);", (site / "index.html").read_text(), re.S)
    return dict(json.loads(m.group(1)))


def test_finds_a_figure_that_labels_the_structure(site):
    # Left atrium's textbook figure (19.13) doesn't label it; 19.9 does
    rep = _run_deck(site, "ch19-anat", ["ch19-anat-8"])
    assert rep["ch19-anat-8"]["status"] == "ok"
    assert rep["ch19-anat-8"]["fig"] != "19.13"
    assert _idimg_map(site)["ch19-anat-8"] == rep["ch19-anat-8"]["fig"]


def test_card_without_figure_gets_one(site):
    rep = _run_deck(site, "ch19-anat", ["ch19-anat-24"])  # Fossa ovalis has no textbook figure
    assert rep["ch19-anat-24"]["status"] == "ok"
    assert (site / "figs" / f"{rep['ch19-anat-24']['fig']}.jpg").exists()  # tap-to-enlarge target exists


@pytest.fixture(scope="module")
def ulna(tmp_path_factory):
    """Ulna (ch8-arm-10) comes from Figure 8.6, outline-drawn forearm bones in two views side by side."""
    from tools.idimg.build import build
    site = tmp_path_factory.mktemp("ulna")
    shutil.copy(ROOT / "index.html", site / "index.html")
    (site / "figs" / "id").mkdir(parents=True)
    (site / "overrides.json").write_text("{}")
    rep = build(decks=["ch8-arm"], only=["ch8-arm-10"], html=site / "index.html", outdir=site / "figs" / "id",
                overrides=site / "overrides.json", report=site / "report.json", fullfigs=site / "figs")
    return site, rep["ch8-arm-10"]


def test_line_art_glows_the_leader(ulna):
    site, r = ulna
    assert r["status"] == "ok" and r["kind"] == "leader"


def test_line_art_crop_is_one_whole_view(ulna):
    from tools.idimg.labels import render_figure
    site, r = ulna
    W, H = render_figure(r["fig"]).size
    x0, y0, x1, y1 = r["crop"]
    assert x1 - x0 < 0.6 * W          # one view, not both
    assert y1 - y0 > 0.6 * H          # the whole bone, not a strip
    px, py = r["point"]
    assert x0 <= px <= x1 and y0 <= py <= y1


def test_line_art_outlines_intact(ulna):
    # only label words are erased: the bones' outlines and the leader lines all survive
    from tools.idimg.build import _figure
    from tools.idimg.panel import _text_mask
    site, r = ulna
    img, labels, _ = _figure(r["fig"])
    x0, y0, x1, y1 = r["crop"]
    orig = np.asarray(img.convert("L"))[y0:y1, x0:x1]
    notext = _text_mask(img, labels, pad=8)[y0:y1, x0:x1] == 0
    q = np.asarray(Image.open(site / "figs" / "id" / "ch8-arm-10-q.jpg").convert("L").resize((x1 - x0, y1 - y0)))
    before = (orig < 110) & notext
    after = (q < 140) & before
    assert after.sum() >= 0.9 * before.sum()


def test_different_structures_never_share_a_highlight(site):
    # 11.16 colors the obliques and transversus identically: a fill would light all three the same
    only = ["ch11-abd-1", "ch11-abd-2", "ch11-abd-3"]
    rep = _run(site, {}, only)
    full = {}
    for k in only:
        x0, y0, x1, y1 = rep[k]["crop"]
        m = np.asarray(Image.open(site / "figs" / "id" / f"{k}-m.png").resize((x1 - x0, y1 - y0)))[..., 3] > 127
        canvas = np.zeros((3000, 3000), bool)
        canvas[y0:y1, x0:x1] = m
        full[k] = canvas
    for i, a in enumerate(only):
        for b in only[i + 1:]:
            iou = (full[a] & full[b]).sum() / max((full[a] | full[b]).sum(), 1)
            assert iou < 0.5, (a, b, rep[a]["kind"], rep[b]["kind"])


def test_line_art_crop_is_one_view_with_its_label(tmp_path):
    # 8.5 draws the humerus twice (anterior, posterior) plus a skeleton key: Greater tubercle gets one humerus
    from tools.idimg.build import build
    from tools.idimg.labels import render_figure
    shutil.copy(ROOT / "index.html", tmp_path / "index.html")
    (tmp_path / "figs" / "id").mkdir(parents=True)
    (tmp_path / "overrides.json").write_text("{}")
    rep = build(decks=["ch8-arm"], only=["ch8-arm-2", "ch8-arm-13"], html=tmp_path / "index.html",
                outdir=tmp_path / "figs" / "id", overrides=tmp_path / "overrides.json", report=tmp_path / "report.json",
                fullfigs=tmp_path / "figs")
    W, H = render_figure("8.5").size
    x0, y0, x1, y1 = rep["ch8-arm-2"]["crop"]
    assert x1 - x0 < 0.6 * W and y0 > 150          # one humerus, without the skeleton key above it
    # Coronoid process's label sits right of the forearm: the crop keeps the whole label slot for the name
    x0, y0, x1, y1 = rep["ch8-arm-13"]["crop"]
    assert x1 >= 450


def test_line_art_point_override_keeps_the_leader_glow(tmp_path):
    # the tracer overshoots Interosseous membrane's leader; a corrected tip still glows the leader, now ending there
    from tools.idimg.build import build
    shutil.copy(ROOT / "index.html", tmp_path / "index.html")
    (tmp_path / "figs" / "id").mkdir(parents=True)
    (tmp_path / "overrides.json").write_text(json.dumps({"ch8-arm-18": {"point": [224, 566], "fig": "8.6"}}))
    rep = build(decks=["ch8-arm"], only=["ch8-arm-18"], html=tmp_path / "index.html", outdir=tmp_path / "figs" / "id",
                overrides=tmp_path / "overrides.json", report=tmp_path / "report.json", fullfigs=tmp_path / "figs")
    r = rep["ch8-arm-18"]
    assert r["status"] == "ok" and r["kind"] == "leader" and r["point"] == [224, 566]
    x0, y0, x1, y1 = r["crop"]
    m = np.asarray(Image.open(tmp_path / "figs" / "id" / "ch8-arm-18-m.png").resize((x1 - x0, y1 - y0)))[..., 3]
    tx, ty = 224 - x0, 566 - y0
    assert m[ty - 22:ty + 23, tx - 22:tx + 23].max() > 127      # the ring sits on the corrected tip
