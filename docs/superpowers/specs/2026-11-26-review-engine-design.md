# 3.9.0 review engine and Weak Cards (spec v1.0.0, approved by Andrew 2026-11-26; supersedes v0.2.0)

Roadmap v1.1.0 release 1. Architecture v1.1.0 checked against the 3.8.3 code; where they differ, the code wins and this spec records it.

## Decisions (Andrew, 2026-11-26)
1. FSRS-6, day-based. 2. Multiple choice: only misses count. 3. Keep a frozen pre-upgrade copy. 4. Card memory starts empty.
Also resurfaced from `IDEAS.md`: "Weak cards only round" (2026-11-20) and "Daily Review" (2026-11-06); Weak Cards covers the first now, Today (3.10.0) the second.

## Gate 0 (done)
- **A** card IDs: positional, now locked (3.8.1, `tools/card-ids.json`, `test_card_ids.py`).
- **B** real saves as fixtures: `tools/tests/fixtures/save-3.8.0.json` (2026-11-25) and `save-3.8.3.json` (2026-11-26, includes two Axial Skeleton checks). Public repo OK'd by Andrew.
- **C** mastery check played on the phone: Axial Skeleton, 99% (2026-11-26).
- 3.8.0 backup: waived by Andrew (the code is in `main`'s history).

## What Andrew gets
1. Every typed answer now updates that card's memory: how well it is known and when it is next due. Nothing on screen changes for deck rounds, stars, tiers or checks.
2. A **Weak cards** round: up to 20 cards he has recently missed or only got on the second try, weakest first, typed, from any deck. Results update card memory only; no high score, no stars, no stats line, no check credit.

## What the code says (changes from the architecture doc)
- The save is versioned (`SCHEMA = 3`, forward `MIGRATE` steps, `upgrade()`), with a rolling backup key (`anat101.v1.backup`, the save before the last write) and export/restore (v2.6). 3.9.0 adds step 3 → 4. No second backup system.
- `saveLocal()`, export/import and the remote path in `initRemote()` name `rounds`, `best`, `mc` explicitly; each must carry the new `cardMem` or it is silently dropped. Tests cover all three paths.
- Saved rounds hold deck totals only (no per-card results), so card memory **cannot be replayed from history**.
- Check rounds already mix decks (`round.qs[i].deck`), so Weak Cards reuses that engine. Weak rounds are **not** written to `DATA.rounds`, so stars, best, stats and checks cannot see them by construction.
- ts-fsrs is now **6.0.1** with a new API (`DefaultScheduler`, card fields `dueAt`, `lastReviewAt`, `scheduledDays`, ...) and **FSRS-7 as the default model**; FSRS-6 is still offered. npm is blocked here, but esbuild and the ts-fsrs source (GitHub, MIT; its `srs-kit` dependency is BSD-3-Clause) are available, so it can be built into one inline script: about 62 KB minified with the full scheduler, less if trimmed to FSRS-6. Build script and pinned commit kept in `tools/fsrs/` so it can be rebuilt.

## Scheduler
- Model **FSRS-6** (Andrew, 2026-11-26), desired retention 0.90, maximum interval 120 days, fuzz off, **day-based** (`enableShortTerm: false`): no 1/5/10-minute learning steps, which don't fit a round-based app. Measured with these settings: first Good → due in 3 days, then 14, 57, 120; first Again → next day; a miss after a long streak → 3 days, then 8, 19.
- Grades (one constant table, tunable):

| Event | Grade |
|---|---|
| Typed, right first try (a "Did you mean" yes counts as first try) | Good |
| Typed, right on second try | Hard |
| Typed, missed twice, or "I don't know" | Again |
| Multiple choice, wrong | Again (Andrew: only misses count) |
| Multiple choice, right | no change (the ready streak still tracks it) |
| Easy | never used |

- Typed answers in deck rounds, mastery checks and Weak rounds all update memory (a check is real recall). Free retries ("nudge", "near") don't.

## Data
- `DATA.cardMem`: `{ "deck|cardId": { s, d, st, due, last, reps, lapses, g } }` (stability, difficulty, FSRS state, due and last review as ms timestamps, last grade). Keyed by deck + card, like the ready streaks, because Organelles and Organelle Functions share card IDs. About 2,300 cards × ~90 bytes at most: well under storage limits.
- Save schema 4: `MIGRATE[3] = d => ({...d, cardMem: {}})`. Idempotent; an old save loads with all rounds, best scores and streaks unchanged.
- **Seeding**: none (Andrew). Every card's memory starts the first time it is answered after the update.
- **Pre-upgrade copy** (Andrew: yes): on the first upgrade from schema 3 the old save is written once to `anat101.v1.pre-v4`, never overwritten, and removed in a later release. It sits beside the rolling backup in the same storage; export/restore can read it.
- Corrupt or unreadable `cardMem` is dropped (memory restarts) without touching rounds, best or streaks, and the save banner says so in plain words.

## Weak Cards
- **Which cards**: cards whose last grade was Again (typed or a multiple-choice miss) or Hard (typed second try), lowest current retrievability first, then highest difficulty; at most 20. Empty state: "No weak cards yet. Cards you miss or get on the second try show up here."
- **Where**: a "Weak cards · N" button at the top of the lobby (above the units), and on each unit page for that unit's weak cards. Moves into the Weak tab in 4.0.0.
- **Round**: typed, mixed decks, the deck name shown on each card, normal pictures and tips. Results screen: right first try / second try / missed, how many cards are no longer weak, Weak again, Back.

## Tests (written first)
- Migration on both real fixtures: rounds, best and mc identical after upgrade; running it twice changes nothing; schema 4 written; the frozen pre-v4 copy is written once and never overwritten; v1/v2 saves still upgrade; corrupt `cardMem` handled.
- Save paths: `cardMem` survives `saveLocal`/`loadLocal`, export → import, and the remote shape.
- Scheduler golden tests: fixed dates in, fixed due dates out for each grade (numbers above).
- Grade mapping: first try, did-you-mean, second try, two misses, "I don't know", nudge (no update), multiple-choice miss (Again) and right pick (no update).
- Isolation: a Weak round leaves `DATA.rounds`, `best`, stars, stats, tiers and check unlocks unchanged.
- Weak selection: ordering, cap 20, empty state, per-unit filter.
- `regress.py --quick` gains one Weak Cards flow; vendored script loads offline with its licence notices.

## Out of scope (next releases)
Today session and streak (3.10.0), Path (4.0.0), specimens (4.1.0), "I guessed" flag, confusable pairs, exam-date pacing.
