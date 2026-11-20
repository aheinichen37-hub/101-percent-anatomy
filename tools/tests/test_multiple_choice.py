"""v3.5.0: multiple choice study rounds, streaks, readiness bar, save."""
DECK = "ch11-abd"      # an identification deck
PLAIN = "ch12-ap"      # a concept deck (no picture mode)


def mc(page, deck=DECK, images=True):
    page.evaluate(f"startMC({deck!r}, {str(images).lower()})")


def pick(page, right=True):
    page.evaluate(
        "right => { const q = round.qs[round.i]; "
        "pickChoice(q.choices.findIndex(c => c.right === right)); }", right)


def test_how_picker_offers_both_ways(page):
    page.evaluate(f"view={{page:'unit',unit:DECKS['{PLAIN}'].unit}};render()")
    page.click(f'[data-deck="{PLAIN}"]')
    assert page.locator("#how-type").count() == 1 and page.locator("#how-mc").count() == 1
    page.click("#how-mc")
    assert page.evaluate("round.method") == "mc"          # concept deck: straight into the round
    page.evaluate(f"view={{page:'unit',unit:DECKS['{DECK}'].unit}};render()")
    page.click(f'[data-deck="{DECK}"]')
    page.click("#how-mc")
    assert page.locator("#img-on").count() == 1            # picture deck still asks images on/off
    page.click("#img-on")
    assert page.evaluate("round.method") == "mc"


def test_four_choices_one_right_and_keys_work(page):
    mc(page)
    assert page.locator(".choice").count() == 4
    assert page.evaluate("round.qs[round.i].choices.filter(c=>c.right).length") == 1
    assert page.locator("#ans").count() == 0               # no typing bar in a study round
    page.keyboard.press("1")
    assert page.evaluate("round.state") == "done"


def test_right_turns_green_wrong_turns_red_then_next(page):
    mc(page)
    pick(page, right=True)
    assert page.locator(".choice.right").count() == 1
    assert page.locator(".choice.wrong").count() == 0
    assert page.locator(".fb.ok").count() == 1
    assert page.locator("#next").count() == 1
    page.click("#next")
    assert page.evaluate("round.i") == 1
    pick(page, right=False)
    assert page.locator(".choice.right").count() == 1       # the right answer is shown green
    assert page.locator(".choice.wrong").count() == 1       # the pick is red
    assert page.locator(".fb.bad").count() == 1
    assert page.locator("#next").count() == 1


def test_two_in_a_row_makes_a_card_ready_and_a_miss_resets(page):
    mc(page)
    card = page.evaluate("round.qs[round.i].st.id")
    pick(page, True)
    assert page.evaluate(f"streakOf({DECK!r},{card!r})") == 1
    assert page.evaluate("readiness(%r).ready" % DECK) == 0
    page.evaluate(f"setStreak({DECK!r},{card!r},1)")
    page.evaluate(f"startMC({DECK!r}, true)")
    # make the card we want come up first
    page.evaluate(f"round.qs.sort((a,b)=>(b.st.id==={card!r})-(a.st.id==={card!r}))")
    page.evaluate("playPage()")
    pick(page, True)
    assert page.evaluate(f"streakOf({DECK!r},{card!r})") == 2
    assert page.evaluate("readiness(%r).ready" % DECK) == 1
    page.evaluate(f"startMC({DECK!r}, true)")
    page.evaluate(f"round.qs.sort((a,b)=>(b.st.id==={card!r})-(a.st.id==={card!r}))")
    page.evaluate("playPage()")
    pick(page, False)
    assert page.evaluate(f"streakOf({DECK!r},{card!r})") == 0
    assert page.evaluate("readiness(%r).ready" % DECK) == 0


def test_study_round_never_touches_scores(page):
    mc(page)
    n = page.evaluate("round.qs.length")
    for _ in range(n):
        pick(page, True)
        page.evaluate("next()")
    assert page.evaluate("view.page") == "results"
    assert "study round complete" in page.inner_text("#app").lower()
    assert page.evaluate("DATA.rounds.length") == 0
    assert page.evaluate(f"DATA.best[{DECK!r}] === undefined")


def test_readiness_bar_on_tile_and_survives_reload(page):
    page.evaluate(f"setStreak({DECK!r}, itemsFor({DECK!r})[0].id, 2); saveLocal()")
    page.evaluate(f"view={{page:'unit',unit:DECKS['{DECK}'].unit}};render()")
    assert page.locator(f'[data-deck="{DECK}"] .rbar').count() == 1
    page.reload()
    page.wait_for_function("typeof DECKS!=='undefined'")
    assert page.evaluate(f"readiness({DECK!r}).ready") == 1


def test_old_save_without_streaks_loads(page):
    page.evaluate(
        "localStorage.setItem('anat101.v1', JSON.stringify({v:2,rounds:[],best:{'u1-org':80},savedAt:1}))")
    page.reload()
    page.wait_for_function("typeof DECKS!=='undefined'")
    assert page.evaluate("DATA.best['u1-org']") == 80
    assert page.evaluate("typeof DATA.mc") == "object"


def test_wrong_choices_never_also_right(page):
    bad = page.evaluate("""() => {
      const out=[];
      for (const id of Object.keys(DECKS)) for (const st of itemsFor(id)) for (let k=0;k<3;k++) {
        const ch = pickChoices(id, st);
        if (ch.length!==4 || ch.filter(c=>c.right).length!==1) out.push(id+':'+st.id);
        if (ch.some(c=>!c.right && st.accept.some(a=>norm(a)===norm(c.name)))) out.push(id+':'+st.id+' alias');
      }
      return out.slice(0,10);}""")
    assert bad == []
