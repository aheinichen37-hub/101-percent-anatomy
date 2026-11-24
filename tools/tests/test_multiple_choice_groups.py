"""v3.6.0: wrong options come from the same family as the right answer."""
ARM = "ch8-arm"


def card(page, deck, name):
    return page.evaluate(
        "([d,n]) => itemsFor(d).find(i => i.name === n).id", [deck, name])


def gof(page, deck, name):
    return page.evaluate(
        "([d,n]) => groupOf(d, itemsFor(d).find(i => i.name === n))", [deck, name])


def picks(page, deck, name, n=200):
    """Run pickChoices n times; return [(group of each wrong option), ...] per run."""
    return page.evaluate("""([d,name,n]) => {
        const st = itemsFor(d).find(i => i.name === name), out = [];
        for (let k = 0; k < n; k++) {
          const cs = pickChoices(d, st);
          out.push({names: cs.map(c => c.name), right: cs.filter(c => c.right).length,
                    wrong: cs.filter(c => !c.right).map(c => groupOf(d, itemsFor(d).find(i => i.id === c.id)))});
        }
        return out; }""", [deck, name, n])


def test_groups_follow_the_bone(page):
    assert gof(page, ARM, "Medial epicondyle") == "humerus"
    assert gof(page, ARM, "Radial tuberosity") == "radius"
    assert gof(page, ARM, "Scaphoid") == "carpal"
    assert gof(page, ARM, "Coronoid process") == "ulna"
    assert gof(page, ARM, "Ulna") == "bones"            # a whole bone is its own family
    assert gof(page, "ch7-skull", "Coronal suture") == "suture"


def test_landmark_gets_landmarks_not_other_bones(page):
    runs = picks(page, ARM, "Medial epicondyle")
    for r in runs:
        assert len(set(r["names"])) == 4 and r["right"] == 1
        assert r["wrong"].count("humerus") >= 2          # mostly same family
        assert "bones" not in r["wrong"]                  # never a whole bone among landmarks


def test_whole_bone_gets_whole_bones(page):
    for r in picks(page, ARM, "Radius"):
        assert r["wrong"].count("bones") >= 2


def test_small_group_tops_up_without_repeats(page):
    # Hamate sits in a carpal group of 3; the rest must come from elsewhere, still 4 distinct
    for r in picks(page, ARM, "Hamate", 100):
        assert len(set(r["names"])) == 4 and r["right"] == 1


def test_ungrouped_decks_and_missing_clues_do_not_crash(page):
    ids = page.evaluate("Object.keys(DECKS)")
    bad = page.evaluate("""ids => { const out = [];
        for (const d of ids) for (const st of itemsFor(d)) {
          const cs = pickChoices(d, st);
          if (new Set(cs.map(c => c.name)).size !== cs.length || cs.filter(c => c.right).length !== 1) out.push(d + '|' + st.name);
        } return out.slice(0, 5); }""", ids)
    assert bad == []


def test_report_shape(page):
    rep = page.evaluate("groupReport()")
    d = next(x for x in rep["decks"] if x["id"] == ARM)
    assert d["cards"] > 20 and 0 <= d["sameGroupShare"] <= 1
