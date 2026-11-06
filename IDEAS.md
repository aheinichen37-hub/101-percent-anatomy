# Ideas backlog

Side ideas Andrew mentions while we work on something else. Claude adds new ones as they come up and checks this list before starting new work. Move an item to **Done** when it ships, or to **Dropped** if Andrew decides against it.

## Open
- **Swipe to next card** after answering (Next button stays for laptop). Building into the image-design samples to try on a phone. *(2026-11-05)*
- **Tips on missed cards**: short memory tricks, fun facts or "how to tell it apart" notes, shown only when you miss. Andrew reviews each unit's tips before they go live. *(2026-11-05)*
- **Pulsing highlight on structures**: light-blue fill over the whole structure, pulsing about 10–80% opacity, Visible Body style. Part of the pre-answer image design. *(2026-11-05)*
- **Save v2.3 and v2.4 to the claude.ai project** once there's room (the project hit its size limit; remove v1.6, v2.0, v2.1 first). *(2026-11-05)*
- **Match decks to guided notes**: Units 2, 7–9 and 12–28 are written from the OpenStax textbook; adjust each unit to Andrew's guided notes when he has them. *(2026-11-05)*
- **Fix figure mismatches**: Andrew flags any card whose figure looks wrong in `101-anatomy-v2.4-figure-list.csv`. *(2026-11-05)*
- **Pictures for Types of Body Movements** (`ch9-mov`): show the unlabeled movement drawing before answering (no highlight needed). Left out of v2.5. *(2026-11-05)*

### Game-ification (brainstorm started 2026-11-06, nothing built yet)
- **Reliable save on his phone (top priority)**: versioned save with migrations so updates never wipe progress, ask the browser to keep storage permanently, plus a backup option (export/import). Open it from a home-screen icon instead of a Safari link (Safari can clear a site's saved data after about 7 days without use). No phone↔laptop sync for now. *(2026-11-06)*
- **Open it like an app**: make it installable (Add to Home Screen icon, full screen, no browser bar) so it launches like a phone app. *(2026-11-06)*
- **Accounts / cloud login (future, for public use)**: sign-in plus cloud save (Firebase or Supabase). Build the save layer with a swappable storage adapter so local storage can become cloud storage later. *(2026-11-06)*
- **Deck stars**: 3 perfect runs = 3 stars. Typo ("did you mean") answers get full credit. Up to 5 second tries per run, each worth half a point. *(2026-11-06)*
- **Unit mastery check**: 50 randomly selected questions from the unit. Gold at 95% or higher (lose no more than 2.5 points), mastery at 100%. Unlocks once every deck in the unit has 2 stars. Best score is saved. *(2026-11-06)*
- **Unit header tiers in the lobby**: the unit's header changes with achievement. Gold = 95%+ on the mastery check, Diamond = 100% mastery, Ruby = 100% mastery plus 3 stars on every deck (full completion). *(2026-11-06)*
- **Build order decided**: 1) safe save + installable app (next release), 2) deck stars and unit mastery checks, then the rest. *(2026-11-06)*
- **Daily Review**: re-drills the cards you've missed. *(2026-11-06)*
- **Speed Round**: timed random testing. Code later. *(2026-11-06)*
- **Boss Fights**: the mastery check as a boss, possibly themed on each unit's pathologies (osteoporosis for bones, brain cancer for the nervous system, etc.). *(2026-11-06)*
- **Cumulative boss every few units** that mixes earlier material. *(2026-11-06)*
- **Mastery fades** if you don't revisit a unit (optional). *(2026-11-06)*
- **Cell-to-human avatar (back burner)**: one fluid layered silhouette. Each unit fills a slot in the order earned, so textbook order doesn't matter. Decks in a unit unlock sub-parts (e.g. heart chambers, valves, myocardium); overall growth stage from a cell to a human is driven by total stars. *(2026-11-06)*

## Done
- Decks for all 28 units (v2.3, 2026-11-05)
- Textbook figures on 1,545 cards + Images on/off choice (v2.4, 2026-11-05)

## Dropped
