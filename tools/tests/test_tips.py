"""Task 6: tips live in tools/tips.csv and are written into the cards' fifth field by tools/apply_tips.py."""
import csv
import re
import shutil
import subprocess
import sys

from .conftest import ROOT

CSV = ROOT / "tools" / "tips.csv"


def rows():
    with open(CSV, newline="") as f:
        return list(csv.DictReader(f))


def test_apply_idempotent(tmp_path):
    html = tmp_path / "index.html"
    shutil.copy(ROOT / "index.html", html)
    run = [sys.executable, str(ROOT / "tools" / "apply_tips.py"), "--html", str(html), "--csv", str(CSV)]
    subprocess.run(run, check=True)
    once = html.read_bytes()
    subprocess.run(run, check=True)
    assert html.read_bytes() == once
    # every tip landed on its card
    sys.path.insert(0, str(ROOT))
    from tools.idimg.build import DECK_RE
    lines = {}
    for m in DECK_RE.finditer(html.read_text()):
        did, _, _, body = m.groups()
        for i, ln in enumerate(body.strip().split("\n")):
            lines[f"{did}-{i}"] = [x.strip() for x in ln.split("|")]
    for r in rows():
        p = lines[r["card_id"]]
        assert len(p) == 5 and p[4] == r["tip"] and p[0] == r["answer"]


def test_tip_rules():
    sys.path.insert(0, str(ROOT))
    from tools.idimg.build import id_decks
    ident = set(id_decks(ROOT / "index.html"))
    rs = rows()
    assert rs, "tips.csv is empty"
    for r in rs:
        t = r["tip"]
        assert len(t) <= 220, r["card_id"]
        assert len(re.findall(r"[.!?](\s|$)", t)) <= 2, r["card_id"]
        assert "|" not in t and "`" not in t, r["card_id"]
        assert r["deck"] in ident and r["card_id"].startswith(r["deck"] + "-"), r["card_id"]


def test_no_answer_in_tip():
    for r in rows():
        assert r["answer"].lower() not in r["tip"].lower(), r["card_id"]
