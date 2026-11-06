"""Deck tiles carry a dot for the kind of deck and a dot for what pictures it has."""


def open_unit(page, deck):
    page.evaluate(f"view={{page:'unit',unit:DECKS[{deck!r}].unit}};render()")


def tile_classes(page, deck):
    return page.evaluate(
        "id => [...document.querySelector(`[data-deck='${id}']`).querySelectorAll('.dots i')]"
        ".map(e => e.className)", deck)


def test_identification_deck_dot(page):
    open_unit(page, "ch11-abd")
    assert tile_classes(page, "ch11-abd")[0] == "k-id"


def test_term_deck_dot(page):
    open_unit(page, "ch12-ap")
    assert tile_classes(page, "ch12-ap")[0] in {"k-term", "k-fn"}
    assert tile_classes(page, "ch12-ap")[0] != "k-id"


def test_picture_dot_reflects_built_images(page):
    built = page.evaluate("[...IDIMG][0] || null")
    if not built:
        return
    deck = page.evaluate("""id => {
        for (const d of Object.values(DECKS))
            if ((itemsFor(d.id) || []).some(i => i.id === id)) return d.id;
        return null;
    }""", built)
    open_unit(page, deck)
    assert tile_classes(page, deck)[1] == "p-yes"


def test_deck_without_any_pictures(page):
    """A deck with no built pictures must not claim one."""
    deck = page.evaluate("""() => {
        for (const d of Object.values(DECKS)) {
            const its = itemsFor(d.id) || [];
            if (its.length && !its.some(i => IDIMG.has(i.id))) return d.id;
        }
        return null;
    }""")
    if not deck:
        return
    open_unit(page, deck)
    assert tile_classes(page, deck)[1] in {"p-after", "p-no"}


def test_dots_are_described_for_screen_readers(page):
    open_unit(page, "ch11-abd")
    text = page.evaluate(
        "document.querySelector(\"[data-deck='ch11-abd'] .sr\").textContent")
    assert "Identification" in text


def test_legend_lists_every_dot(page):
    open_unit(page, "ch11-abd")
    classes = page.evaluate(
        "[...document.querySelectorAll('.legend i')].map(e => e.className)")
    assert set(classes) == {"k-id", "k-fn", "k-term", "p-yes", "p-after", "p-no"}
