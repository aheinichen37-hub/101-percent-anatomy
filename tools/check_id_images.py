"""Exit 0 only if every card in IDIMG has all three pictures, none blank, and a non-empty highlight.

    python3 tools/check_id_images.py [--html index.html] [--figs figs/id]
"""
import argparse
import json
import pathlib
import re
import sys

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
MIN_STD = 12  # a picture with less pixel variation than this is blank


def problems(html, figs):
    m = re.search(r"const IDIMG=new Map\((\[.*?\])\);", pathlib.Path(html).read_text(), re.S)
    ids = [cid for cid, _ in json.loads(m.group(1))] if m else []
    out = []
    for cid in ids:
        q, mk, a = (pathlib.Path(figs) / f"{cid}{s}" for s in ("-q.jpg", "-m.png", "-a.jpg"))
        missing = [p.name for p in (q, mk, a) if not p.exists()]
        if missing:
            out.append(f"{cid}: missing {', '.join(missing)}")
            continue
        for p in (q, a):
            if np.asarray(Image.open(p).convert("L")).std() < MIN_STD:
                out.append(f"{cid}: {p.name} is blank")
        if not (np.asarray(Image.open(mk).convert("RGBA"))[..., 3] > 0).any():
            out.append(f"{cid}: {mk.name} has no highlight")
    return ids, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(ROOT / "index.html"))
    ap.add_argument("--figs", default=str(ROOT / "figs" / "id"))
    a = ap.parse_args()
    ids, bad = problems(a.html, a.figs)
    for b in bad:
        print(b)
    print(f"{len(ids)} cards checked, {len(bad)} problems")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
