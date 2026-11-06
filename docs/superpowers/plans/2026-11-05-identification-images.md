# Identification Images, Tips & Swipe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v2.5 of 101% Anatomy. Identification decks show an unlabeled, cropped picture with the target structure pulsing in light blue before you answer; every card shows its figure after you answer; misses on identification cards show a tip; swiping left goes to the next card.

**Architecture:** An offline Python build (`tools/idimg/`) turns each identification card's textbook figure into three files: a pre-answer picture, a highlight mask and an after-answer labeled picture. It uses Tesseract to find labels, follows the label's leader line to the structure, crops to its panel, erases labels, and fills the structure. A corrections file overrides any card. Tips live as a fifth field on card lines, sourced from `tools/tips.csv`. The single-file app (`index.html`) reads these files. A preview with three decks is published as a private artifact for Andrew's checkpoint before the full build.

**Tech Stack:** Python 3 with Pillow, NumPy, SciPy, scikit-image, OpenCV (`cv2`) and pytesseract/Tesseract; pdfplumber and pypdfium2 for re-rendering from the PDF. pytest for unit tests. Plain HTML/CSS/JS app. Playwright (Python) for app and regression tests.

**Spec:** `docs/superpowers/specs/2026-11-05-identification-images-design.md`

## Global Constraints

- Version: `Version 2.5` in the page footer, the CSS comment and `README.md`. The preview is labeled `Version 2.5-preview`.
- Identification decks are exactly the 54 IDs in spec §1. Every other term deck is a concept deck. `u1-org`, `u1-fn` and `u1-mit` keep their current behavior.
- The highlight color is light blue `#4fd4ff`. The opacity pulse is 0.10 → 0.80 → 0.10, 1.6 s, ease-in-out, infinite. Pulsing is disabled under `prefers-reduced-motion` (fixed at 0.45).
- Marker fallback order: `fill` → `outline` → `circle` → `arrow`. A fill is rejected if its area exceeds 35% of the panel or if it leaks past the panel edge.
- Output files per card: `figs/id/<card-id>-q.jpg`, `figs/id/<card-id>-m.png`, `figs/id/<card-id>-a.jpg`. Pictures are at most 1000 px wide, JPEG quality 78. The mask is a PNG with alpha, the same size as `-q.jpg`.
- Card line format: `Answer | alternates | clue | figure | tip`. All fields after the clue are optional.
- Tips are one or two sentences, in Claude's own words, and anatomically accurate. Each is a memory trick, a tell-apart note, or a fun fact.
- Swipe: a left swipe of at least 60 px, with horizontal travel more than 1.5× vertical, advances only when the card is answered.
- Source PDF: `/mnt/user-data/uploads/Claude/a&p open stax 1-100.pdf`. Re-stage it from Andrew's Mac (`/Users/andrewheinichen/Documents/3rd Year/Claude/`) if the session lost it. Figure captions and page numbers come from `tools/idimg/caps.json`, produced by Task 2.
- Release flow (repo `CLAUDE.md`): run the regression test, push to GitHub `main`, notify Andrew's phone.

## Review Focus

- **A label split over two lines in the figure** (for example "Rectus" / "abdominis") must still match the answer. Task 2's test uses `11.16` / rectus abdominis.
- **An answer labeled twice in one figure** (left and right, or two views) must pick one consistent label and never highlight both halves of a mismatched pair. Task 2 test: choose the label whose leader line is longest-in-panel and deterministic across runs.
- **A figure that labels a structure by an alternate name** (for example "Achilles tendon" for the calcaneal tendon) must match through the card's alternates. Task 2 test with `11.32`, the lower leg.
- **A vertical scroll on a phone** must not count as a swipe, and a swipe while the zoom view or a modal is open must not advance. Task 5 tests.
- **A tall pre-answer picture on a small phone** must not push the answer box or the Next button off screen or cover them. The regression test's on-screen and not-covered checks run on identification decks with images on (Task 7).

---

### Task 1: Card data — identification flag and tip field

**Files:**
- Modify: `index.html`: `D()` parser, deck registry, `IDDECKS` constant
- Test: `tools/tests/test_app_data.py`

**Interfaces:**
- Produces (JS, global): `IDDECKS: Set<string>` (the 54 IDs); `DECKS[id].ident: boolean`; each card item gains `tip: string|undefined`; helper `idFiles(item) -> {q,m,a}|null`, which returns `null` unless `IDIMG.has(item.id)`; `IDIMG: Set<string>`, the card IDs with built images (empty until Task 4 writes it).

