# Physical drop tests (workstream E): raw data

Recorded by hand on paper, one mark per drop, and videoed. Transcribed from the sheet photo before any scoring;
the predictions were committed first (research/results/drop_predictions.json, commit 0718c2f).

## Run 1 (2026-10-13): 3 bodies x 6 starts x 5 drops = 90 drops, 12 US quarters

- `run1_sheet.jpg` is the sheet; `run1.csv` is the transcription, one row per drop.
- Zach's marks: X inverted, O upright, N nose down, T tail down (nose up), R right side, L left side, F front
  (read as nose down).
- Bodies are identified on the sheet by drawn icons. Zach, before scoring: top to bottom E2, E3, E1, so oval =
  E2_dome, rounded square = E3_tall, hill = E1_tub.
- Loading: coins first, then the spacer (Zach), which is **mass high** in DROP_TEST.md. The card asked for mass low
  first; the order of the two runs does not change either prediction.

## Open (2026-10-13, late): the sheet and the E1 video don't agree

- Zach: the sheet is a 6 cm session, and so is the video `IMG_1617.MOV` (in his Downloads, 174 MB, not in git).
- The video is E1 (the slot where the pocket breaks through the top is unique to E1), about 28 drops released from
  roughly 4-8 cm by eye. In it E1 comes to rest standing on end twice (0:49 and 1:17); the sheet's E1 row has no N or
  T. So the two are not the same drops. To settle with Zach before anything is scored: how many sessions there were,
  at what heights, and where each was recorded. He also has 30 cm drops recorded somewhere, without video.
- Release height doesn't need redos: the simulation at 40, 60 and 80 mm moves no E1 probability by more than 0.03
  (`results/drop_predictions_E1_40mm.md`, `_E1_80mm.md`). A rerun at 60 mm reproduced the committed predictions exactly.
- `results/drop_predictions_30cm.*` are the same model at 300 mm, for the 30 cm drops. They were run after those drops
  were made (not before), so they count as post hoc for any data already recorded.
