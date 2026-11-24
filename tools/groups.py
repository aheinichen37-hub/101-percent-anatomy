#!/usr/bin/env python3
"""101% Anatomy GROUPS scanner, v1.0.0. Finds multiple-choice questions whose wrong options are weak.

Usage: python3 tools/groups.py [index.html] [--all] [--json] [--apply] [--overrides FILE]

Each card has an answer "group" (a bone, a family such as "suture", or "bones" for whole bones). The app
fills wrong choices from the same group first. This tool loads the page, asks it for groupReport(), and
prints, worst decks first:
  - cards with no group (they get today's behaviour: random same-deck options)
  - groups with fewer than 4 cards (the deck has to top up from other groups)
  - echoes: a word the clue and the right answer share that no other answer has
  - how many grouped cards have 3 same-group wrong options available

Hand fixes: edit tools/groups-overrides.json ({"deck-id|Card name": "group"}), then run with --apply to
write them into the /*GO*/ ... /*END GO*/ block of index.html. Overrides naming a card that no longer
exists are listed under "Stale overrides". For a new course, swap GROUP_HOSTS in index.html and start a
fresh overrides file; nothing else is course-specific.
"""
import argparse, functools, http.server, json, os, re, sys, threading
from playwright.sync_api import sync_playwright

VERSION = "1.0.0"


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def load(page_path, fn):
    """Serve the page's folder, open it, run fn(page) and return its result."""
    root, name = os.path.split(os.path.abspath(page_path))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=root))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/{name}")
            pg.wait_for_timeout(300)
            out = fn(pg)
            b.close()
            if errs:
                raise SystemExit(f"page errors: {errs}")
            return out
    finally:
        srv.shutdown()


def score(d):
    return len(d["ungrouped"]) + 2 * len(d["small"]) + len(d["echo"])


def render(rep, stale, show_all):
    plain = [d for d in rep["decks"] if not d["groups"]]
    decks = sorted([d for d in rep["decks"] if d["groups"]], key=score, reverse=True)
    shown = [d for d in decks if score(d) or show_all]
    if not show_all:
        shown = shown[:15]
    lines = [f"Groups scanner v{VERSION}: {len(rep['decks'])} decks, {sum(d['cards'] for d in rep['decks'])} cards"]
    lines.append(f"{len(plain)} decks have no groups at all (wrong options come from the same deck at random, as before; "
                 f"add overrides only if a deck mixes families): " + (", ".join(d["id"] for d in plain) if show_all else f"{len(plain)} decks, --all lists them"))
    lines.append(f"{len(decks)} decks have groups. Worst first" + ("" if show_all else " (top 15; --all for the rest)") + ":\n")
    for d in shown:
        share = "n/a" if d["sameGroupShare"] is None else f"{round(d['sameGroupShare']*100)}%"
        lines.append(f"{d['id']}  {d['name']}  ({d['cards']} cards, full same-group options: {share})")
        if d["ungrouped"]:
            lines.append(f"    no group ({len(d['ungrouped'])}): " + ", ".join(d["ungrouped"][:8]) + (" ..." if len(d["ungrouped"]) > 8 else ""))
        if d["small"]:
            lines.append("    small groups: " + ", ".join(f"{s['group']} ({s['n']})" for s in d["small"]))
        if d["echo"]:
            lines.append("    echoes: " + "; ".join(f"{e['name']} [{', '.join(e['words'])}]" for e in d["echo"][:5]) + (" ..." if len(d["echo"]) > 5 else ""))
    if stale:
        lines.append("\nStale overrides (no such card): " + ", ".join(stale))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=f"101% Anatomy groups scanner v{VERSION}")
    ap.add_argument("page", nargs="?", default="index.html")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--apply", action="store_true", help="write the overrides file into the page")
    ap.add_argument("--overrides", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "groups-overrides.json"))
    a = ap.parse_args()

    ov = json.load(open(a.overrides)) if os.path.exists(a.overrides) else {}
    if a.apply:
        src = open(a.page).read()
        new, n = re.subn(r"/\*GO\*/.*?/\*END GO\*/", lambda m: "/*GO*/" + json.dumps(ov, sort_keys=True, ensure_ascii=False) + "/*END GO*/", src, flags=re.S)
        if n != 1:
            raise SystemExit("could not find the /*GO*/ ... /*END GO*/ block in the page")
        open(a.page, "w").write(new)
        print(f"applied {len(ov)} overrides to {a.page}")

    def run(pg):
        rep = pg.evaluate("groupReport()")
        keys = pg.evaluate("Object.keys(DECKS).flatMap(d => itemsFor(d).map(i => d + '|' + i.name))")
        return rep, keys

    rep, keys = load(a.page, run)
    stale = sorted(k for k in ov if k not in set(keys))
    print(json.dumps({"decks": rep["decks"], "stale": stale}, indent=1) if a.json else render(rep, stale, a.all))


if __name__ == "__main__":
    main()
