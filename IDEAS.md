# Ideas backlog

Side ideas Andrew mentions while we work on something else. Claude adds new ones as they come up and checks this list before starting new work. Move an item to **Done** when it ships, or to **Dropped** if Andrew decides against it.

## Open

### Next four releases (roadmap v1.1.0, brainstorm 2026-11-25)
- **Spaced review via FSRS** (3.9.0): per-card memory using FSRS v6 (`ts-fsrs`, MIT, vendored inline), plus a Weak Cards round. *(2026-11-25)*
- **Today session** (3.10.0): one button mixing due reviews, weak cards and a little new material; "all caught up" empty state with Study ahead. *(2026-11-25)*
- **Streak with freeze days** (3.10.0, Claude's proposal, not yet confirmed): forgiving streak, local dates, freezes banked automatically. *(2026-11-25)*
- **Unit Readiness warm-up inside Today** (3.10.0): offered when a unit's check is unlocked but not taken. *(2026-11-25)*
- **Path with body silhouette and unit trails** (4.0.0): Path / Library / Weak tabs; the body fills in as units are mastered; each unit opens a trail of its decks with the mastery check as the boss node; mockups approved before code. *(2026-11-25)*
- **Specimens with rusty fading** (4.1.0): a body part is mastered when all its parts are; dims slowly if not reviewed, never vanishes, one Polish round fixes it. *(2026-11-25)*
- **"I guessed" flag** on answers (Claude's proposal, not yet confirmed). *(2026-11-25)*
- **Confusable-pairs drill** (radius vs ulna and similar; Claude's proposal, not yet confirmed). *(2026-11-25)*
- **Exam-date pacing mode** (Claude's proposal, not yet confirmed). *(2026-11-25)*
- **Repeated answers inside a deck (2026-11-25)**: 17 cards share an answer with another card in the same deck (e.g. "Superior" twice in Directional Terms, different clues). `groups-overrides.json` keys on deck + answer, so an override there hits both. Harmless today; worth a look if a fix ever targets one of them.
- **Card memory per deck, for 3.9.0 (2026-11-25)**: Organelles and Organelle Functions share one card list (same IDs, asked two ways), so card memory should be keyed by deck + card, the way the ready streaks already are.
- **Groups for non-skeletal decks (2026-11-24).** Only the bone decks have hand-fixed groups so far (3.6.0). Decks that mix families (heart anatomy, respiratory, CNS, nephron) could get overrides; run `python3 tools/groups.py --all` to see which. Andrew also noted the Deltoid tuberosity clue gives it away; the scanner lists such echoes.
- **Swipe to next card** after answering (Next button stays for laptop). Building into the image-design samples to try on a phone. *(2026-11-05)*
- **Tips on missed cards**: short memory tricks, fun facts or "how to tell it apart" notes, shown only when you miss. Andrew reviews each unit's tips before they go live. *(2026-11-05)*
- **Pulsing highlight on structures**: light-blue fill over the whole structure, pulsing about 10–80% opacity, Visible Body style. Part of the pre-answer image design. *(2026-11-05)*
- **Save v2.3 and v2.4 to the claude.ai project** once there's room (the project hit its size limit; remove v1.6, v2.0, v2.1 first). *(2026-11-05)*
- **SAM (MobileSAM ONNX) for structure outlines**: try it against the hand-placed points to auto-outline structures; Andrew would download the ~40 MB model to his Claude folder. *(2026-11-07)*
- **Gray's Anatomy plates for gaps** (face muscles, Transversus thoracis, Serratus posterior superior): download via the built-in browser, add a credits page. *(2026-11-07)*
- **Re-do the 13 skipped cards** (leg/arm veins, uterus parts, phrenic/femoral nerves) with closer crops. *(2026-11-07)*
- **3D renders, next**: fill the gaps (ethmoid, lacrimal, palatine, iliocostalis, eye muscles, genioglossus, landmarks like foramina) with better views or cut-away renders; maybe organs and vessels from BodyParts3D; speed up huge frames. *(2026-11-07)*
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
- **Unit mastery check**: 50 randomly selected questions from the unit. Gold at 95% or higher (lose no more than 2.5 points), mastery at 100%. Unlocks once every deck in the unit has 2 or more stars (stars shipped in 3.7.0). Best score is saved. *(2026-11-06)*
- **Unit header tiers in the lobby, the fancy version**: 3.8.0 shows Gold / Diamond / Ruby as a small badge on the unit page and lobby tile; the idea of the whole unit header changing look with the tier is still open. *(2026-11-06)*
- **Build order decided**: 1) safe save + installable app (next release), 2) deck stars and unit mastery checks, then the rest. *(2026-11-06)*
- **Daily Review**: re-drills the cards you've missed. Could draw on the multiple-choice readiness data (cards not yet "ready"). *(2026-11-06, updated 2026-11-20)*
- **Weak cards only round**: a round built only from cards that aren't "ready" yet in multiple choice (fewer than 2 right in a row). *(2026-11-20)*
- **Multiple choice as a study method (v3.5.0, building 2026-11-20; the app was already at v3.4)**: after answering, the choice turns green if right or red if wrong, then a Next button like typed answers. Ready cards stay in every round. 4 choices per card, the right answer plus 3 other answers from the same deck (filter out look-alike or alias answers; fall back to same-unit answers for tiny decks). A card is "ready" after 2 right in a row; a miss resets it. Fills a per-deck readiness bar; typed answers stay the real test for stars, high scores and the unit mastery check. One try per card. *(2026-11-20)*
- **Speed Round**: timed random testing. Code later. *(2026-11-06)*
- **Boss Fights**: the mastery check as a boss, possibly themed on each unit's pathologies (osteoporosis for bones, brain cancer for the nervous system, etc.). *(2026-11-06)*
- **Cumulative boss every few units** that mixes earlier material. *(2026-11-06)*
- **Unit Readiness deck (multiple choice, before the boss battle)**: one multiple-choice round that pools every deck in a unit, as the warm-up before the typed mastery check. Thinking so far (nothing decided, build only after Andrew says build it, and after the deck stars build): ~25-30 cards, at least a couple from every deck so none gets skipped, weighted toward cards that aren't "ready" yet; distractors from the card's own deck like regular multiple choice; identification cards keep their pre-answer picture. Ends with a per-deck breakdown and a "drill your weakest deck" button. Optional, not a gate (the boss still unlocks at 2 stars per deck). Label it readiness, not mastery, since recognizing an answer is easier than typing it, so the boss stays the real test. Decided 2026-11-22: its answers DO feed each card's "ready" streak; no star or high-score credit; a cumulative version (mixing earlier units) comes later for the every-few-units boss. *(2026-11-22)*
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
- Locked card IDs (3.8.1, 2026-11-25): every current card ID is recorded in `tools/card-ids.json` and `test_card_ids.py` fails if one disappears or moves; new cards go at the end of a deck, a retired card's line starts with `~` and keeps its slot; `tools/card_ids.py --update` after a real answer fix. Found at Gate 0: most IDs were line positions.
- Unit mastery check (3.8.0, 2026-11-25): 50 random typed cards from the unit (all of them for units with fewer, like 15 and 16), unlocked at 2+ stars on every deck; first try 1, second try half, miss 0; Gold 95%+, Diamond 100%, Ruby = 100% plus 3 stars on every deck; retake any time, best counts. Andrew considered scaling the size per unit or themed checks per unit (bone identification master vs landmarks master) and chose a flat 50 for now.
- Deck stars (3.7.0, 2026-11-25): 50% = 1 star, 80% = 2, a perfect first-try run = 3; best typed run counts and never goes down; shown on deck tiles and the results page; no grey stars (the readiness bar covers study progress). Replaces the 2026-11-06 "3 perfect runs" idea.
- Regression test 2.0: parallel tabs, `--quick` / `--full` / `--units` / `--changed`, seeded runs; full check about 40 s, quick about 6 s (2026-11-07)
- Hand-fixed pictures for 74 bone cards (skull, vertebrae, thorax, arm, pectoral, pelvis, leg); Adobe connector tried and not useful here (v3.0, 2026-11-06)
- Hand-fixed pictures for 59 Unit 11 muscle cards from Head & Neck down; the `fig` override lets a card borrow a better drawing and a hand-placed `point` skips the automatic quality checks (v2.9, 2026-11-06)- Decks for all 28 units (v2.3, 2026-11-05)
- Textbook figures on 1,545 cards + Images on/off choice (v2.4, 2026-11-05)
- Safe save: versioned save with migrations, rolling backup copy, persistent-storage request, a red bar when the browser refuses to save, and a Save & backup sheet with export/restore (v2.6, 2026-11-06)
- Installable app: manifest, icons, offline app shell, Add to Home Screen (v2.6, 2026-11-06)
- Deck tiles show two dots: kind of deck, and what pictures it has, with a legend (v2.8, 2026-11-06)
- Identification decks: 54 decks show the textbook drawing cropped to the structure, label text covered, the structure marked in blue at 20%; the named picture after answering, tapping through to the full figure; tips on a miss; swipe to advance (v2.7, 2026-11-06)

## Dropped
