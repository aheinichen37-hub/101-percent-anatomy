"""Render every card listed in cards3d.SPECS from BodyParts3D and register it in the app.

    python3 tools/anat3d/build3d.py --data /path/to/BodyParts3D/assets/BodyParts3D_data [--decks a,b] [--cards id,id] [--jobs 2] [--no-register]
"""
import argparse, json, multiprocessing as mp, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)
REPO = os.path.dirname(TOOLS)
OUT = os.path.join(REPO, "figs", "id")
REPORT = os.path.join(HERE, "report3d.json")

_scene = None


def _init(data):
    global _scene
    from anat3d.pipeline import Scene
    _scene = Scene(data)


def _work(job):
    from anat3d.pipeline import render_card
    cid, name, regexes, tside, cside, muscles = job
    sc = _scene
    pool = set(sc.bones) | set(sc.muscles)
    target = [b for b in pool if any(re.fullmatch(r, sc.names[b]) for r in regexes)]
    if tside == "R":
        target = [b for b in target if sc.side(b) != "L"]
    if not target:
        return cid, {"status": "fail", "reason": "no structures matched"}
    t = time.time()
    try:
        r = render_card(sc, sorted(target), name, os.path.join(OUT, cid), muscles, cside)
    except Exception as e:  # one card must not stop the batch
        r = {"status": "fail", "reason": f"{type(e).__name__}: {e}"}
    r["n_mesh"] = len(target)
    r["secs"] = round(time.time() - t, 1)
    return cid, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--decks")
    ap.add_argument("--cards")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--no-register", action="store_true")
    a = ap.parse_args()
    from anat3d.cards3d import SPECS
    from idimg import build
    cards = build.read_cards()
    jobs = []
    for c in cards:
        sp = SPECS.get(c["deck"])
        if not sp or c["name"] not in sp["cards"]:
            continue
        if a.decks and c["deck"] not in a.decks.split(","):
            continue
        if a.cards and c["card"] not in a.cards.split(","):
            continue
        jobs.append((c["card"], c["name"], sp["cards"][c["name"]], sp["target"], sp["ctx"], sp["muscles"]))
    print(len(jobs), "cards", flush=True)
    os.makedirs(OUT, exist_ok=True)
    try:
        report = json.load(open(REPORT))
    except (OSError, ValueError):
        report = {}
    with mp.Pool(a.jobs, initializer=_init, initargs=(a.data,)) as pool:
        for i, (cid, r) in enumerate(pool.imap_unordered(_work, jobs), 1):
            report[cid] = r
            print(f"{i}/{len(jobs)} {cid} {r.get('status')} {r.get('view','')} {r.get('reason','')} {r.get('secs','')}s", flush=True)
            json.dump(report, open(REPORT, "w"), indent=1, sort_keys=True)
    if not a.no_register:
        html = open(os.path.join(REPO, "index.html"), encoding="utf-8").read()
        m = re.search(r"const IDIMG=new Set\(\[([^\]]*)\]\);", html)
        have = set(json.loads("[" + m.group(1) + "]")) if m.group(1).strip() else set()
        have |= {c for c, r in report.items() if r.get("status") == "ok"}
        html = build.set_idimg(html, have)
        open(os.path.join(REPO, "index.html"), "w", encoding="utf-8").write(html)
        print("registered", len(have))
    bad = [(c, r.get("reason")) for c, r in report.items() if r.get("status") != "ok"]
    print("failed:", bad)


if __name__ == "__main__":
    main()