- [ ] **Step 1: Write failing test** `test_id_flags_and_tips` (Playwright, loads `index.html`):
  - `IDDECKS.size === 54`, and `DECKS['ch11-abd'].ident === true`, `DECKS['ch12-ap'].ident === false`, `DECKS['u1-org'].ident` is falsy.
  - Inject a deck via `D('t-x','ch1','T','q','-', "A | b | c | 1.12 | tip text\nB | | d")` and assert `items[0].tip === 'tip text'`, `items[0].fig === '1.12'`, `items[1].tip === undefined`.
  - `idFiles(DECKS['ch11-abd'].items[0]) === null` while `IDIMG` is empty.
- [ ] **Step 2:** Run `python3 -m pytest tools/tests/test_app_data.py -v`. Expected: FAIL (`IDDECKS` is not defined).
- [ ] **Step 3: Implement.** In `D()`, read `p[4]` as `tip` (trimmed, `undefined` if empty). Add `const IDDECKS=new Set([...54 ids from spec §1...])` and `const IDIMG=new Set([])` above the deck registration. Set `d.ident=IDDECKS.has(d.id)` in the existing `NEWDECKS.forEach`. Remove the v2.4 `d.imgOpt` 60% rule. `idFiles` returns `{q:'figs/id/'+id+'-q.jpg', m:'…-m.png', a:'…-a.jpg'}`.
- [ ] **Step 4:** Run the test. Expected: PASS.
- [ ] **Step 5:** Commit `feat: identification deck flag and tip field`.

### Task 2: Label finding, leader-line tracing, panel crop, label erase

**Files:**
- Create: `tools/idimg/__init__.py`, `tools/idimg/labels.py`, `tools/idimg/panel.py`, `tools/idimg/caps.json` (the figure caption/page map, copied from the v2.4 extraction)
- Test: `tools/tests/test_labels.py`

**Interfaces:**
- Produces:
  - `render_figure(fig: str, scale: float=3.0) -> PIL.Image`: re-renders the figure's region from the PDF using the same caption-anchored crop as v2.4 (`/home/claude/figwork/extract.py` logic), at the higher scale, for better text recognition.
  - `find_labels(img) -> list[Label]`: `Label(text:str, box:(x0,y0,x1,y1))`. Joins words on adjacent lines into one label when they are left-aligned within 8 px and less than 1.6 line-heights apart.
  - `match_label(labels, terms: list[str]) -> Label|None`: normalized match (lowercase, alphanumerics only, `fi`/`fl` ligatures folded), exact first, then Levenshtein ≤ 1 for terms longer than 6. Terms are the card answer plus its alternates.
  - `trace_leader(img, label) -> (x:int,y:int)|None`: finds the thin dark line starting within 12 px of the label box's nearest edge, follows it with a skeleton walk, and returns the far endpoint.
  - `panel_box(img, point) -> (x0,y0,x1,y1)`: the connected non-background region containing `point` after removing label text and lines, padded 12 px and clamped to the image.
  - `erase_labels(img, labels, lines) -> PIL.Image`: fills label boxes and leader-line pixels from the local background (`cv2.inpaint`, TELEA, radius 3).

- [ ] **Step 1: Write failing tests:**
  - `test_two_line_label`: on `render_figure('11.16')`, `match_label(find_labels(img), ['Rectus abdominis'])` is not `None`.
  - `test_alternate_name`: on `11.32`, `match_label(..., ['Calcaneal tendon','achilles tendon'])` is not `None`.
  - `test_leader_lands_on_structure`: for `19.9` / `['Left atrium']`, the traced point lies inside the drawing (non-background pixel, more than 40 px from every label box).
  - `test_panel_excludes_other_panels`: for `11.16` / rectus abdominis, the panel box does not contain the pelvic-floor panel's center, taken from the figure's second-largest connected region.
  - `test_duplicate_label_deterministic`: two runs pick the same label box for `8.6` / `['Ulna']`.
  - `test_erase_leaves_no_text`: after erasing, `find_labels` on the cropped panel returns no label with three or more letters.
