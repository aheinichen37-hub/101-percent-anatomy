"""Write the tips from tools/tips.csv into the card lines in index.html.

A card line is  Answer | alternates | clue | figure | tip  and every field after the
clue is optional, so a card with a tip but no figure gets "-" in the figure slot.
Running this twice changes nothing the second time.
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
INDEX = os.path.join(REPO, "index.html")
TIPS = os.path.join(HERE, "tips.csv")

DECK_RE = re.compile(r'^D\("([^"]+)","[^"]*","[^"]*","[^"]*","([^"]*)",`$')


def read_tips(path=TIPS):
    try:
        with open(path, newline="") as fh:
            return {r["card_id"]: r["tip"].strip()
                    for r in csv.DictReader(fh) if r.get("tip", "").strip()}
    except OSError:
        return {}


def apply(html, tips):
    """The page source with each tip written into its card's fifth field."""
    lines = html.split("\n")
    out = []
    deck = None
    idx = 0
    changed = 0
    for line in lines:
        m = DECK_RE.match(line)
        if m:
            deck, idx = m.group(1), 0
            out.append(line)
            continue
        if deck is None:
            out.append(line)
            continue
        if line.strip() == "`);":
            deck = None
            out.append(line)
            continue
        if not line.strip():
            out.append(line)
            continue

        card_id = f"{deck}-{idx}"
        idx += 1
        tip = tips.get(card_id)
        if tip is None:
            out.append(line)
            continue

        parts = [p.strip() for p in line.split("|")]
        while len(parts) < 4:
            parts.append("")
        if not parts[3]:
            parts[3] = "-"            # the figure slot has to hold something
        parts = parts[:4] + [tip]
        new = " | ".join(parts)
        changed += new != line
        out.append(new)
    return "\n".join(out), changed


def main():
    tips = read_tips()
    if not tips:
        print("no tips in tools/tips.csv")
        return 0
    with open(INDEX) as fh:
        html = fh.read()
    new, changed = apply(html, tips)
    if new != html:
        with open(INDEX, "w") as fh:
            fh.write(new)
    print(f"{len(tips)} tips in the file, {changed} card line(s) updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
