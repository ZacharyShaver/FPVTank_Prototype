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

## The E1 video (`IMG_1617.MOV`, Zach's Downloads, 174 MB, not in git)

- The same 6 cm session as the sheet. The video starts partway through: it holds the last 2 nose-down drops and
  all 25 after them, 27 in total. One more pick-up at 1:24 lifts the body out of frame and isn't a drop.
- `video_E1.csv` is my reading of each drop's landing from the frames, matched to the card's order of starting
  attitudes. It agrees with the sheet's E1 row on 24 of 27. The 3 that differ are drops 2-4 of the left-side block
  (video X O X, sheet O X O). Zach's call (2026-10-13): **go with the video** for E1.
- Correction to my first pass: I read drops 12 and 16 as "standing on end". They are lying on their side (base to
  one side), which is what Zach wrote (R). With that fixed, the right-side, tail-down, upside-down and 45 blocks
  match the sheet exactly.
- Release height: about 4-8 cm by eye. The simulation moves no E1 probability by more than 0.03 across 40-80 mm
  (`results/drop_predictions_E1_40mm.md`, `_E1_80mm.md`), so no drop is redone for height. A rerun at 60 mm reproduced
  the committed predictions exactly.
- **Nose and tail, to confirm with Zach:** in the "tail down" drops (video 4-7) the head end (the bump; the pointed end
  seen from the base) points down. The card defines nose down as the head end down, so Zach's nose and tail are
  likely swapped against the card and the model. Score by the physical end, once he confirms.
- Left and right: all three bodies are mirror-symmetric, so "left side" and "right side" (starts and rest states)
  are the same physics and get merged into "side" when scoring.
- Found while checking this: `tumble.classify` names the on-end rest states opposite to `scale_model.ATTITUDES`
  (+X up is called "nose down"). It doesn't touch P(upright) or anything already reported; when scoring, the
  predicted "nose up"/"nose down" rest labels are swapped back. Probabilities are unchanged.
- `results/drop_predictions_30cm.*` are the same model at 300 mm, for the 30 cm drops (recorded elsewhere, no
  video). They were run after those drops, so they count as post hoc.
