"""For cards whose own figure has no usable drawing, find another figure that does.

Tries each candidate drawing in turn, with the card's own figure first, and keeps the first
one that yields a picture. The result goes to tools/id-overrides.json as a `fig` entry, so
it is a starting point to review, not a verdict.
"""
import functools, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from idimg import build, figures, labels as L  # noqa: E402

TABLES = {"11.24", "11.26", "11.27", "11.30", "11.31", "11.33"}   # lists of muscles, not drawings


_orig_render = figures.render_figure
_orig_find = L.find_labels
_orig_match = L.match_label


@functools.lru_cache(maxsize=None)
def _cached(fig):
    try:
        return _orig_render(fig, scale=3.0)
    except (KeyError, ValueError):
        return figures.stored_figure(fig)


def _render(fig, scale=3.0):
    return _cached(fig)


@functools.lru_cache(maxsize=None)
def _labels(fig):
    return _orig_find(_render(fig))


def main(deck_ids, candidates):
    figures.render_figure = _render
    # Across figures only an exact or near-exact name counts: a loose prefix match is fine
    # inside the card's own figure and a trap among a dozen others.
    build.labels_mod.match_label = lambda labs, terms: _orig_match(labs, terms, partial_ok=False)
    L_find = _orig_find
    L.find_labels = lambda img: _labels_by_img(img)
    by_id = {id(_render(f)): f for f in candidates}

    def _labels_by_img(img):
        return _labels(by_id[id(img)]) if id(img) in by_id else L_find(img)

    overrides = build.load_overrides()
    report = json.load(open(build.REPORT))
    found = {}
    for card in build.read_cards(deck_ids):
        if report.get(card["card"], {}).get("status") == "ok" or card["card"] in overrides:
            continue
        order = ([card["fig"]] if card["fig"] in candidates else []) + \
                [f for f in candidates if f != card["fig"]]
        for fig in order:
            row = build.build_card(card, {"fig": fig})
            if row["status"] == "ok":
                found[card["card"]] = {"fig": fig}
                report[card["card"]] = row
                print("ok", card["card"], card["name"], "->", fig, flush=True)
                break
    json.dump(found, open(os.path.join(os.path.dirname(build.OVERRIDES), "id-overrides.suggested.json"), "w"), indent=1, sort_keys=True)
    print(len(found), "cards found a drawing")


if __name__ == "__main__":
    decks = sys.argv[1].split(",")
    cands = [f for f in sys.argv[2].split(",") if f not in TABLES]
    main(decks, cands)
