"""3.9.0 review engine: card memory (FSRS-6, whole days), save schema 4 and the Weak Cards round.
Spec: docs/superpowers/specs/2026-11-26-review-engine-design.md (v1.0.0)."""
import json
import os

import pytest

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
NOW = "2026-11-26T14:00:00Z"
DAY = 86400000


def _fixture(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()


def _load_save(page, text):
    page.evaluate("t => { localStorage.clear(); localStorage.setItem(LS, t); }", text)
    page.reload()
    page.wait_for_timeout(200)


def _days(page, ms_from, ms_to):
    return round((ms_to - ms_from) / DAY, 3)


# ---------- save upgrade ----------

@pytest.mark.parametrize("fixture", ["save-3.8.0.json", "save-3.8.3.json"])
def test_real_save_upgrades_without_loss(page, fixture):
    text = _fixture(fixture)
    old = json.loads(text)
    _load_save(page, text)
    d = page.evaluate("({rounds: DATA.rounds, best: DATA.best, mc: DATA.mc, cardMem: DATA.cardMem, schema: SCHEMA})")
    assert d["schema"] == 4
    assert d["rounds"] == old["rounds"] and d["best"] == old["best"] and d["mc"] == old["mc"]
    assert d["cardMem"] == {}
    saved = json.loads(page.evaluate("localStorage.getItem(LS)"))
    assert saved["v"] == 4 and saved["rounds"] == old["rounds"] and saved["cardMem"] == {}


def test_frozen_pre_upgrade_copy_is_written_once(page):
    text = _fixture("save-3.8.3.json")
    _load_save(page, text)
    assert page.evaluate("localStorage.getItem(LS_PRE4)") == text
    page.evaluate("recordGrade('ch7-skull','ch7-skull-0','good',Date.parse('%s')); saveLocal();" % NOW)
    page.reload()
    page.wait_for_timeout(200)
    assert page.evaluate("localStorage.getItem(LS_PRE4)") == text          # never overwritten
    assert page.evaluate("Object.keys(DATA.cardMem).length") == 1          # and the new data stayed


def test_upgrade_is_idempotent(page):
    _load_save(page, _fixture("save-3.8.0.json"))
    first = page.evaluate("localStorage.getItem(LS)")
    page.reload()
    page.wait_for_timeout(200)
    again = json.loads(page.evaluate("localStorage.getItem(LS)"))
    assert {k: v for k, v in again.items() if k != "savedAt"} == \
        {k: v for k, v in json.loads(first).items() if k != "savedAt"}


@pytest.mark.parametrize("bad", ['"garbage"', "[1,2]", '{"ch1-cav|ch1-cav-0": null, "x": 5}'])
def test_corrupt_card_memory_is_dropped_safely(page, bad):
    save = json.loads(_fixture("save-3.8.3.json"))
    save["v"] = 4
    save["cardMem"] = json.loads(bad)
    _load_save(page, json.dumps(save))
    d = page.evaluate("({rounds: DATA.rounds.length, best: DATA.best, mem: DATA.cardMem})")
    assert d["rounds"] == 20 and d["best"] == save["best"]
    assert isinstance(d["mem"], dict) and all(isinstance(v, dict) for v in d["mem"].values())


def test_old_v1_save_still_upgrades(page):
    _load_save(page, json.dumps({"v": 1, "rounds": [{"deck": "u1-org", "unit": "u1", "credit": 5, "total": 10, "pct": 50, "ts": 1}], "best": {}}))
    d = page.evaluate("({unit: DATA.rounds[0].unit, mc: DATA.mc, mem: DATA.cardMem})")
    assert d == {"unit": "ch3", "mc": {}, "mem": {}}


# ---------- save paths ----------

def test_card_memory_survives_save_export_and_restore(page):
    _load_save(page, _fixture("save-3.8.3.json"))
    page.evaluate("""() => { recordGrade('ch7-vert','ch7-vert-8','hard',Date.parse('%s'));
                              recordGrade('ch1-cav','ch1-cav-0','good',Date.parse('%s')); saveLocal(); }""" % (NOW, NOW))
    page.reload()
    page.wait_for_timeout(200)
    assert set(page.evaluate("Object.keys(DATA.cardMem)")) == {"ch7-vert|ch7-vert-8", "ch1-cav|ch1-cav-0"}
    exported = json.loads(page.evaluate("exportText()"))
    assert set(exported["cardMem"]) == {"ch7-vert|ch7-vert-8", "ch1-cav|ch1-cav-0"}
    # restore into a fresh app: memory comes back; a newer local review is never replaced by an older one
    page.evaluate("() => { localStorage.clear(); }")
    page.reload()
    page.wait_for_timeout(200)
    page.evaluate("recordGrade('ch1-cav','ch1-cav-0','again',Date.parse('%s')+DAY_MS)" % NOW)
    page.evaluate("t => mergeSave(JSON.parse(t))", json.dumps(exported))
    mem = page.evaluate("DATA.cardMem")
    assert mem["ch7-vert|ch7-vert-8"]["g"] == "h"
    assert mem["ch1-cav|ch1-cav-0"]["g"] == "a"                            # the newer local review wins


def test_remote_shape_keeps_card_memory(page):
    page.evaluate("recordGrade('ch1-cav','ch1-cav-0','good',Date.parse('%s'))" % NOW)
    assert "ch1-cav|ch1-cav-0" in page.evaluate("remotePayload().cardMem")


# ---------- scheduler ----------

def test_scheduler_golden_dates(page):
    r = page.evaluate("""() => { const t0 = Date.parse('%s'); DATA.cardMem = {};
        const out = {};
        for (const g of ['again','hard','good']) { recordGrade('ch1-cav','ch1-cav-1',g,t0);
            out[g] = memOf('ch1-cav','ch1-cav-1').due - t0; delete DATA.cardMem['ch1-cav|ch1-cav-1']; }
        let t = t0; const gaps = [];
        for (let i = 0; i < 5; i++) { recordGrade('ch1-cav','ch1-cav-2','good',t); const m = memOf('ch1-cav','ch1-cav-2');
            gaps.push((m.due - t) / DAY_MS); t = m.due; }
        recordGrade('ch1-cav','ch1-cav-2','again',t); const lapse = memOf('ch1-cav','ch1-cav-2');
        return { first: out, gaps, lapseDays: (lapse.due - t) / DAY_MS, lapses: lapse.lapses }; }""" % NOW)
    assert r["first"] == {"again": 1 * DAY, "hard": 2 * DAY, "good": 3 * DAY}
    assert r["gaps"] == [3, 14, 57, 120, 120]                               # capped at 120 days
    assert r["lapseDays"] == 6 and r["lapses"] == 1                         # a miss after a long streak: back in 6 days


# ---------- grades from play ----------

def _typed_card_first(page, deck, cid):
    page.evaluate("""([d, c]) => { startRound(d, false); const k = round.qs.findIndex(q => q.st.id === c);
        round.qs.unshift(round.qs.splice(k, 1)[0]); round.i = 0; round.state = 'ask'; round.fb = ''; playPage(); }""", [deck, cid])


def _answer(page, text):
    page.fill("#ans", text)
    page.click("#go")
    page.wait_for_timeout(60)


def _grade(page, deck, cid):
    return page.evaluate("([d, c]) => (memOf(d, c) || {}).g || null", [deck, cid])


def test_typed_first_try_is_good(page):
    _typed_card_first(page, "ch7-thor", "ch7-thor-11")
    _answer(page, "12")
    assert _grade(page, "ch7-thor", "ch7-thor-11") == "g"


def test_typed_second_try_is_hard(page):
    _typed_card_first(page, "ch7-thor", "ch7-thor-11")
    _answer(page, "13")
    _answer(page, "12")
    assert _grade(page, "ch7-thor", "ch7-thor-11") == "h"


def test_typed_two_misses_is_again(page):
    _typed_card_first(page, "ch7-thor", "ch7-thor-11")
    _answer(page, "13")
    _answer(page, "14")
    assert _grade(page, "ch7-thor", "ch7-thor-11") == "a"


def test_dont_know_is_again(page):
    _typed_card_first(page, "ch7-thor", "ch7-thor-11")
    page.evaluate("giveUp()")
    assert _grade(page, "ch7-thor", "ch7-thor-11") == "a"


def test_did_you_mean_yes_is_good(page):
    _typed_card_first(page, "ch1-cav", "ch1-cav-4")
    _answer(page, "thoracic cavaty")
    page.click("#sug-yes")
    page.wait_for_timeout(60)
    assert _grade(page, "ch1-cav", "ch1-cav-4") == "g"


def test_multiple_choice_miss_is_again_and_right_pick_changes_nothing(page):
    page.evaluate("""() => { startMC('ch7-thor', false); const k = round.qs.findIndex(q => q.st.id === 'ch7-thor-11');
        round.qs.unshift(round.qs.splice(k, 1)[0]); round.i = 0; round.state = 'ask'; playPage(); }""")
    right = page.evaluate("round.qs[0].choices.findIndex(c => c.right)")
    page.evaluate("k => pickChoice(k)", right)
    assert _grade(page, "ch7-thor", "ch7-thor-11") is None
    page.evaluate("""() => { round.i = 0; round.state = 'ask'; const q = round.qs[0];
        pickChoice(q.choices.findIndex(c => !c.right)); }""")
    assert _grade(page, "ch7-thor", "ch7-thor-11") == "a"


def test_mastery_check_answers_update_memory(page):
    _load_save(page, _fixture("save-3.8.3.json"))                           # Axial Skeleton is unlocked
    page.evaluate("() => { startCheck('ch7'); round.state = 'ask'; }")
    q = page.evaluate("({deck: round.qs[0].deck, id: round.qs[0].st.id, name: round.qs[0].st.name})")
    page.evaluate("playPage()")
    _answer(page, q["name"])
    assert _grade(page, q["deck"], q["id"]) == "g"


# ---------- Weak Cards ----------

def _seed(page):
    page.evaluate("""() => { DATA.cardMem = {}; const t0 = Date.parse('%s');
        recordGrade('ch1-cav','ch1-cav-0','again',t0 - 5*DAY_MS);   // old miss: weakest
        recordGrade('ch1-cav','ch1-cav-1','again',t0);
        recordGrade('ch1-cav','ch1-cav-2','hard',t0);
        recordGrade('ch1-cav','ch1-cav-3','good',t0);               // not weak
        recordGrade('ch7-skull','ch7-skull-0','again',t0); }""" % NOW)


def test_weak_cards_selection_and_order(page):
    _seed(page)
    keys = page.evaluate("weakCards(Date.parse('%s')).map(w => w.deck + '|' + w.st.id)" % NOW)
    assert "ch1-cav|ch1-cav-3" not in keys
    assert keys[0] == "ch1-cav|ch1-cav-0"
    assert set(keys) == {"ch1-cav|ch1-cav-0", "ch1-cav|ch1-cav-1", "ch1-cav|ch1-cav-2", "ch7-skull|ch7-skull-0"}
    unit = page.evaluate("weakCards(Date.parse('%s'), 'ch7').map(w => w.st.id)" % NOW)
    assert unit == ["ch7-skull-0"]


def test_weak_cards_cap_at_twenty(page):
    page.evaluate("""() => { DATA.cardMem = {}; itemsFor('ch7-skull').slice(0, 30).forEach(
        st => recordGrade('ch7-skull', st.id, 'again', Date.parse('%s'))); }""" % NOW)
    assert page.evaluate("weakCards(Date.parse('%s')).length" % NOW) == 20


def test_weak_round_never_touches_scores_stars_or_checks(page):
    _load_save(page, _fixture("save-3.8.3.json"))
    _seed(page)
    before = page.evaluate("""() => ({ rounds: DATA.rounds.length, best: JSON.stringify(DATA.best),
        stars: Object.keys(DECKS).map(starsFor).join(), tier: unitTier('ch7'), stats: JSON.stringify(statsFor(() => true)) })""")
    page.evaluate("startWeak()")
    assert page.evaluate("round.method") == "weak"
    n = page.evaluate("round.qs.length")
    for _ in range(n):
        page.evaluate("() => { const q = round.qs[round.i]; grade({id: q.st.id, n: norm(q.st.name)}); next(); }")
    assert page.evaluate("view.page") == "results"
    after = page.evaluate("""() => ({ rounds: DATA.rounds.length, best: JSON.stringify(DATA.best),
        stars: Object.keys(DECKS).map(starsFor).join(), tier: unitTier('ch7'), stats: JSON.stringify(statsFor(() => true)) })""")
    assert after == before
    assert page.evaluate("weakCards(Date.now()).length") == 0                # all right first try: no longer weak


def test_weak_button_and_empty_state(page):
    page.evaluate("() => { DATA.cardMem = {}; view = {page: 'lobby'}; render(); }")
    assert "No weak cards yet" in page.inner_text("#weak")
    _seed(page)
    page.evaluate("() => { view = {page: 'lobby'}; render(); }")
    assert "4" in page.inner_text("#weak-go")
    page.evaluate("() => { view = {page: 'unit', unit: 'ch7'}; render(); }")
    assert "1" in page.inner_text("#weak-go")
