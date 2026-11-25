"""3.8.2: results screens lead back to the deck's unit; a wrong number never gets "Did you mean"."""
import pytest


def _results(page, deck, method):
    page.evaluate("""([d, m]) => { m === 'mc' ? startMC(d, false) : startRound(d, false);
        round.i = round.qs.length - 1; finish(); }""", [deck, method])


@pytest.mark.parametrize("method", ["typed", "mc"])
def test_results_go_back_to_the_unit(page, method):
    _results(page, "ch7-skull", method)
    assert page.locator("#tolobby").inner_text() == "Back to the unit"
    page.click("#tolobby")
    assert page.evaluate("view.page") == "unit"
    assert page.evaluate("view.unit") == page.evaluate("DECKS['ch7-skull'].unit")


@pytest.mark.parametrize("deck,typed", [
    ("ch7-thor", "13"),            # 12 pairs of ribs
    ("ch6-cls", "205"),            # 206 bones
    ("ch18-rbc", "12 days"),       # 120 days
    ("ch3-ps", "47"),              # 46 chromosomes
    ("ch17-panc", "Type 3 diabetes"),
])
def test_wrong_number_gets_no_suggestion(page, deck, typed):
    assert page.evaluate("([r, d]) => classify(r, d).kind", [typed, deck]) == "unknown"


@pytest.mark.parametrize("deck,typed,want", [
    ("ch7-thor", "12", "answer"),
    ("ch7-thor", "twelv", "suggest"),          # a spelled-out number still gets spelling help
    ("u1-mit", "G1 phse", "suggest"),          # right number, a slipped letter
    ("ch17-panc", "Type 1 diabetis", "suggest"),
])
def test_number_answers_still_match(page, deck, typed, want):
    assert page.evaluate("([r, d]) => classify(r, d).kind", [typed, deck]) == want