- [ ] **Step 2:** Run `python3 -m pytest tools/tests/test_labels.py -v`. Expected: FAIL (module not found).
- [ ] **Step 3:** Implement the five functions above in `labels.py` and `panel.py`. Tesseract config: `--psm 11`, keeping words with confidence ≥ 55.
- [ ] **Step 4:** Run the tests. Expected: all PASS. If a figure-specific case can't pass with general rules, that card goes to the overrides file in Task 4. The test stays, marked `xfail` with the override name.
- [ ] **Step 5:** Commit `feat(idimg): label find, leader trace, panel crop, erase`.

### Task 3: Highlight mask, fallbacks, after-answer image

**Files:**
- Create: `tools/idimg/highlight.py`
- Test: `tools/tests/test_highlight.py`

**Interfaces:**
- Consumes: Task 2's cropped, erased panel and the point (in panel coordinates).
- Produces:
  - `make_mask(panel_img, point, force: str|None=None) -> (mask: PIL.Image 'L', kind: str)`. `kind` is one of `fill|outline|circle|arrow`.
    - fill: flood fill in Lab color space, tolerance ΔE ≤ 14, bounded by dark outlines (L < 35), then one closing and one dilation pass of 2 px.
    - outline: the fill limited to a 70 px radius around the point.
    - circle: a 6 px ring of radius 28.
    - arrow: a 60 px arrow pointing at the point from the side with the most free space.
  - `mask_png(mask) -> PIL.Image RGBA`: color `#4fd4ff`, alpha = mask.
  - `answer_image(panel_img, mask, kind, name) -> PIL.Image`: overlays the mask at 45% opacity and draws `name` in IBM Plex Sans–like system font, 28 px, black on a white rounded box, placed in the nearest free margin with a 2 px leader line to the point.

- [ ] **Step 1: Write failing tests:**
  - `test_fill_bounded`: for the `11.16` rectus abdominis panel, `kind=='fill'` and the mask area is between 2% and 35% of the panel.
  - `test_landmark_falls_back`: for `8.5` / `['Deltoid tuberosity']`, `kind` is in `{'outline','circle','arrow'}`.
  - `test_force_kind`: `make_mask(..., force='circle')[1]=='circle'`.
  - `test_answer_image_size`: `answer_image` returns the same size as the panel.
