def test_id_flags_and_tips(page):
    assert page.evaluate("IDDECKS.size") == 54
    assert page.evaluate("DECKS['ch11-abd'].ident") is True
    assert page.evaluate("DECKS['ch12-ap'].ident") is False
    assert not page.evaluate("!!DECKS['u1-org'].ident")
    items = page.evaluate(
        """D('t-x','ch1','T','q','-',"A | b | c | 1.12 | tip text\\nB | | d")"""
        """.items.map(i=>({tip:i.tip===undefined?null:i.tip,fig:i.fig}))"""
    )
    assert items[0]["tip"] == "tip text"
    assert items[0]["fig"] == "1.12"
    assert items[1]["tip"] is None
    assert page.evaluate("idFiles(DECKS['ch11-abd'].items[0])") is None
    assert page.errors == []
