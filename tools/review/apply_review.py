"""Turn Spot Check answers into marker updates.

1. Save the answers: ArtifactData list on collection "reviews" with out_dir=<dir> (one JSON per card).
2. python3 tools/review/apply_review.py <dir>/reviews [--batch hand1] [--dry]

  ok      -> overrides[card]["verified"] = true  (hand point kept, build leaves it alone)
  fix     -> new point = crop box origin + (fx, fy) * box size, from the batch's cards json; marked verified
  remove  -> overrides[card] = {"skip": true, ...}; picture files deleted; build.py then drops it from IDIMG
  skip    -> nothing
Then rebuild the changed cards: python3 tools/idimg/build.py --decks <decks> --cards <ids>
"""
import argparse, glob, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OV = os.path.join(REPO, "tools", "id-overrides.json")
IDS = os.path.join(REPO, "figs", "id")

ap = argparse.ArgumentParser()
ap.add_argument("dir")
ap.add_argument("--batch", default="hand1")
ap.add_argument("--dry", action="store_true")
a = ap.parse_args()
cards = {c["id"]: c for c in json.load(open(os.path.join(HERE, "out", f"cards-{a.batch}.json")))["cards"]}
ov = json.load(open(OV))
touched, counts = [], {"ok": 0, "fix": 0, "remove": 0, "skip": 0}
for path in sorted(glob.glob(os.path.join(a.dir, "**", "*.json"), recursive=True)):
    d = json.load(open(path))
    d = d.get("data", d)
    if d.get("batch") != a.batch or d.get("card") not in cards:
        continue
    cid, v, c = d["card"], d["verdict"], cards[d["card"]]
    counts[v] = counts.get(v, 0) + 1
    o = ov.setdefault(cid, {"fig": c["fig"]})
    if d.get("note"):
        o["note"] = d["note"]
    if v == "ok":
        o["verified"] = True
    elif v == "fix":
        x0, y0, x1, y1 = c["box"]
        o["point"] = [round(x0 + d["fx"] * (x1 - x0)), round(y0 + d["fy"] * (y1 - y0))]
        o["verified"] = True
        touched.append(cid)
    elif v == "remove":
        ov[cid] = {"skip": True, "note": d.get("note") or "removed in Spot Check"}
        if not a.dry:
            for s in ("-q.jpg", "-m.png", "-a.jpg"):
                try: os.remove(os.path.join(IDS, cid + s))
                except OSError: pass
        touched.append(cid)
print(counts, "| to rebuild:", ",".join(touched) or "none")
if not a.dry:
    json.dump(ov, open(OV, "w"), indent=1)
    print("decks:", ",".join(sorted({t.rsplit('-', 1)[0] for t in touched})))