- [ ] **Step 2:** Run `python3 -m pytest tools/tests/test_highlight.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement `highlight.py` per the interfaces.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit `feat(idimg): highlight mask with fallbacks and answer image`.

### Task 4: Build runner, overrides, image check, contact sheets

**Files:**
- Create: `tools/idimg/build.py`, `tools/id-overrides.json` (starts as `{}`), `tools/check_id_images.py`, `tools/idimg/sheets.py`
- Modify: `index.html` (the `IDIMG` set is written by the build)
- Test: `tools/tests/test_build.py`

**Interfaces:**
- Consumes: Tasks 2–3; card data parsed from `index.html` (reuse the regex from `/home/claude/figwork/match.py`).
- Produces:
  - CLI `python3 tools/idimg/build.py --decks ch11-abd,ch8-arm,ch19-anat` (or `--all`). It writes `figs/id/*`, rewrites `const IDIMG=new Set([...])` in `index.html` with every card that got all three files, and writes `tools/idimg/report.json` (`{card_id:{kind, fig, status: ok|skip|fail, reason}}`).
  - Override schema per card ID: `{"point":[x,y], "crop":[x0,y0,x1,y1], "kind":"fill|outline|circle|arrow", "label":"text to match", "skip":true}`, in coordinates of `render_figure(fig, 3.0)`.
  - `python3 tools/check_id_images.py` exits 0 only if every ID in `IDIMG` has all three files, every `-q.jpg` has a pixel standard deviation of at least 12 (not blank), and every mask has nonzero alpha.
  - `python3 tools/idimg/sheets.py --decks …` writes `tools/idimg/sheets/<deck>.jpg`: a grid of each card's `-q` with mask over `-a`, captioned with the card ID and kind, for visual review.

- [ ] **Step 1: Write failing tests:**
  - `test_override_skip`: with `{"ch11-abd-0":{"skip":true}}`, the build leaves `ch11-abd-0` out of `IDIMG`, and its report status is `skip`.
  - `test_override_kind`: forcing `circle` gives report `kind=='circle'`.
  - `test_check_detects_blank`: a 1000×600 all-white `-q.jpg` makes `check_id_images.py` exit 1.
- [ ] **Step 2:** Run `python3 -m pytest tools/tests/test_build.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement `build.py`, `check_id_images.py` and `sheets.py`.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Run the build on the three preview decks, generate their sheets, and review every image by eye. Record fixes in `tools/id-overrides.json` and rebuild until every card is right or marked `skip`. Then run `python3 tools/check_id_images.py`. Expected: exit 0.
- [ ] **Step 6:** Commit `feat(idimg): build runner, overrides, image check` with `figs/id/` for the three decks.

### Task 5: Card screen — pre-answer highlight, after-answer figure, tip, swipe

**Files:**
- Modify: `index.html` (CSS block; `unitPage` click rule; `chooseMode` copy; `playPage`; new `bindSwipe()`)
- Test: `tools/tests/test_app_play.py`

**Interfaces:**
- Consumes: `DECKS[id].ident`, `item.tip`, `idFiles(item)` (Task 1).
- Produces: DOM hooks for tests: `#qimg` (pre-answer wrapper), `#qimg .hl` (mask `<img>` with class `pulse-hl`), `#aimg` (after-answer button that opens the zoom on the textbook figure), `#tip` (tip paragraph).

- [ ] **Step 1: Write failing tests** (Playwright, 390×664 touch viewport, served over `http.server` so `figs/` loads):
  - `test_ident_asks_mode`: tapping `ch11-abd` shows `#img-on`, and tapping `ch12-ap` starts a round directly (`round` exists, no `#img-on`).
  - `test_preanswer_image_on`: in `ch11-abd` with images on, for a card in `IDIMG`, `#qimg` is visible before answering, `#aimg` isn't, and the mask has computed `animation-name` `pulseHL`.
  - `test_images_off_hides_preanswer`: with images off, there's no `#qimg` before answering, but `#aimg` appears after answering.
  - `test_tip_only_on_miss`: a correct answer shows no `#tip`; answering "zzzz" twice shows `#tip` with the card's tip text; "I don't know" shows `#tip`.
  - `test_swipe_advances_after_answer`: dispatching touch events (start 300,400 → end 200,410) after answering moves `round.i` by 1. The same swipe before answering does not.
  - `test_vertical_scroll_not_swipe`: touch 200,500 → 170,300 after answering does not advance.
  - `test_swipe_ignored_with_zoom_open`: with the zoom view open, a left swipe does not advance.
  - `test_concept_after_answer_figure`: in `ch12-ap`, a card with a figure shows the textbook figure after answering, as in v2.4.
- [ ] **Step 2:** Run `python3 -m pytest tools/tests/test_app_play.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - Click rule: `fn || ident` opens `chooseMode`. Identification copy: "Images on" → "See the structure before you answer", "Images off" → "Clue only".
  - Pre-answer (`ident && round.images && idFiles(item)`): a `#qimg` wrapper, relatively positioned, holds `-q.jpg` with the mask `<img class="hl pulse-hl">` absolutely positioned to match it.
  - After answer (any mode): if `ident && idFiles(item)`, show `#aimg` with `-a.jpg`, which opens the zoom on `figs/<fig>.jpg`. Otherwise use the v2.4 figure logic, minus the `round.images` gate, so concept figures always show.
  - `#tip` renders when `state==='done' && round.missed-or-gaveup-on-this-card && ident && item.tip`. Track `round.lastMissed` in `grade` and `giveUp`.
  - CSS: `@keyframes pulseHL{0%,100%{opacity:.10}50%{opacity:.80}}`, `.pulse-hl{animation:pulseHL 1.6s ease-in-out infinite}`, and under `prefers-reduced-motion`, `.pulse-hl{animation:none;opacity:.45}`.
  - `bindSwipe()` on `#app` with touchstart/touchend. It advances when `round.state==='done'`, `#modalSlot` is empty, `dx<=-60` and `|dx|>1.5*|dy|`.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit `feat: identification pre-answer images, tips, swipe`.

### Task 6: Tips — authoring, apply script, spreadsheet

**Files:**
- Create: `tools/tips.csv` (columns `card_id,unit,deck,answer,tip`), `tools/apply_tips.py`
- Modify: `index.html` (card lines gain a fifth field)
- Test: `tools/tests/test_tips.py`

**Interfaces:**
- Produces: `python3 tools/apply_tips.py` writes each tip from `tips.csv` into its card's fifth field. It pads an empty figure field as `-` when needed and never touches cards outside the CSV. It is idempotent.

- [ ] **Step 1: Write failing tests:**
  - `test_apply_idempotent`: running twice leaves `index.html` byte-identical to running once.
  - `test_tip_rules`: every tip in `tips.csv` has at most two sentences and 220 characters, contains no `|` or backtick, and its `card_id` exists and belongs to an identification deck.
  - `test_no_answer_in_tip`: for each row, the tip doesn't contain the card answer.
- [ ] **Step 2:** Run `python3 -m pytest tools/tests/test_tips.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement `apply_tips.py`. Write tips for the three preview decks into `tips.csv`, following the Global Constraints tip rules.
- [ ] **Step 4:** Run the tests. Expected: PASS. Run `apply_tips.py`.
- [ ] **Step 5:** Commit `feat: tips for preview decks`.

### Task 7: Regression test update

**Files:**
- Create: `tools/regress.py`, a copy of the project's `claude/101-anatomy-regression-test.py`, which becomes the repo's source of truth
- Test: the script itself

- [ ] **Step 1:** Change deck discovery to `Object.values(DECKS).map(d=>[d.id,!!(d.fn||d.ident)])` so identification decks play in both modes. Serve the repo over `http.server` and load `index.html` by URL, so images load and on-screen checks include real image heights.
- [ ] **Step 2:** After each answer on an identification deck, assert: `#tip` is present exactly when the card was missed and has a tip; `#aimg` is present when `idFiles(item)` is not null.
- [ ] **Step 3:** For every fourth card, advance with a synthetic left swipe instead of tapping `#next`. This keeps the existing on-screen and not-covered checks for `#next` on all other cards.
- [ ] **Step 4:** Run `python3 tools/regress.py index.html`. Expected: `RESULT: PASS`.
- [ ] **Step 5:** Commit `test: regression covers identification images, tips, swipe`. Upload `tools/regress.py` to the project path `claude/101-anatomy-regression-test.py`.

### Task 8: Preview checkpoint (Andrew)

**Files:**
- Create: a preview copy (scratchpad), with `Version 2.5-preview` and a lobby limited to Units 8, 11 and 19

- [ ] **Step 1:** Load the `artifact-design` skill. Build the preview page from `index.html`, set `Version 2.5-preview`, and limit the `UNITS` array to `ch8`, `ch11` and `ch19`.
- [ ] **Step 2:** Publish it as a private artifact with `files` mapping `figs/id/<preview cards>*` and the textbook figures those decks use. Confirm the file count is under 255 per publish, splitting into multiple publishes to the same URL if needed.
- [ ] **Step 3:** Send Andrew the link with what to try: images on and off, a deliberate miss to see a tip, a swipe, and tapping the after-answer picture. Send a phone notification.
- [ ] **Step 4: STOP.** Collect Andrew's feedback, then apply changes to the pipeline (Tasks 2–4), the app (Task 5) or the tips (Task 6) with their tests. Re-publish and repeat until Andrew says the samples are right. Log any new side ideas in `IDEAS.md`.

### Task 9: Full build — all identification decks

- [ ] **Step 1:** Run `python3 tools/idimg/build.py --all` and `python3 tools/idimg/sheets.py --all`.
- [ ] **Step 2:** Review every contact sheet by eye, deck by deck. Record fixes in `tools/id-overrides.json` and rebuild the affected decks until every card is correct or `skip`.
- [ ] **Step 3:** Run `python3 tools/check_id_images.py`. Expected: exit 0.
- [ ] **Step 4:** Write tips for the remaining 51 identification decks in `tools/tips.csv`. Run `python3 -m pytest tools/tests/test_tips.py -v` (expected: PASS) and `apply_tips.py`.
- [ ] **Step 5:** Export the tips spreadsheet (`101-anatomy-v2.5-tips.csv`: unit, deck, answer, tip) and commit it to Andrew's Mac at `/Users/andrewheinichen/Documents/3rd Year/Claude/`.
- [ ] **Step 6:** Commit `feat: identification images and tips for all decks`.

### Task 10: Release v2.5

- [ ] **Step 1:** Set `Version 2.5` in the footer, the CSS comment and `README.md`. Move the shipped items in `IDEAS.md` to **Done**.
- [ ] **Step 2:** Run all unit tests, `python3 tools/check_id_images.py` and `python3 tools/regress.py index.html`. Expected: all PASS.
- [ ] **Step 3:** Push to GitHub `main`, upload the regression test to the project, and send Andrew a phone notification.
