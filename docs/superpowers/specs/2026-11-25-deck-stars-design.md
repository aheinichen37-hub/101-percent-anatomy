# Deck stars (target release 3.7.0)

Short design. Written 2026-11-25 from the conversation with Andrew. It replaces the 2026-11-06 "3 perfect runs = 3 stars" idea in `IDEAS.md`.

## Intent
Give each typed deck a star rating so a run has a reward beyond the high score, and so the later unit mastery check has something to unlock against. Stars were named the next build after multiple choice (Andrew, 2026-11-20).

## Rule (decided by Andrew)
- A typed run's score earns a tier: 50% or more = 1 star, 80% or more = 2 stars, a perfect run = 3 stars.
- Perfect means every card right on the first try. A second try is worth half a point, so a run with any second try cannot earn 3 stars. A spelling correction ("did you mean", "Yes, submit") costs nothing, as it does today.
- A deck's stars come from its best typed run. Stars never go down.
- A deck needs 2 or more stars to count toward the unit mastery check (built later, not in this release).

## Goals
- Stars show on each deck tile and are announced on the results page when a run earns more than before.

## Non-goals
- No unit mastery check, lobby header tiers, Daily Review or Speed Round in this release.
- Multiple choice never earns stars. There are no grey readiness stars: the readiness bar already shows study progress (Andrew, 2026-11-25).
- No change to grading, high scores or the save format.

## Anti-goals
- Stars that disagree with the saved history, or a change that risks the save. Either would defeat the purpose.

## Approaches
1. **Compute stars from saved rounds (picked).** `starsFor(deckId)` reads the credit and total already saved on every typed round. No migration, no second copy of the truth, and past runs count automatically.
2. **Store a star counter per deck.** Needs a schema bump and a migration, and can drift from the history. Rejected.

## Decisions
- Andrew decided: the tier cutoffs, the best-run rule, that 3 stars needs a perfect first-try run, and no grey stars.
- Claude's calls (not yet confirmed by Andrew): tiers use the exact score and not the rounded percent (79.6% stays at 1 star); Images on and off both count; past runs count retroactively.

## Parts
- `starTier(credit, total)` is the only place the 50/80/100 rule lives.
- `starsFor(deckId)` returns 0 to 3 from the deck's best typed round.
- Deck tile: 3-star row. Results page: "stars earned" line.

## Left to the builder
- Star markup and styling, in the existing visual style.
- Test cases: tier boundaries (49.9%, 50%, 79.9%, 80%), a 100% run, a run with one second try (not 3 stars), a deck with no runs, an old save with past runs.
- Version bump to 3.7.0 in the footer, the CSS comment and `README.md`, then the regression, groups and correctness runs before the push, as `CLAUDE.md` requires.
