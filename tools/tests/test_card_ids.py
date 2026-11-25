"""3.8.1: card IDs are locked. Saved progress (multiple-choice streaks now, card memory from 3.9.0),
tips and picture overrides all key on a card's ID, and most IDs are a deck line's position
("ch8-arm-3"). This test fails when an ID disappears or starts pointing at a different answer,
which is what inserting, deleting or reordering a deck line does.

Rules: add new cards at the end of a deck; retire a card by starting its line with "~" (its slot
keeps its number); after a real answer edit or a new card, run `python3 tools/card_ids.py --update`
and check the summary it prints."""
import json
import os

SNAP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "card-ids.json")
LIVE = "() => Object.values(DECKS).flatMap(d => itemsFor(d.id).map(it => [it.id, d.id, it.name]))"


def _live(page):
    """{cardId: (decks sorted, answer)}. Two Unit 3 decks share one card list on purpose
    (Organelles and Organelle Functions), so a card can sit in more than one deck."""
    out = {}
    for cid, deck, name in page.evaluate(LIVE):
        decks, _ = out.get(cid, ((), name))
        out[cid] = (tuple(sorted(set(decks) | {deck})), name)
    return out


def _snap():
    with open(SNAP, encoding="utf-8") as f:
        return json.load(f)


def test_no_card_id_moved(page):
    snap = _snap()
    live = _live(page)
    cards, retired = snap["cards"], snap.get("retired", {})

    gone = [c for c in cards if c not in live]
    assert not gone, f"card IDs disappeared (retire a card with '~' instead of deleting its line): {gone[:10]}"

    moved = [f"{c}: was {cards[c]['answer']!r}, now {live[c][1]!r}"
             for c in cards if live[c] != (tuple(cards[c]["decks"]), cards[c]["answer"])]
    assert not moved, ("these IDs now point at a different card (a line was inserted or moved?); "
                       "if it is only a spelling fix, run tools/card_ids.py --update:\n" + "\n".join(moved[:10]))

    reused = [c for c in live if c in retired]
    assert not reused, f"retired IDs came back: {reused}"

    new = [c for c in live if c not in cards]
    assert not new, f"new cards are not in tools/card-ids.json yet; run tools/card_ids.py --update: {new[:10]}"


def test_live_ids_are_unique_per_deck(page):
    pairs = [(deck, cid) for cid, deck, _ in page.evaluate(LIVE)]
    assert len(pairs) == len(set(pairs))
    shared = {d for cid, (decks, _) in _live(page).items() if len(decks) > 1 for d in decks}
    assert shared <= {"u1-org", "u1-fn"}, f"a new deck shares card IDs with another: {shared}"


def test_retired_line_keeps_its_slot(page):
    items = page.evaluate(
        """() => D('t-x','ch1','T','q','-', "A | | a\\n~ B | | b\\nC | | c").items.map(i => [i.id, i.name])""")
    assert items == [["t-x-0", "A"], ["t-x-2", "C"]]


def test_fixture_save_cards_all_exist(page):
    """Andrew's real 3.8.0 save: every streak in it still points at a live card."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "save-3.8.0.json")
    with open(path, encoding="utf-8") as f:
        save = json.load(f)
    live = {cid for cid, _, _ in page.evaluate(LIVE)}
    missing = [c for deck in save["mc"].values() for c in deck if c not in live]
    assert not missing
