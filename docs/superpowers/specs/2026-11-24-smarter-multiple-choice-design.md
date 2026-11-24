# Smarter multiple choice: distractors that don't give the answer away

Date: 2026-11-24. Status: draft for Andrew's approval. Target: app 3.6.0.

## Intent and why
Multiple choice is the warm-up for the typed decks, which are the real test. Right now the wrong options can be spotted without knowing the material. Example from Upper Limb Bones: the question points at the medial epicondyle (a humerus landmark) and the other three options are radius, ulna or carpal answers, so "the only humerus one" wins. If a question can be beaten by pattern, it stops preparing him for typing the answer.

## Goals
- Wrong options come from the same family as the right answer (same bone, same muscle group, same organ system) so he has to know the content.
- Questions where the stem and an option share a rare word (the answer echoing the question) are found and fixed or accepted knowingly.
- One scanner reports weak questions across all 142 decks / 2,247 cards, so he never has to hunt for them by playing.

## Non-goals
- No change to typed rounds, grading, stars, readiness, save format, or pictures.
- No new question types, and no rewriting of clues or answers in bulk.

## Anti-goals (failure even if it "works")
- A deck gets stuck or shows repeated options because its family is small.
- Wrong options that could also be correct (the existing `clash()` rule stays and runs first).
- Making multiple choice so hard it stops being a warm-up.

## Constraints
- Single-file app (index.html), decks written as `Name | alternates | clue | figure | tip` lines through `D(...)`.
- Existing picker `pickChoices(deckId, st)` already filters number vs text and avoids clashes; keep that behaviour.
- Existing checks (regress.py quick/full, correctness.py, tests/test_multiple_choice.py) must still pass. Release flow and version in footer, CSS comment, README.

## Approaches considered
1. Hand-tag every card with a group. Exact, but 2,247 lines to touch.
2. Fully automatic groups from clue text. Fast, but only about two-thirds of bone cards name their bone in the clue; the rest would be guessed wrong.
3. **Hybrid (chosen by Andrew).** Automatic first pass, a report of cards it can't place or that look thin, and a corrections file for hand fixes.

## Design
**Groups.** A new optional 6th field per card line (`group`), plus `tools/groups-overrides.json` for hand fixes (same idea as `id-overrides.json`). A build/audit script `tools/groups.py` infers a group per card when none is given: host word in the clue (humerus, ulna, scapula, femur ...), then the clue's category words for muscles/organs, then name patterns. It writes the result into the page's data and prints what it could not place.

**Picker rule ("mostly same").** For each question, fill up to 3 wrong options in this order: same group; then, at most one slot, a neighbouring group in the same deck (a "neighbour" is a group that shares a unit/figure); then the current fallbacks (same unit, anywhere, any kind). Cards with no group behave exactly as today. A deck with a tiny group tops up from neighbours first, so it never repeats or runs dry.

**Leak check.** Before an option is accepted, reject it if (a) it is the odd one out in kind (landmark vs whole bone) or (b) the stem/clue shares a rare word with exactly one option and that option is the answer. Rare means a word appearing in few answers in the deck. Deltoid tuberosity is expected to be reported as a mild echo and kept, because its distractors will all be humerus landmarks.

**Scanner report.** `python3 tools/groups.py index.html --report` lists, per deck: cards with no group, groups of fewer than 3 cards, questions with a leak, and the share of questions that now have 3 same-group wrong options. Output is a readable list for Andrew to review, worst decks first.

**Tests.** Extend `test_multiple_choice.py`: no card ever gets duplicate or clashing options; a card in a group of 4+ gets at least 2 same-group wrong options; ungrouped decks are unchanged. Add the scanner to the pre-release routine next to regress and correctness.

## Left to the builder
Exact word lists for inference, scoring details for the leak check, report formatting, and the file layout of the overrides.

## Calls I made (not discussed with Andrew)
- Max one neighbour-group option per question.
- Cards in decks with no groups (steps, numbers) keep today's behaviour.
- Version as 3.6.0 (new capability), under the semver rule.
- Nothing is pushed; I have read-only access to the repo from this session.
