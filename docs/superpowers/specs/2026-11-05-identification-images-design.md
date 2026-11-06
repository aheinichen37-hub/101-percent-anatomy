# Identification images, tips and swipe — design (v2.5)

Date: 2026-11-05 · Status: approved in conversation, awaiting written-spec review

## Goal

Let Andrew learn structures the way he will be tested in lab: by looking at an unlabeled picture with one structure marked and naming it. After every answer he sees the structure labeled; after a miss he also gets a short tip.

## What Andrew asked for

- **Images on** means an unlabeled picture *before* answering, with the target structure marked, like the original Cells decks.
- Figures appear *after* every answer, in both modes.
- Missed identification cards show a short tip: a memory trick, a fun fact, or a "how to tell it apart" note.
- Pre-answer pictures are cropped to the relevant drawing (panel), with nothing in that drawing clipped. If a figure has one heart drawing, the whole heart is shown with only the target glowing.
- The target is marked with a light-blue fill over the whole structure, pulsing between about 10% and 80% opacity (Visible Body style). A circle or arrow is used where a fill can't outline the structure cleanly.
- Swipe left to move to the next card; the Next button stays.

## 1. Deck types and round flow

Every term deck is tagged either **identification** or **concept**.

**Identification decks** (54 decks): `ch1-reg`, `ch1-pl`, `ch1-cav`, `ch1-abd`, `ch1-ser`, `ch4-epi`, `ch4-ct`, `ch5-lay`, `ch5-str`, `ch5-acc`, `ch6-str`, `ch6-cell`, `ch7-skull`, `ch7-vert`, `ch7-thor`, `ch8-pect`, `ch8-arm`, `ch8-pelv`, `ch8-leg`, `ch9-syn`, `ch9-sel`, `ch10-str`, `ch11-head`, `ch11-resp`, `ch11-back`, `ch11-abd`, `ch11-sh`, `ch11-arm`, `ch11-hand`, `ch11-hip`, `ch11-thigh`, `ch11-leg`, `ch12-cell`, `ch13-cns`, `ch13-csf`, `ch13-pns`, `ch13-cn`, `ch14-spec`, `ch18-wbc`, `ch19-anat`, `ch19-cond`, `ch20-str`, `ch20-art`, `ch20-vein`, `ch21-lym`, `ch22-anat`, `ch23-mouth`, `ch23-stom`, `ch23-int`, `ch23-acc`, `ch25-anat`, `ch25-neph`, `ch27-male`, `ch27-fem`.

**Concept decks**: every other term deck. The three original Cells decks (`u1-org`, `u1-fn`, `u1-mit`) keep their existing behavior unchanged.

### Starting a round
- Identification deck → the "Images on / Images off" choice appears.
  - **Images on**: each card shows the pre-answer picture (unlabeled, cropped, target highlighted) above the clue.
  - **Images off**: each card shows the clue only.
- Concept deck → the round starts immediately (no choice). This replaces the v2.4 rule that offered the choice on any deck where 60% of cards had figures.

### Card-level rule
Inside an identification deck, a card has a pre-answer picture only if the image build produced one for it (Section 2). A card without one shows the clue only in both modes. A card is never shown with a broken or blank image.

### After every answer (all decks, both modes)
- **Identification card with images**: the same cropped picture, now with the structure's name placed next to the highlight. Tapping it opens the full labeled textbook figure.
- **Any other card with a textbook figure**: the full textbook figure, as in v2.4.
- **Card with no figure**: nothing, as in v2.4.
- **Miss on an identification card** (wrong twice, or "I don't know"): the card's tip appears under the picture. Correct answers never show the tip.
- **Next card**: swipe left anywhere on the card, or tap Next.

## 2. Image build

A build script runs offline (not in the app) on the figures already extracted to `figs/<number>.jpg` from Andrew's OpenStax A&P 2e PDF, re-rendering from the PDF at higher resolution where text recognition needs it. For each identification card:

