"""Task 1: identification deck flag, tip field, idFiles()."""


def test_id_flags_and_tips(page):
    assert page.evaluate("IDDECKS.size") == 54
    assert page.evaluate("DECKS['ch11-abd'].ident") is True
    assert page.evaluate("DECKS['ch12-ap'].ident") is False
    assert not page.evaluate("!!DECKS['u1-org'].ident")

    items = page.evaluate(
        """() => D('t-x','ch1','T','q','-', "A | b | c | 1.12 | tip text\\nB | | d").items"""
    )
    assert items[0]["tip"] == "tip text"
    assert items[0]["fig"] == "1.12"
    assert "tip" not in items[1] or items[1]["tip"] is None

    assert page.evaluate("idFiles(DECKS['ch11-abd'].items[0])") is None


def test_every_id_deck_exists(page):
    """A typo in IDDECKS would silently leave that deck a concept deck."""
    missing = page.evaluate("[...IDDECKS].filter(id => !DECKS[id])")
    assert missing == []


def test_imgopt_rule_is_gone(page):
    """v2.4 offered the images choice on any deck where 60% of cards had a figure.
    Identification decks decide it now, so the old flag must not linger."""
    assert page.evaluate("Object.values(DECKS).every(d => d.imgOpt === undefined)")
