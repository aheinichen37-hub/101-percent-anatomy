"""Check every registered identification picture is present and not blank.

Exits 0 only if each card in the app's IDIMG set has all three files, each picture has
some variation in it (a blank crop means the build went wrong), and each mask marks
something.
"""
import json
import os
import re
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
INDEX = os.path.join(REPO, "index.html")
ID_DIR = os.path.join(REPO, "figs", "id")

MIN_STD = 12          # a near-flat picture is a failed crop, not a drawing


def registered_ids(html=None):
    html = html if html is not None else open(INDEX).read()
    m = re.search(r"const IDIMG=new Set\(\[([^\]]*)\]\);", html)
    if not m:
        raise RuntimeError("could not find the IDIMG set in index.html")
    return json.loads("[" + m.group(1) + "]") if m.group(1).strip() else []


def check(card_ids=None, id_dir=ID_DIR):
    problems = []
    for cid in (card_ids if card_ids is not None else registered_ids()):
        base = os.path.join(id_dir, cid)
        q, m, a = base + "-q.jpg", base + "-m.png", base + "-a.jpg"
        missing = [p for p in (q, m, a) if not os.path.exists(p)]
        if missing:
            problems.append(f"{cid}: missing {', '.join(os.path.basename(p) for p in missing)}")
            continue
        std = float(np.array(Image.open(q).convert("L")).std())
        if std < MIN_STD:
            problems.append(f"{cid}: picture is nearly blank (variation {std:.1f})")
        alpha = np.array(Image.open(m).convert("RGBA"))[:, :, 3]
        if not alpha.any():
            problems.append(f"{cid}: highlight marks nothing")
    return problems


def main():
    problems = check()
    total = len(registered_ids())
    if problems:
        print(f"{len(problems)} problem(s) in {total} registered cards:")
        for p in problems[:40]:
            print(" ", p)
        return 1
    print(f"all {total} registered cards have a picture, a highlight and a labelled copy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
