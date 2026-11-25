# 101% Anatomy

A trivia-style study game for Anatomy & Physiology (OpenStax A&P 2e, EXSC 2061). Pick a unit, choose a deck, and type your answers — with "did you mean" suggestions for near-misses.

**Play it:** https://aheinichen37-hub.github.io/101-percent-anatomy/

Current version: 3.8.2

## Small fixes (3.8.2)

- After a deck, the results screen's **Back to the unit** button returns to that deck's unit page
  (the skull deck goes back to Axial Skeleton), like the mastery check already did.
- **A wrong number is just wrong.** "Did you mean" never offers an answer whose number differs from
  the one you typed, so typing 13 for the 12 pairs of ribs counts as a wrong try instead of being
  corrected. Spelling help still works around a right number ("G1 phse" → G1 phase).

## Locked card IDs (3.8.1)

Your progress remembers cards by ID, and most IDs are a card's line number in its deck, so a moved
line would hand one card's progress to another. 3.8.1 locks every ID in `tools/card-ids.json` and
`tools/tests/test_card_ids.py` fails if one moves. When editing decks: **add new cards at the end**,
**retire a card by starting its line with `~`** (its slot keeps its number), and after a real answer
fix or a new card run `python3 tools/card_ids.py --update` and read the summary it prints. Nothing
changes on screen.

## Unit mastery check (3.8.0)

Every unit page has a **Mastery check**. It unlocks once every deck in the unit has 2 or more stars,
then asks 50 random cards pooled from all the unit's decks (a unit with fewer uses them all), typed
and scored like a normal round: first try 1 point, second try half, miss 0. **Gold** is 95% or more,
**Diamond** is a perfect 100%, and **Ruby** is a perfect check plus 3 stars on every deck. Retake any
time; your best score counts and a worse retake never lowers it. The tier shows on the unit page and
the lobby tile. Checks are saved as rounds of kind "check", so the save format is unchanged and the
deck stats and stars ignore them.

## Deck stars (3.7.0)

Every typed deck earns up to three stars from its best typed run: **50%** is 1 star, **80%** is 2,
and **3 stars needs a perfect run**, every card right on the first try (a second try is half a
point, so it costs the third star; a "did you mean" spelling correction costs nothing). Stars
show on each deck tile and the results page announces a new one. They are worked out from your
saved rounds, so they never go down and need no new save format; multiple choice never earns stars.
Two stars on every deck in a unit will unlock that unit's mastery check (not built yet).

## Multiple choice study mode (3.5.0)

Tap any deck and pick **Type it** (the real test: high scores, and later stars and mastery
checks) or **Multiple choice** (a study method). A multiple-choice card shows four choices: the
right answer plus three other answers from the same deck (small decks borrow from the same unit).
Tap one and it turns green if right or red if wrong, then Next. A card is **ready** after two right
answers in a row; a miss sends it back to zero. Each deck tile shows a light-grey readiness bar.
Number answers (46, 206, 120 days, -70 mV, a pH range) get other numbers as wrong choices, never names.
Study rounds never change high scores or the stats line. Streaks are saved in the browser with the
rest of your progress (save format 3; older saves load fine).

### Wrong choices come from the same family (3.6.0)

Each card has an answer *group* (a bone such as humerus, a family such as suture, or "bones" for whole
bones). A landmark on the humerus gets other humerus landmarks as wrong choices, never a carpal bone;
a whole bone gets other whole bones. Now and then one choice comes from a neighbouring family. Cards
and decks without a group behave as before. `python3 tools/groups.py` lists weak questions and
decks that still need groups; fixes go in `tools/groups-overrides.json`, then `--apply`.
For another course, swap `GROUP_HOSTS` in `index.html` and start a fresh overrides file.

## Identification decks

Fifty-four decks ask you to name a structure from a picture, the way a lab practical
does. With images on, the card shows the drawing cropped to the right region, with the
label text covered and the structure marked in blue; answer, and the same picture comes
back with its name on it, tapping through to the full textbook figure. Miss a card and a
short tip appears. Swipe left on an answered card to move on.

Some cards are placed by hand, in `tools/id-overrides.json`: `fig` borrows a better drawing
than the card's own, and `point` marks the structure's spot in that figure's pixels. Every
Unit 11 muscle that has a labelled drawing in the book is done this way. The rest are listed in
`IDEAS.md` under "Diagrams still needed".

Cards whose structure could not be located in the textbook figure show the clue alone,
and coverage varies a lot by deck. Each deck tile carries two dots in its corner so you
can see what you are getting before you open it: the first is the kind of deck
(identification, what-it-does, or term), the second is what pictures it has (one shown
before you answer, a figure after you answer, or none).

## Your progress

Progress is stored in the browser you play in, and it survives every update: each save
carries a version number, and a new version upgrades an old save instead of discarding it.

**Put it on your home screen.** On iPhone, open the link in Safari, tap **Share**, then
**Add to Home Screen**. Safari can clear a plain website's data after about a week of not
using it; a home-screen app isn't cleared that way, and it opens full screen and works
offline. The home-screen app keeps its *own* save, so back up from Safari once and restore
it there (below).

**Back up and restore.** Menu → **Save & backup**. That sheet shows whether saving is
working, when it last saved, and how much is stored. Download a backup file or copy the
code, then restore it on another browser or device. Restoring only adds what's missing —
it never deletes a round you already have.

If the browser ever refuses to store the save (private browsing, a full phone), a red bar
appears at the top of the app instead of failing silently, and it links to the backup sheet.

## Credits

- Textbook figures: OpenStax *Anatomy & Physiology 2e*, CC BY 4.0, labels removed.
- Muscle and bone pictures: rendered from BodyParts3D, (c) The Database Center for Life Science, licensed under CC BY-SA 2.1 Japan (http://lifesciencedb.jp/bp3d/). Mitsuhashi N, et al. BodyParts3D: 3D structure database for anatomical concepts. Nucleic Acids Res. 2009;37:D782-5. https://doi.org/10.1093/nar/gkn613. The models were re-rendered and recolored for this app (tools/anat3d); those pictures are shared under CC BY-SA.
