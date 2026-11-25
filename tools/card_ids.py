"""101% Anatomy card ID lock, v1.0.0 (3.8.1).

Usage: python3 tools/card_ids.py [index.html] [--update]

Without --update: reports how the page's cards differ from tools/card-ids.json (the same check as
tools/tests/test_card_ids.py) and exits 1 if anything moved.
With --update: rewrites tools/card-ids.json from the page. New cards are added, missing IDs are
kept as retired so they are never reused, and answer changes are printed so you can check each one
is the same card (a spelling fix), not a shifted line."""
import functools
import http.server
import json
import os
import sys
import threading

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, "card-ids.json")
LIVE = "() => Object.values(DECKS).flatMap(d => itemsFor(d.id).map(it => [it.id, d.id, it.name]))"


def live_cards(page_file):
    root = os.path.dirname(os.path.abspath(page_file))
    srv = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(type("Q", (http.server.SimpleHTTPRequestHandler,),
                                                 {"log_message": lambda *a: None}), directory=root))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/{os.path.basename(page_file)}")
            rows = pg.evaluate(LIVE)
            b.close()
    finally:
        srv.shutdown()
    out = {}
    for cid, deck, name in rows:   # Organelles and Organelle Functions share one card list
        e = out.setdefault(cid, {"decks": [], "answer": name})
        e["decks"] = sorted(set(e["decks"]) | {deck})
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    page_file = args[0] if args else os.path.join(os.path.dirname(HERE), "index.html")
    live = live_cards(page_file)
    old = {"cards": {}, "retired": {}}
    if os.path.exists(SNAP):
        with open(SNAP, encoding="utf-8") as f:
            old = json.load(f)
    cards, retired = old["cards"], old.get("retired", {})

    new = sorted(c for c in live if c not in cards)
    gone = sorted(c for c in cards if c not in live)
    changed = sorted(c for c in cards if c in live and live[c] != cards[c])
    for c in changed:
        print(f"changed  {c}: {cards[c]['answer']!r} -> {live[c]['answer']!r}")
    for c in gone:
        print(f"retired  {c}: {cards[c]['answer']!r}")
    print(f"{len(live)} cards; {len(new)} new, {len(gone)} retired, {len(changed)} changed")

    if "--update" not in sys.argv:
        sys.exit(1 if (gone or changed or new) else 0)
    for c in gone:
        retired[c] = cards[c]
    out = {"version": "1.0.0",
           "note": "Locked card IDs. Do not edit by hand; see tools/card_ids.py.",
           "cards": dict(sorted(live.items())), "retired": dict(sorted(retired.items()))}
    with open(SNAP, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0, separators=(",", ":"))
        f.write("\n")
    print("wrote", os.path.relpath(SNAP))


if __name__ == "__main__":
    main()
