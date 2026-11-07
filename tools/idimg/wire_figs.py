"""Set the figure field (4th field) of cards in index.html from a {card-id: figure} map.

Usage: python3 tools/idimg/wire_figs.py tools/idimg/wire-3.2.json
Only fills cards whose figure is empty or "-". Checks the card's name first, so a changed
deck can never be edited by position alone.
"""
import json, re, sys
REPO = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
path = REPO + "/index.html"
html = open(path, encoding="utf-8").read()
spec = json.load(open(sys.argv[1]))
names = spec.pop("_names", {})
changed = skipped = 0
by_deck = {}
for cid, fig in spec.items():
    deck, idx = cid.rsplit("-", 1); by_deck.setdefault(deck, {})[int(idx)] = fig
for deck, cards in by_deck.items():
    m = re.search(r'D\("%s","[^"]*","[^"]*","[^"]*","[^"]*",`\n(.*?)\n`\)' % re.escape(deck), html, re.S)
    if not m: raise SystemExit(f"deck {deck} not found")
    lines = m.group(1).split("\n")
    live = [i for i, l in enumerate(lines) if l.strip()]
    for idx, fig in cards.items():
        li = live[idx]; parts = [p.strip() for p in lines[li].split("|")]
        want = names.get(f"{deck}-{idx}")
        if want and parts[0] != want: raise SystemExit(f"{deck}-{idx}: expected {want!r}, found {parts[0]!r}")
        while len(parts) < 4: parts.append("")
        if parts[3] not in ("", "-"): skipped += 1; print("keeps existing fig:", deck, idx, parts[0], parts[3]); continue
        parts[3] = fig
        lines[li] = " | ".join(parts)   # keeps the tip (5th field) if there is one
        changed += 1
    html = html[:m.start(1)] + "\n".join(lines) + html[m.end(1):]
open(path, "w", encoding="utf-8").write(html)
print("cards wired:", changed, " left alone:", skipped)
