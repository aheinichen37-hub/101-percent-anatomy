# 3.9.0 review engine: build plan and record (2026-11-26)

Spec: `docs/superpowers/specs/2026-11-26-review-engine-design.md` v1.0.0 (approved by Andrew).

1. **Vendor FSRS-6.** ts-fsrs 6.0.1 at commit 828447d (MIT) + srs-kit 1.0.1 (BSD-3-Clause), FSRS-6 only, built synchronously by `tools/fsrs/entry.ts` + `build.mjs` with esbuild into `tools/fsrs/fsrs6.min.js` (40 KB with licences) and inlined between the `fsrs-vendor` markers. Checked: same intervals as the library's own `DefaultScheduler({version:'FSRS-6'})`.
2. **Tests first** (`tools/tests/test_review_engine.py`, 22 tests): upgrade of both real saves, frozen copy, idempotence, corrupt memory, v1 saves, save/export/restore/remote paths, golden dates, every grade path from play, Weak selection, cap, isolation and buttons.
3. **Card memory + schema 4**: `MIGRATE[3]`, `cleanMem`, `mergeMem`, `LS_PRE4`, `remotePayload`; hooks in `grade`, `giveUp`, `pickChoice`; saved after each answer.
4. **Weak Cards**: `weakAll`/`weakCards`, `startWeak`, `finishWeak`, `weakResultsPage`, `weakBlock` on lobby and unit page; back navigation handles a round with no unit.
5. **Regression test v2.2.0**: a Weak Cards pass on the first pass's saved stats in every mode.
6. **Release**: version marks, README, CLAUDE.md, IDEAS.md; full checks; phone-width screenshots (360, 430 px); push on Andrew's word.

Measured golden intervals (FSRS-6, retention 0.9, cap 120, whole days): first Again 1 day, Hard 2, Good 3; Good streak 3, 14, 57, 120, 120; a miss after that streak 6 days.
