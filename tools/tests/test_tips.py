"""Task 6: tips are written into the card lines, and they follow the rules."""
import re

import apply_tips

MAX_LEN = 220


def test_apply_writes_the_fifth_field_and_is_idempotent():
    html = 'D("d1","ch1","N","q","-",`\nAlpha |  | A clue. | 1.12\nBeta | b | Another clue.\n`);\n'
    once, changed = apply_tips.apply(html, {"d1-0": "First tip.", "d1-1": "Second tip."})
    assert changed == 2
    assert "Alpha |  | A clue. | 1.12 | First tip." in once
    assert "Beta | b | Another clue. | - | Second tip." in once   # figure slot padded
    twice, changed_again = apply_tips.apply(once, {"d1-0": "First tip.", "d1-1": "Second tip."})
    assert twice == once and changed_again == 0


def test_apply_leaves_cards_without_a_tip_alone():
    html = 'D("d1","ch1","N","q","-",`\nAlpha |  | A clue. | 1.12\nBeta | b | Another clue.\n`);\n'
    out, _ = apply_tips.apply(html, {"d1-1": "Only this one."})
    assert "Alpha |  | A clue. | 1.12\n" in out


def test_tip_rules():
    tips = apply_tips.read_tips()
    for card_id, tip in tips.items():
        assert len(tip) <= MAX_LEN, f"{card_id}: {len(tip)} characters"
        assert "|" not in tip and "`" not in tip, f"{card_id}: illegal character"
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", tip.strip()) if s]
        assert len(sentences) <= 2, f"{card_id}: {len(sentences)} sentences"


def test_tips_belong_to_identification_cards(page):
    tips = apply_tips.read_tips()
    if not tips:
        return
    known = page.evaluate("""() => {
        const out = {};
        for (const id of IDDECKS) {
            const d = DECKS[id];
            if (d) for (const it of d.items) out[it.id] = it.name;
        }
        return out;
    }""")
    import csv
    rows = {r["card_id"]: r for r in csv.DictReader(open(apply_tips.TIPS, newline=""))}
    for card_id, tip in tips.items():
        assert card_id in known, f"{card_id} is not a card in an identification deck"
        answer = known[card_id]
        # the answer column must name the card it is filed under, or the tip lands on
        # the wrong structure and teaches the wrong thing
        assert rows[card_id]["answer"].strip().lower() == answer.lower(), (
            f"{card_id}: tip is filed under {rows[card_id]['answer']!r} "
            f"but that card is {answer!r}")
        assert answer.lower() not in tip.lower(), f"{card_id}: the tip gives the answer away"
