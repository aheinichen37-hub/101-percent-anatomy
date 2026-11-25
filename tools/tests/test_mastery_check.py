"""Unit mastery check (3.8.0): unlock at 2 stars per deck, 50 random cards, gold / diamond / ruby."""

BIG, SMALL = "ch11", "ch15"      # 148 cards over 12 decks, 37 cards over 3 decks


def give_stars(page, unit, credit, total=10, only=None):
    page.evaluate("""([u, c, t, only]) => {
        const ds = unitDecks(u).filter(d => !only || only.includes(d));
        DATA.rounds = DATA.rounds.filter(r => r.kind === 'check')
          .concat(ds.map(d => ({deck: d, unit: u, credit: c, total: t, pct: c / t * 100, ts: 1})));
    }""", [unit, credit, total, only])


def open_unit(page, unit):
    page.evaluate(f"view={{page:'unit',unit:{unit!r}}};render()")


def run_check(page, unit, second_tries=0, misses=0):
    """Play a whole check, typing real answers, with some cards answered badly."""
    page.evaluate(f"startCheck({unit!r})")
    n = page.evaluate("round.qs.length")
    for i in range(n):
        if i < misses:
            page.evaluate("giveUp()")
        else:
            if i < misses + second_tries:
                page.evaluate("grade(null)")          # wrong first try
            page.evaluate("submit(round.qs[round.i].st.name)")   # real typing path, own deck's vocabulary
        page.evaluate("next()")
    return n


def test_locked_until_every_deck_has_two_stars(page):
    open_unit(page, SMALL)
    assert page.locator("#startcheck").is_disabled()
    give_stars(page, SMALL, 10, only=[page.evaluate("unitDecks('ch15')[0]")])
    page.evaluate("render()")
    assert page.locator("#startcheck").is_disabled()
    assert "1 of 3" in page.inner_text("#checkblock")
    give_stars(page, SMALL, 8)                     # 80% = 2 stars on every deck
    page.evaluate("render()")
    assert not page.locator("#startcheck").is_disabled()


def test_start_refused_while_locked(page):
    page.evaluate("startCheck('ch15')")
    assert page.evaluate("view.page") == "lobby"


def test_big_unit_gets_50_cards_from_several_decks(page):
    give_stars(page, BIG, 8)
    page.evaluate("startCheck('ch11')")
    assert page.evaluate("round.qs.length") == 50
    assert page.evaluate("new Set(round.qs.map(q => q.deck)).size") > 1


def test_small_unit_uses_every_card(page):
    give_stars(page, SMALL, 8)
    page.evaluate("startCheck('ch15')")
    assert page.evaluate("round.qs.length") == 37
    assert page.evaluate("new Set(round.qs.map(q => q.st.id)).size") == 37


def test_perfect_check_is_diamond_and_typed_answers_use_their_own_deck(page):
    give_stars(page, SMALL, 8)
    run_check(page, SMALL)
    assert page.evaluate("view.page") == "results"
    assert page.evaluate("round.credit") == page.evaluate("round.qs.length")
    assert page.evaluate("unitTier('ch15')") == "diamond"
    assert page.locator(".tier-diamond").count() == 1


def test_ruby_needs_three_stars_on_every_deck(page):
    give_stars(page, SMALL, 10)                    # 3 stars everywhere
    run_check(page, SMALL)
    assert page.evaluate("unitTier('ch15')") == "ruby"


def test_gold_boundary_is_95_percent(page):
    give_stars(page, BIG, 8)
    run_check(page, BIG, second_tries=5)           # 47.5 of 50 = 95%
    assert page.evaluate("round.result.grade") == "gold"
    assert page.evaluate("unitTier('ch11')") == "gold"
    give_stars(page, BIG, 8)
    run_check(page, BIG, second_tries=6)           # 47 of 50 = 94%
    assert page.evaluate("round.result.grade") == "none"


def test_worse_retake_never_lowers_best_and_checks_stay_out_of_deck_stats(page):
    give_stars(page, SMALL, 8)
    run_check(page, SMALL)
    run_check(page, SMALL, misses=20)
    assert page.evaluate("Math.round(checkBest('ch15').credit / checkBest('ch15').total * 100)") == 100
    assert page.evaluate("statsFor(r => r.unit === 'ch15').rounds") == 3   # only the 3 deck rounds
    assert page.evaluate("unitDecks('ch15').every(d => starsFor(d) === 2)")


def test_unit_page_shows_best_and_lobby_tile_shows_badge(page):
    give_stars(page, SMALL, 8)
    run_check(page, SMALL)
    open_unit(page, SMALL)
    assert "Best 100%" in page.inner_text("#checkblock").replace("\n", " ")
    page.evaluate("view={page:'lobby'};render()")
    assert page.locator("[data-unit='ch15'] .tier-diamond").count() == 1
