"""Task 5: the card screen — pre-answer picture, after-answer figure, tip, swipe."""


def start(page, deck, images=True, with_picture=False, tip=None):
    """Begin a round and, optionally, pretend the current card has built pictures."""
    page.evaluate(f"startRound({deck!r}, {str(images).lower()})")
    if with_picture:
        page.evaluate("IDIMG.add(round.qs[round.i].st.id)")
    if tip is not None:
        page.evaluate("t => round.qs[round.i].st.tip = t", tip)
    page.evaluate("playPage()")


def answer_correctly(page):
    page.evaluate("grade({id: round.qs[round.i].st.id, n: '', label: ''})")


SWIPE = """([x0,y0,x1,y1]) => {
  const el = document.querySelector('#app');
  const t = (x,y) => new Touch({identifier:1, target:el, clientX:x, clientY:y});
  el.dispatchEvent(new TouchEvent('touchstart',{bubbles:true,touches:[t(x0,y0)],changedTouches:[t(x0,y0)]}));
  el.dispatchEvent(new TouchEvent('touchend',{bubbles:true,touches:[],changedTouches:[t(x1,y1)]}));
}"""


def test_ident_asks_mode_and_concept_does_not(page):
    page.evaluate("view={page:'unit',unit:DECKS['ch11-abd'].unit};render()")
    page.click('[data-deck="ch11-abd"]')
    assert page.locator("#img-on").count() == 1
    page.evaluate("$('#modalSlot').innerHTML=''")

    page.evaluate("view={page:'unit',unit:DECKS['ch12-ap'].unit};render()")
    page.click('[data-deck="ch12-ap"]')
    assert page.locator("#img-on").count() == 0
    assert page.evaluate("!!round") is True


def test_preanswer_image_on(page):
    start(page, "ch11-abd", images=True, with_picture=True)
    assert page.locator("#qimg").count() == 1
    assert page.locator("#qimg .hl").count() == 1
    assert page.locator("#aimg").count() == 0


def test_images_off_hides_preanswer_but_shows_after(page):
    start(page, "ch11-abd", images=False, with_picture=True)
    assert page.locator("#qimg").count() == 0
    answer_correctly(page)
    assert page.locator("#aimg").count() == 1


def test_tip_only_on_miss(page):
    start(page, "ch11-abd", with_picture=True, tip="Think of a six-pack.")
    answer_correctly(page)
    assert page.locator("#tip").count() == 0

    start(page, "ch11-abd", with_picture=True, tip="Think of a six-pack.")
    page.evaluate("giveUp()")
    assert page.locator("#tip").count() == 1
    assert "six-pack" in page.inner_text("#tip")


def test_tip_hidden_on_a_concept_deck(page):
    start(page, "ch12-ap", tip="should not show")
    page.evaluate("giveUp()")
    assert page.locator("#tip").count() == 0


def test_swipe_advances_only_after_answering(page):
    start(page, "ch11-abd")
    before = page.evaluate("round.i")
    page.evaluate(SWIPE, [300, 400, 200, 410])
    assert page.evaluate("round.i") == before, "swiped before answering"

    answer_correctly(page)
    page.evaluate(SWIPE, [300, 400, 200, 410])
    assert page.evaluate("round.i") == before + 1


def test_vertical_scroll_is_not_a_swipe(page):
    start(page, "ch11-abd")
    answer_correctly(page)
    before = page.evaluate("round.i")
    page.evaluate(SWIPE, [200, 500, 170, 300])
    assert page.evaluate("round.i") == before


def test_swipe_ignored_with_a_modal_open(page):
    start(page, "ch11-abd")
    answer_correctly(page)
    before = page.evaluate("round.i")
    page.evaluate("$('#modalSlot').innerHTML='<div class=\\'scrim\\'></div>'")
    page.evaluate(SWIPE, [300, 400, 200, 410])
    assert page.evaluate("round.i") == before


def test_concept_deck_still_shows_its_figure_after_answering(page):
    start(page, "ch12-ap", images=False)
    page.evaluate("""() => {
        const i = round.qs.findIndex(q => q.st.fig && q.st.fig !== '-' && FIGS.has(q.st.fig));
        if (i >= 0) { round.i = i; playPage(); }
    }""")
    answer_correctly(page)
    assert page.locator("#figzoom").count() == 1
