"""3.8.3: hand fixes for identification pictures (tools/id-fixes.json, tools/idimg/patch_pics.py)."""
import filecmp
import json
import os

import pytest
from PIL import Image

from idimg import patch_pics

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ID = os.path.join(os.path.dirname(TOOLS), "figs", "id")
NAMES = {k: v["answer"] for k, v in
         json.load(open(os.path.join(TOOLS, "card-ids.json"), encoding="utf-8"))["cards"].items()}
FIXES = patch_pics.load()
CHANGED = [c for c, f in FIXES.items() if f.get("cover") or f.get("spot")]


def test_fix_file_is_valid():
    assert patch_pics.problems(FIXES, NAMES) == []


def test_patched_cards_keep_three_matching_files():
    for c in CHANGED:
        sizes = {Image.open(os.path.join(ID, f"{c}-{k}.{'png' if k == 'm' else 'jpg'}")).size for k in "qma"}
        assert len(sizes) == 1, c


@pytest.mark.parametrize("cid", ["ch7-vert-8", "ch7-skull-29", "ch11-head-16", "ch1-cav-11"])
def test_patching_is_repeatable(cid, tmp_path):
    """Rebuilding from the 3.8.2 originals gives exactly the committed files."""
    patch_pics.ensure_base()
    patch_pics.patch(cid, FIXES[cid], NAMES[cid], out=str(tmp_path))
    for k, ext in (("q", "jpg"), ("m", "png"), ("a", "jpg")):
        assert filecmp.cmp(tmp_path / f"{cid}-{k}.{ext}", os.path.join(ID, f"{cid}-{k}.{ext}"), shallow=False), (cid, k)


def test_reported_cards_are_fixed():
    """The pictures Andrew flagged on his phone (2026-11-25)."""
    assert FIXES["ch7-vert-8"]["cover"] and FIXES["ch7-vert-5"]["cover"]          # Dens, Coccyx labels
    assert FIXES["ch7-skull-22"]["cover"] and FIXES["ch7-skull-29"]["spot"]       # Pterion; Squamous suture
    assert FIXES["ch7-vert-20"]["spot"] and FIXES["ch7-skull-22"]["spot"]         # Anulus fibrosus; Zygomatic arch
