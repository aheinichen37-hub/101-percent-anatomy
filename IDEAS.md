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

### Identification images — known gaps (v2.7)
- **Coverage is thin and uneven.** After the matcher improvement: see the build report. Ten decks had none at all before it. The dominant cause is a card whose answer is a grouping the figure never prints, e.g. "Pectoral girdle" where Figure 8.3 labels only Clavicle and Scapula. Per-card overrides in `tools/id-overrides.json` are the lever. *(2026-11-06)*
- **Earlier note: about half of cards get a picture.** The rest have no matching label in the figure, or no leader line that can be traced. They fall back to the clue, which is the specified behaviour. Worth revisiting with per-card overrides in `tools/id-overrides.json`. *(2026-11-06)*
- **The highlight is a patch, not the structure's shape.** Flood-filling the actual structure took the rectus sheath instead of the muscle, so it was dropped in favour of something that cannot be wrong in that way. A shaped highlight is still the nicer end state. *(2026-11-06)*
- **Tips exist for the Heart Anatomy deck only** (25 cards). The mechanism handles the other 53 decks whenever tips are written. *(2026-11-06)*
- **Multi-panel figures** still sometimes include a neighbouring inset in the crop. *(2026-11-06)*

### Game-ification (brainstorm 2026-11-06; the save is built, the rest is not)
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

### Diagrams still needed (Unit 11, head and neck down) — Andrew to find; then add as figures and I mark the spots *(2026-11-06)*
- **Head & Neck (`ch11-head`)**: a face-muscles drawing labelled with Orbicularis oculi, Occipitofrontalis, Buccinator, Zygomaticus major, Levator labii superioris, Depressor anguli oris, Mentalis, Platysma; a tongue/floor-of-mouth drawing with Genioglossus; the six extrinsic eye muscles (Superior/Inferior/Lateral/Medial rectus, Superior/Inferior oblique).
- **Respiratory (`ch11-resp`)**: Serratus posterior superior and inferior (posterior trunk), Transversus thoracis (inside of the anterior chest wall).
- **Back (`ch11-back`)**: a drawing that shows Erector spinae as the group (iliocostalis, longissimus, spinalis side by side).
- **Shoulder (`ch11-sh`)**: Coracobrachialis; a rotator cuff drawing showing all four muscles together.
- **Hip (`ch11-hip`)**: Psoas minor; Iliopsoas as the joined muscle.
- **Thigh (`ch11-thigh`)**: Vastus intermedius (the deep one between lateralis and medialis); the quadriceps and hamstring groups outlined as groups.
- **Lower leg (`ch11-leg`)**: nothing missing; Gastrocnemius, Soleus, Calcaneal tendon and the front four have pictures.
- **Fix later, once the app is settled**: the forearm-extensor spots (Extensor digitorum, Digiti minimi, Carpi ulnaris, pollicis longus/brevis) sit a few pixels apart, so check each one; Orbicularis oris is a tiny muscle under a large blob; Semitendinosus and Semimembranosus leaders end close together.
- **Bony landmarks (Units 7–8)**: 74 now have hand-placed pictures (v3.0). Still without a picture: Cranium, Facial bones, Hyoid bone, Temporal bone, Coracoid process (spots looked wrong; need a drawing that shows them), plus the group cards. Diagrams wanted: ribs and rib classification, thoracic cage, pelvic girdle and female pelvis, primary/secondary spinal curves, paranasal sinuses as a group, sternoclavicular joint. Fix later: Phalanges spot sits on the thumb, Linea aspera and Coracoid need better views.

### Regression test (brainstorm 2026-11-07)
- **Run the test on Andrew's gaming PC** through the Claude desktop app link (more cores means more useful tabs; `--tabs auto` already scales). Needs Python and Playwright installed there and a connected folder. Only worth it if the cloud run (about 40 s full) ever gets slow. *(2026-11-07)*
- **Per-card timing log** (a `--timing` flag) in case a deck ever turns slow, for example from heavy pictures. *(2026-11-07)*
- **Mirror the test into the claude.ai project as `claude/101-anatomy-regression-test-v2.0.py`** once there's room (the project is over its size limit; the old v1 copy there is out of date). *(2026-11-07)*

## Done
- Regression test 2.0: parallel tabs, `--quick` / `--full` / `--units` / `--changed`, seeded runs; full check about 40 s, quick about 6 s (2026-11-07)
- Hand-fixed pictures for 74 bone cards (skull, vertebrae, thorax, arm, pectoral, pelvis, leg); Adobe connector tried and not useful here (v3.0, 2026-11-06)
- Hand-fixed pictures for 59 Unit 11 muscle cards from Head & Neck down; the `fig` override lets a card borrow a better drawing and a hand-placed `point` skips the automatic quality checks (v2.9, 2026-11-06)- Decks for all 28 units (v2.3, 2026-11-05)
- Textbook figures on 1,545 cards + Images on/off choice (v2.4, 2026-11-05)
- Safe save: versioned save with migrations, rolling backup copy, persistent-storage request, a red bar when the browser refuses to save, and a Save & backup sheet with export/restore (v2.6, 2026-11-06)
- Installable app: manifest, icons, offline app shell, Add to Home Screen (v2.6, 2026-11-06)
- Deck tiles show two dots: kind of deck, and what pictures it has, with a legend (v2.8, 2026-11-06)
- Identification decks: 54 decks show the textbook drawing cropped to the structure, label text covered, the structure marked in blue at 20%; the named picture after answering, tapping through to the full figure; tips on a miss; swipe to advance (v2.7, 2026-11-06)

## Dropped
