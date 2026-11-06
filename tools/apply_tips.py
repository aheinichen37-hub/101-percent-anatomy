"""Write each tip in tools/tips.csv into its card's fifth field in index.html.

    python3 tools/apply_tips.py [--html index.html] [--csv tools/tips.csv]

Card lines are `Answer | alternates | clue | figure | tip`. An empty figure becomes `-` so the tip lands in field 5.
Cards not in the CSV are never touched; running it twice changes nothing the second time.
"""
import argparse
import csv
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.idimg.build import DECK_RE  # noqa: E402


def apply(html: pathlib.Path, tips_csv: pathlib.Path) -> int:
    with open(tips_csv, newline="") as f:
        tips = {r["card_id"]: r["tip"].strip() for r in csv.DictReader(f)}
    s = html.read_text()
    out, last, changed = [], 0, 0
    for m in DECK_RE.finditer(s):
        did = m.group(1)
        b0, b1 = m.span(4)
        body = s[b0:b1]
        lines = body.split("\n")
        idx = -1
        for k, ln in enumerate(lines):
            if idx < 0 and not ln.strip():
                continue  # numbered like the app: from the first card line, blank lines included
            idx += 1
            if not ln.strip():
                continue
            cid = f"{did}-{idx}"
            if cid not in tips:
                continue
            lead = ln[:len(ln) - len(ln.lstrip())]
            p = [x.strip() for x in ln.strip().split("|")]
            p += [""] * (4 - len(p))
            p = p[:4]
            p[3] = p[3] or "-"
            new = lead + " | ".join(p + [tips[cid]])
            if new != ln:
                lines[k] = new
                changed += 1
        out.append(s[last:b0])
        out.append("\n".join(lines))
        last = b1
    out.append(s[last:])
    html.write_text("".join(out))
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(ROOT / "index.html"))
    ap.add_argument("--csv", default=str(ROOT / "tools" / "tips.csv"))
    a = ap.parse_args()
    print(apply(pathlib.Path(a.html), pathlib.Path(a.csv)), "card lines updated")


if __name__ == "__main__":
    main()