1. **Find the label.** Tesseract text recognition reads every label in the card's figure and finds the one matching the card's answer or one of its accepted alternates.
2. **Find the structure.** Follow that label's leader line to its far end; that point is on the structure.
3. **Pick the panel.** Keep the one complete drawing that contains the point. Remove other panels and label columns. Keep a margin so no part of the drawing is clipped.
4. **Erase the labels.** Remove all label text and leader lines inside the crop by filling them with the surrounding background.
5. **Make the highlight.** Trace the structure outward from the point (color-region fill bounded by the drawing's outlines) and save it as a mask. If the fill bleeds past the structure or covers most of the drawing (common for bony landmarks on a uniformly colored bone), fall back in this order: a small local outline around the point, then a circle, then an arrow.
6. **Make the after-answer image.** The same crop plus the structure's name drawn next to the highlight with a leader line.

Outputs per card, in `figs/id/<card-id>`: `-q.jpg` (pre-answer picture), `-m.png` (highlight mask, transparent with the structure in light blue), `-a.jpg` (after-answer labeled picture). The app pulses the mask's opacity from 10% to 80% with CSS.

**Corrections file.** `tools/id-overrides.json` holds hand fixes keyed by card id: a highlight point, a crop box, a forced marker type (`fill`, `outline`, `circle`, `arrow`), or `skip`. The build applies it on every run, so fixes survive rebuilds.

**Review.** Claude visually reviews every generated image in contact sheets and records fixes in the corrections file. A card the build can't handle and that can't be fixed is marked `skip` and falls back to clue-only.

**Size.** About 800 cards × 3 files, compressed (pictures at most 1000 px wide, JPEG quality ~78), estimated at 60–80 MB. That's within GitHub Pages limits, and images load only when a card shows.

## 3. Tips

- **Scope**: every card in the identification decks (about 800). Concept decks get no tips in v2.5. More tips are added later only where Andrew asks for them.
- **Content**: one or two short sentences, each one of the following:
  - a memory trick
  - a "how to tell it apart" note naming the structure most often confused with it
  - a memorable, accurate fun fact
- **Sources**: well-known mnemonics and facts, always reworded in Claude's own words, plus original ones. Nothing is copied verbatim from a website, and nothing is included that isn't anatomically accurate.
- **Storage**: a new optional fifth field on each card line: `Answer | alternates | clue | figure | tip`.
- **Review**: a spreadsheet of every tip (unit, deck, card, tip) saved to Andrew's `Documents/3rd Year/Claude` folder. Andrew marks tips to cut or change.

## 4. App changes, rollout and testing

### App (v2.5)
- Deck data: each `D(...)` deck gets an identification flag; card lines accept the optional tip field.
- Card screen: show the pre-answer picture with the pulsing highlight in identification decks with images on; after answering, show the after-answer picture (tap to enlarge the textbook figure) or the textbook figure; on a miss, show the tip.
- Swipe: a left swipe (at least 60 px, mostly horizontal) on the card area after answering does the same as Next. Swipes before answering do nothing.
- Footer and README say Version 2.5.

### Rollout
1. **Preview**: build `ch11-abd` (Abdominal Muscles), `ch8-arm` (Upper Limb Bones) and `ch19-anat` (Heart Anatomy) with images, tips and swipe. Publish it as a private preview artifact, not to GitHub, so the live app is unchanged while Andrew tests on his phone. Apply his feedback to the pipeline and app.
2. **Full build**: run all identification decks, review every image, and send the tips spreadsheet. Then run the tests, push v2.5 to GitHub and notify Andrew's phone.

### Testing
- The regression test plays identification decks in both modes, checks that tips appear only after a miss, and checks that a left swipe after answering advances (and before answering does not).
- A new image check confirms that every identification card that should have images has all three files, and that none is blank or near-blank.
- Claude reviews every image visually.

## Out of scope for v2.5

- Tips for concept decks.
- Pre-answer pictures for `ch9-mov` (Types of Body Movements), which would need whole-panel views rather than a highlighted structure. Logged in `IDEAS.md`.
- Matching decks to Andrew's guided notes (separate backlog item).
