# 101% Anatomy

A trivia-style study game for Anatomy & Physiology (OpenStax A&P 2e, EXSC 2061). Pick a unit, choose a deck, and type your answers — with "did you mean" suggestions for near-misses.

**Play it:** https://aheinichen37-hub.github.io/101-percent-anatomy/

Current version: 3.3

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
