# Spot Check (review page framework)

Reusable loop for checking built identification pictures by eye.

1. `python3 tools/review/export.py <batch>` makes `out/cards-<batch>.json` (small marked pictures + crop boxes).
2. Publish `page/index.html` as an Artifact with `files: {"cards.json": out/cards-<batch>.json}` and `capabilities: {db: {}}`.
   For a new batch, republish the same page with a different cards.json; answers are keyed `<batch>__<card id>`.
3. Andrew taps Correct / Wrong spot (tap the right place) / Remove / Skip. Answers go to db collection `reviews`.
4. Read them with ArtifactData (`list`, `out_dir`) and run `python3 tools/review/apply_review.py <out_dir>/reviews --batch <batch>`,
   then rebuild the touched cards with `tools/idimg/build.py`.

`out/` is generated and ignored by git.
