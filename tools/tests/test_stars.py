"""Deck stars (3.7.0): tiers from the best typed run, shown on tiles and the results page."""

DECK = "ch12-ap"


def set_rounds(page, rounds):
    page.evaluate(
        "([deck, rs]) => { DATA.rounds = rs.map(([c,t]) => ({deck, unit: DECKS[deck].unit,"
        " credit: c, total: t, pct: Math.round(c/t*100), ts: 1})); }", [DECK, rounds])


def test_tier_boundaries(page):
    tier = lambda c, t: page.evaluate("([c,t]) => starTier(c,t)", [c, t])
    assert tier(9, 20) == 0
    assert tier(10, 20) == 1
    assert tier(15.5, 20) == 1      # 77.5%
    assert tier(15.9, 20) == 1      # just under 80%: no rounding up
    assert tier(16, 20) == 2        # exactly 80%
    assert tier(19.5, 20) == 2      # one second try: not 3 stars
    assert tier(20, 20) == 3
    assert tier(0, 0) == 0


def test_starsfor_uses_best_run_and_never_drops(page):
    assert page.evaluate("d => starsFor(d)", DECK) == 0
    set_rounds(page, [(18, 20), (9, 20)])
    assert page.evaluate("d => starsFor(d)", DECK) == 2


def test_mc_never_earns_stars(page):
    page.evaluate("d => { const id = itemsFor(d)[0].id; setStreak(d, id, 5); }", DECK)
    assert page.evaluate("d => starsFor(d)", DECK) == 0


def open_unit(page):
    page.evaluate(f"view={{page:'unit',unit:DECKS[{DECK!r}].unit}};render()")


def test_tile_shows_stars(page):
    set_rounds(page, [(18, 20)])
    open_unit(page)
    label = page.get_attribute(f"[data-deck='{DECK}'] .stars", "aria-label")
    assert label == "2 of 3 stars"


def play_round(page, second_try_on_first=False):
    page.evaluate(f"startRound({DECK!r}, true)")
    n = page.evaluate("round.qs.length")
    for i in range(n):
        if second_try_on_first and i == 0:
            page.evaluate("grade(null)")  # a wrong first try
        page.evaluate("grade({id: round.qs[round.i].st.id, n: '', label: ''})")
        page.evaluate("next()")


def test_perfect_round_earns_three_stars_and_announces(page):
    play_round(page)
    assert page.evaluate("view.page") == "results"
    assert "3 of 3 stars" in page.get_attribute("#starsline .stars", "aria-label")
    assert page.locator("#starsline .earned").count() == 1


def test_no_earned_line_when_stars_already_held(page):
    set_rounds(page, [(20, 20)])
    play_round(page)
    assert page.locator("#starsline .earned").count() == 0


def test_second_try_costs_the_third_star(page):
    play_round(page, second_try_on_first=True)
    assert "2 of 3 stars" in page.get_attribute("#starsline .stars", "aria-label")
