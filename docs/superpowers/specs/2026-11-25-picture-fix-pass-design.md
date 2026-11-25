# 3.8.3 picture fix pass (spec, approved by Andrew 2026-11-25)

## Problem
Playing the skull and vertebral decks on his phone, Andrew found identification pictures that
(1) still show the answer (Dens, Coccyx) or another card's label (Pterion), and
(2) put the blue spot on a leader line's label end instead of the structure (Squamous suture,
Anulus fibrosus, Zygomatic arch). The v2.7 build read labels by OCR and followed leader lines;
both steps miss. `tools/idimg/scan_pics.py` v1.0.0 flags 121 of the 291 textbook pictures.

## Decisions (Andrew)
- Fix pass before the 3.9.0 review engine; review **all 291** textbook pictures by eye, not only the flagged ones.
- A picture that can't be made fully honest **keeps the picture with the word covered by a box** (no fallback to clue only).
- 3D renders for landmarks: parked in `IDEAS.md`.
- The 162 BodyParts3D renders are out of scope (they carry no labels and were placed per structure).

## Design
- `tools/id-fixes.json`: per card, in before-answer picture pixels:
  `{"cover": [[x0,y0,x1,y1], ...], "spot": [x,y], "note": "..."}`. `spot` is optional (keeps the current one).
- `tools/idimg/patch_pics.py` v1.0.0 rebuilds `-q.jpg`, `-m.png` and `-a.jpg` for each listed card from the
  3.8.2 originals (git commit `5f2682e`), so running it twice gives the same files. Covers are white boxes
  like the build's own; the spot and the name plate are drawn with the build's own `highlight` functions.
- Card IDs, deck text and the save are untouched; this release changes pictures only.

## Checks
- `scan_pics.py` after the pass: no "answer" or "label" flags left except ones reviewed and noted as false.
- New pytest: patching is repeatable; every fix names a built card; covers and spots lie inside the picture;
  a patched card's three files share one size.
- The usual four release checks.

## Outcome (2026-11-25)
- 291 textbook pictures reviewed on contact sheets; 162 changed (covers and/or spots), 6 more carry a note only.
- After the pass `scan_pics.py` reports 0 answer leaks, 0 spots on the rim; the 10 remaining "label" hits are OCR noise from drawing texture ("Yooy", "SARS"), checked by eye.
- Slanted text on coloured shapes (the eye-muscle arrows) is covered with a polygon in the shape's own colour.
- Not fixable by a spot move, noted in `tools/id-fixes.json`: Lower esophageal sphincter (not in its figure), Lesser trochanter (outside the crop), hair Medulla/Cortex/Cuticle (the drawing only marks the hair).
