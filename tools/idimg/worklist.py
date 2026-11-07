"""Triage every identification card into a work lane and write tools/idimg/worklist.csv.

Lanes:
  done        picture built (automatically or from id-overrides.json)
  needs-fig   card has no textbook figure yet (needs a page/diagram supplied)
  locate      figure exists but the build could not find the structure; fix with
              a hand-placed point (and/or a better matcher) in id-overrides.json
Run: python3 tools/idimg/worklist.py
"""
import csv, json, collections, pathlib
root = pathlib.Path(__file__).resolve().parents[2]
rep = json.load(open(root / 'tools/idimg/report.json'))
rows = []
for cid, v in rep.items():
    if v['status'] == 'ok': lane, why = 'done', ''
    elif v['reason'] == 'card has no textbook figure': lane, why = 'needs-fig', 'no figure'
    else: lane, why = 'locate', v['reason']
    rows.append((v['deck'], cid, v.get('fig') or '', lane, why))
rows.sort(key=lambda r: (r[0], int(r[1].rsplit('-', 1)[1])))
with open(root / 'tools/idimg/worklist.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['deck', 'card', 'fig', 'lane', 'why']); w.writerows(rows)
tot = collections.Counter(r[3] for r in rows); print(dict(tot))
deck = collections.defaultdict(collections.Counter)
for r in rows: deck[r[0]][r[3]] += 1
print(f"{'deck':12s} done locate needs-fig")
for d, c in sorted(deck.items(), key=lambda kv: -(kv[1]['locate'] + kv[1]['needs-fig'])):
    print(f"{d:12s} {c['done']:4d} {c['locate']:6d} {c['needs-fig']:8d}")
