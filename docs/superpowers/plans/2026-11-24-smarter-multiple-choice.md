# Smarter Multiple Choice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (native) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Multiple choice wrong options come from the same family as the right answer, with a scanner that reports weak questions across all decks.

**Architecture:** Group inference, the picker rule and the echo check live inside `index.html` (one source of truth, no build step). `tools/groups.py` loads the page in a headless browser, calls the page's `groupReport()` and prints a readable report; hand fixes live in `tools/groups-overrides.json` and `groups.py --apply` writes them into a marked block in `index.html`.

**Tech Stack:** Single-file HTML/JS app, Python 3 + Playwright + pytest (already used by `tools/`).

**Spec:** `docs/superpowers/specs/2026-11-24-smarter-multiple-choice-design.md`

## Global Constraints
- Target version `3.6.0` (semver): footer `#ver`, CSS comment on line 17, `README.md` "Current version".
- Cards without a group behave exactly as today; typed rounds, grading, stars, readiness, save format and pictures do not change.
- Existing `clash()` runs first on every candidate; number answers keep number-only wrong options.
- `python3 tools/regress.py index.html --full` and `python3 tools/correctness.py index.html` must pass before the release push.

## Review Focus
- A deck whose only group has 2 cards: no repeated or missing options (tested in Task 1).
- A card with no clue, or a deck built from `MITO`/`STRUCT` (no `.items`): no crash, today's behaviour (Task 1).
- Whole-bone answers (Ulna) never get landmark options and landmark answers never get whole-bone options (Task 1).
- Same card asked 200 times: never duplicate options, never two right answers (Task 1).
- Overrides naming a card that no longer exists: ignored, reported as stale (Task 2).

---

### Task 1: Groups and picker in index.html
**Files:** Modify `index.html` (`D()` parser, new `groupOf`/`echoWords`/`groupReport`, `pickChoices`); Test `tools/tests/test_multiple_choice_groups.py`

**Interfaces:**
- Produces: `groupOf(deckId, item) -> string|null`; `echoWords(deckId, item) -> string[]`; `groupReport() -> {decks:[{id,cards,ungrouped:[names],small:[{group,n}],echo:[{name,words}],sameGroupShare:number}]}`; `GROUP_OVERRIDES` object (`"deckId|Card name": "group"`) inside `/*GO*/…/*END GO*/` markers; `D()` accepts an optional 6th field `group`.

- [ ] Write failing tests: in `ch8-arm`, `groupOf` gives `humerus` to Medial epicondyle, `radius` to Radial tuberosity, `carpal` to Scaphoid, `bones` to Ulna; over 200 picks for "Medial epicondyle" at least 2 of 3 wrong options are `humerus` group and none are carpal; for a group-of-2 deck card options are 4 distinct with one right; `ch1-pl` (no groups) results unchanged in shape.
- [ ] Run them, confirm they fail (`groupOf is not defined`).
- [ ] Implement `groupOf` in order: override or 6th field; whole bone (name is a host word or ends in "bone") → `bones`; host word in the name (adjectives too: radial→radius); a shared last word across 3+ cards in the deck (suture, process); first host word in the clue; else null. Host word table is a plain object `GROUP_HOSTS` at the top of the block so a new course swaps it out.
- [ ] Implement picker rule in `pickChoices`: same group first; when the group has 5+ siblings, 1 question in 4 swaps one for a neighbour-group card; then the existing fallbacks. Prefer same-group options that share an echo word with the clue.
- [ ] Run the new tests and `tools/tests/test_multiple_choice.py`; confirm pass.
- [ ] Commit.

### Task 2: Scanner and overrides
**Files:** Create `tools/groups.py`, `tools/groups-overrides.json`; Test `tools/tests/test_groups_tool.py`

**Interfaces:** Consumes `groupReport()`. `groups.py [index.html] [--report|--apply|--json]`; stale overrides listed under "Stale overrides".

- [ ] Failing test: `--report` on the repo exits 0 and prints "ch8-arm"; `--apply` with a temp override file changes only the `/*GO*/` block.
- [ ] Implement report (worst decks first: ungrouped, small groups, echoes, same-group share) and apply.
- [ ] Run tests; run the report on the real data; fix wrong or missing groups through overrides.
- [ ] Commit.

### Task 3: Release checks
**Files:** Modify `index.html` footer + CSS comment, `README.md`, `CLAUDE.md`, `IDEAS.md`

- [ ] Add the scanner to the pre-release routine in `CLAUDE.md`; note the toolkit is reusable for other courses (swap `GROUP_HOSTS` and overrides).
- [ ] Bump to 3.6.0. Run `tools/regress.py --full`, `tools/correctness.py`, all of `tools/tests`.
- [ ] Commit; try to push (needs push access).
