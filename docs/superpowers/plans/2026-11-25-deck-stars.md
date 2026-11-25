# Deck stars Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every typed deck 0-3 stars from its best typed run, shown on deck tiles and announced on the results page.

**Architecture:** Stars are computed from `DATA.rounds` (each typed round already saves `credit`, `total`, `deck`). Two pure functions in `index.html` hold the rule; no save-format change. Multiple choice never writes to `DATA.rounds`, so it cannot earn stars.

**Tech Stack:** Single-file `index.html` app, pytest + Playwright tests in `tools/tests/`.

**Spec:** `docs/superpowers/specs/2026-11-25-deck-stars-design.md`

## Global Constraints

- Tiers: 50% or more = 1 star, 80% or more = 2 stars, 3 stars only when `credit === total` (every card right on the first try; a second try is 0.5).
- Spelling corrections ("did you mean") already cost nothing; do not change grading.
- A deck's stars come from its best typed run; they never go down. Past runs count.
- Tier maths uses exact `credit`/`total`, never the rounded `pct`, and no floating division at the boundaries.
- No schema bump, no migration, no change to `finish()`'s saved round shape.
- No grey stars; the readiness bar stays as is.
- Release 3.7.0: version in the page footer (`#ver`), the CSS comment, and `README.md`.

## Review Focus

- A deck with no runs shows 0 stars, not an error.
- A 79.6% run stays 1 star; 80% exactly is 2 stars (boundary at 16 of 20).
- A run with one second try and everything else right is 2 stars, not 3.
- Multiple-choice rounds never change stars.
- A worse later run never lowers stars.

---

### Task 1: Star rule

**Files:**
- Modify: `index.html` (add beside `statsFor`, near line 3062)
- Test: `tools/tests/test_stars.py` (create)

**Interfaces:**
- Produces: `starTier(credit: number, total: number): 0|1|2|3` and `starsFor(deckId: string): 0|1|2|3` (max tier over `DATA.rounds` with `r.deck===deckId`).

- [ ] **Step 1: Write failing tests** in `test_stars.py`: `test_tier_boundaries` asserts `starTier` is 0 for (9,20), 1 for (10,20), 1 for (15.5,20), 2 for (16,20), 2 for (19.5,20), 3 for (20,20), 0 for (0,0); `test_starsfor_uses_best_run` sets `DATA.rounds` to two rounds on one deck (credit 18 then 9 of 20) and expects 2, and 0 for a deck with no rounds; `test_mc_never_earns_stars` sets `DATA.mc` streaks for a deck and expects `starsFor` 0.
- [ ] **Step 2:** Run `python3 -m pytest tools/tests/test_stars.py -q`; expect failures (`starTier is not defined`).
- [ ] **Step 3:** Implement both functions. Compare with integers (`credit>=total`, `credit*10>=8*total`, `credit*2>=total`).
- [ ] **Step 4:** Run the same command; expect all pass.
- [ ] **Step 5:** Commit `3.7.0: star rule`.

### Task 2: Show stars

**Files:**
- Modify: `index.html` (`unitPage` tile at line 3118, `finish()` at 3451, `resultsPage()` at 3484, CSS near `.tile .ready`)
- Test: `tools/tests/test_stars.py`

**Interfaces:**
- Consumes: `starsFor`.
- Produces: `starRow(n: number): string` returning markup with `aria-label="N of 3 stars"`; tile element `.stars`; results element `#starsline`; `round.result.stars` and `round.result.starsBefore` (compute `starsBefore` in `finish()` before the new round is added to `DATA.rounds`).

- [ ] **Step 1: Write failing tests:** the unit page tile for a deck with a saved 90% round has a `.stars` element whose aria-label is "2 of 3 stars"; after `startRound` and grading every card correctly, `view.page` is `results` and `#starsline` says 3 stars and shows an earned line; a second all-correct run on a 3-star deck shows no earned line; a run that gets one second try shows 2 stars.
- [ ] **Step 2:** Run; expect failures.
- [ ] **Step 3:** Implement `starRow`, add it to the tile after the meta row, add the results line ("New star earned" only when `stars>starsBefore`), and add star CSS in the existing style.
- [ ] **Step 4:** Run the new tests plus `python3 -m pytest tools/tests -q`; expect all pass.
- [ ] **Step 5:** Commit.

### Task 3: Release 3.7.0

**Files:**
- Modify: `index.html` (`#ver`, CSS comment), `README.md`, `IDEAS.md`, `CLAUDE.md` only if it names versions

- [ ] **Step 1:** Bump to 3.7.0 in all three places and add a short README section on stars.
- [ ] **Step 2:** In `IDEAS.md`, move the deck stars item to **Done** (3.7.0, 2026-11-25) and replace the 11/06 star line; keep the unit mastery line, noting it now unlocks at 2 stars on every deck.
- [ ] **Step 3:** Run `python3 tools/regress.py index.html --full`, `python3 tools/groups.py`, `python3 tools/correctness.py index.html`; expect no errors.
- [ ] **Step 4:** Commit.
