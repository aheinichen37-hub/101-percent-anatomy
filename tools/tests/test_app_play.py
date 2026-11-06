"""Task 5: the card screen — pre-answer highlight, after-answer picture, tip on a miss, swipe to the next card."""
import functools
import http.server
import threading

import pytest

from .conftest import ROOT


@pytest.fixture(scope="module")
def server():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    handler = functools.partial(Quiet, directory=str(ROOT))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/index.html"
    srv.shutdown()


@pytest.fixture
def phone(browser, server):
    ctx = browser.new_context(viewport={"width": 390, "height": 664}, has_touch=True, is_mobile=True)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(server)
    pg.errors = errs
    yield pg
    ctx.close()


def open_deck(pg, deck, unit):
    pg.evaluate(f"view={{page:'unit',unit:'{unit}'}};render()")
    pg.click(f"[data-deck='{deck}']")


def start(pg, deck, unit, images):
    open_deck(pg, deck, unit)
    pg.click("#img-on" if images else "#img-off")
    pg.wait_for_selector("#ans")


def built_first(pg):
    """Put a card with built pictures first in the round, then redraw."""
    pg.evaluate("round.qs.sort((a,b)=>(idFiles(b.st)?1:0)-(idFiles(a.st)?1:0));render()")


def answer_right(pg):
    name = pg.evaluate("round.qs[round.i].st.name")
    pg.fill("#ans", name)
    pg.click("#go")
    pg.wait_for_selector("#next")


def swipe(pg, x0, y0, x1, y1):
    pg.evaluate("""([x0,y0,x1,y1])=>{
      const el=document.querySelector('#app');
      const t=(x,y)=>new Touch({identifier:1,target:el,clientX:x,clientY:y});
      el.dispatchEvent(new TouchEvent('touchstart',{bubbles:true,touches:[t(x0,y0)],changedTouches:[t(x0,y0)]}));
      el.dispatchEvent(new TouchEvent('touchend',{bubbles:true,touches:[],changedTouches:[t(x1,y1)]}));
    }""", [x0, y0, x1, y1])


def test_ident_asks_mode(phone):
    open_deck(phone, "ch11-abd", "ch11")
    assert phone.locator("#img-on").count() == 1
    phone.click("#mode-x")
    open_deck(phone, "ch12-ap", "ch12")
    assert phone.locator("#img-on").count() == 0
    assert phone.evaluate("round && round.deck") == "ch12-ap"
    assert phone.errors == []


def test_preanswer_image_on(phone):
    start(phone, "ch11-abd", "ch11", True)
    built_first(phone)
    assert phone.locator("#qimg").is_visible()
    assert phone.locator("#aimg").count() == 0
    anim = phone.evaluate("getComputedStyle(document.querySelector('#qimg .hl')).animationName")
    assert anim == "pulseHL"
    assert phone.errors == []


def test_images_off_hides_preanswer(phone):
    start(phone, "ch11-abd", "ch11", False)
    built_first(phone)
    assert phone.locator("#qimg").count() == 0
    answer_right(phone)
    assert phone.locator("#aimg").is_visible()


def test_after_answer_zoom_opens_textbook_figure(phone):
    start(phone, "ch11-abd", "ch11", True)
    built_first(phone)
    answer_right(phone)
    phone.click("#aimg")
    fig = phone.evaluate("idFiles(round.qs[round.i].st).fig")
    assert phone.locator(".zoom img").get_attribute("src") == f"figs/{fig}.jpg"


def test_tip_only_on_miss(phone):
    phone.evaluate("DECKS['ch11-abd'].items.forEach(i=>i.tip='TIP for '+i.name)")
    start(phone, "ch11-abd", "ch11", True)
    answer_right(phone)
    assert phone.locator("#tip").count() == 0
    phone.click("#next")
    phone.wait_for_selector("#ans")
    for _ in range(2):
        phone.fill("#ans", "zzzz")
        phone.click("#go")
    phone.wait_for_selector("#next")
    name = phone.evaluate("round.qs[round.i].st.name")
    assert phone.locator("#tip").inner_text().endswith("TIP for " + name)
    phone.click("#next")
    phone.wait_for_selector("#idk")
    phone.click("#idk")
    phone.wait_for_selector("#tip")


def test_swipe_advances_after_answer(phone):
    start(phone, "ch11-abd", "ch11", True)
    swipe(phone, 300, 400, 200, 410)
    assert phone.evaluate("round.i") == 0
    answer_right(phone)
    swipe(phone, 300, 400, 200, 410)
    assert phone.evaluate("round.i") == 1


def test_vertical_scroll_not_swipe(phone):
    start(phone, "ch11-abd", "ch11", True)
    answer_right(phone)
    swipe(phone, 200, 500, 170, 300)
    assert phone.evaluate("round.i") == 0


def test_swipe_ignored_with_zoom_open(phone):
    start(phone, "ch11-abd", "ch11", True)
    built_first(phone)
    answer_right(phone)
    phone.click("#aimg")
    swipe(phone, 300, 400, 200, 410)
    assert phone.evaluate("round.i") == 0


def test_concept_after_answer_figure(phone):
    open_deck(phone, "ch12-ap", "ch12")
    phone.wait_for_selector("#ans")
    phone.evaluate("round.qs.sort((a,b)=>(FIGS.has(b.st.fig)?1:0)-(FIGS.has(a.st.fig)?1:0));render()")
    answer_right(phone)
    assert phone.locator("#figzoom img").count() == 1
