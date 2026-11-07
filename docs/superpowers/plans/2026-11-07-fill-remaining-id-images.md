# Filling the remaining identification images (plan, 2026-11-07)

## Where we are (from `tools/idimg/report.json`, 934 identification cards)

| Lane | Cards | Meaning |
|---|---|---|
| done | 364 | picture built (auto or `id-overrides.json`) |
| locate | 400 | figure exists, build could not find the structure |
| needs-fig | 170 | card has no textbook figure at all |

Full per-card list: `tools/idimg/worklist.csv` (regenerate with `python3 tools/idimg/worklist.py`).

## Tooling decision

- **Engine stays local**: Pillow, OpenCV, scikit-image, Tesseract, poppler are all installed and fast, and the build is reproducible. No new connector or skill is needed for the image work itself.
- **Adobe connector: not used.** Tried 2026-11-06 and judged not useful; its selection tools target everyday objects in photos, not structures in textbook line drawings, and every image would need uploading first.
- **The bottleneck is locating the structure**, not editing pixels. Two systematic causes found:
  1. *Label sits on the structure, no leader line* (e.g. Fig 1.16 abdominopelvic regions, quadrants). OCR also misses these bold labels over a colored picture. Fix: hand point, or a "label box centre is the point" mode.
  2. *Two-name / wrapped labels* (e.g. Fig 1.12 "Frons or forehead (frontal)"). OCR merges neighbouring rows, and cards use the English term inside the parentheses. Fix: split merged rows, match parenthetical terms.
- Cards like Anatomical position, Prone, Supine are concepts with no structure to mark: lane `skip` (clue only), not a failure.

## Per-figure workflow (hand lane)

1. Render the figure with a numbered pixel grid and the OCR label index overlaid.
2. Read each card's point off the grid, write `{"fig": ..., "point": [x, y]}` into `tools/id-overrides.json`.
3. Rebuild that deck, view the contact sheet, correct misses.
4. `python3 tools/regress.py index.html --quick`.

## Order of work

1. Decks with zero pictures: ch1-reg (47), ch1-abd (13), ch1-ser, ch13-cn, ch18-wbc, ch23-acc, ch25-neph.
2. Largest `locate` backlogs: ch4-epi, ch4-ct, ch10-str, ch20-art, ch20-str, ch12-cell.
3. `needs-fig` decks last, once the missing textbook pages are supplied.

Each batch ships as its own version (3.2, 3.3, ...) after `--full` regression.

## Blocker

The textbook PDF is not in this cloud session (`figures.pdf_available()` is False). It lives in Andrew's `Documents/3rd Year/Claude` folder on his computer. Needed for the 170 `needs-fig` cards and for higher-resolution re-renders where OCR struggles.

## Update: textbook scan (2026-11-07, later)

The textbook PDF is now reachable (it is the full 1,347-page book despite the "1-100" in the file name). Method: OCR every page in the relevant chapters (551 pages, about 7 minutes on 2 cores), search each of the 170 no-figure cards' terms, keep only hits that fall inside a figure image, then review every hit by eye.

- 163 of 170 cards had the term somewhere in the OCR; only 80 were inside a figure image, and about 75 of those are real labels on a drawing (the rest are table cells or look-alike words, for example Geniohyoid for Genioglossus, Thrombin for Thrombopoietin).
- Candidates are in `tools/idimg/book-candidates.csv`. Several sit in figures the app already has (kidney Fig 25.8, teeth, soft palate); 11 figures are not in the app yet (for example the cranial nerves, Fig 13.23).
- About 95 cards have no drawing to find: hormones, phases, diseases and other concepts (Gastrin, Polyuria, Heart block). They stay clue-only or move to concept decks.
- Next: add the missing figures to `figs/` and `caps.json`, point each candidate card at its figure via a `fig` override, rebuild those decks, review contact sheets, run `--quick` regression, release as 3.2.
