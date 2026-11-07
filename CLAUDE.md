# Notes for Claude

- Andrew talks in raw, rambling thoughts. When a message mentions a side idea (even in passing), add it to `IDEAS.md` under **Open** with the date, and check `IDEAS.md` before starting new work so parked ideas resurface when they fit.
- Push new ideas to `IDEAS.md` on GitHub automatically whenever a conversation ends or a brainstorm wraps up, without waiting to be asked.
- Version every release with an incrementing number (2.4, 2.5, ...) in the page footer, the CSS comment and `README.md`.
- Run the regression test (regress 2.0, `tools/regress.py` in this repo is the source of truth; the claude.ai project still holds the old v1 copy, `claude/101-anatomy-regression-test.py`, which is out of date) on every new version before pushing. Use `python3 tools/regress.py index.html --quick` (about 6 s) while building and `--full` (about 40 s) before every release push. `--units 3,11` replays chosen units and `--changed` replays only decks whose questions or pictures changed since the last passing run. Commit `tools/.regress-cache.json` with each release; it is what `--changed` compares against. Version the test itself with an incrementing number when it is revised.
