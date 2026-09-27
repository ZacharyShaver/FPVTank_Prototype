# 2026-09-27: A zero-overlap check is not a fit check, and other lessons from the pan-coil merge

These came from one long session. It covered the folder move off OneDrive, phase B, fitting the cradle
onto the 360° pan coil, and the coil's first print set. Most are about checks that read green while
the thing they were meant to catch was sitting in plain view.

## 1. Zero overlap says nothing about holes that don't line up

`pan_coil_b_check.py` read **0 clashes** with the cradle on the drum. It was right. It was also blind
to all three real problems:
- the drum's M3 holes sat under solid cradle;
- the ribbon's way down was 80–90% solid;
- the groove landed at the edge of the drum's hole.

Voids that fail to meet don't overlap anything. An interference check proves two parts don't
collide, not that they join.

**Do:** at every joint, probe the features that must line up (bolt axes, bores, the ribbon's path) for
*open* space, as well as probing for overlap. Run the same probe on the old version as the negative
control: the bolt probe read 100% open on the new cradle and 0% on the old.

## 2. Follow the real path, not a convenient plane

A straight vertical probe said the ribbon slot was 89.7% open. The ribbon doesn't run straight: it
comes in on a bend, and the probe was clipping the bend's corner. Sampled along the groove's own
centreline, at the ribbon's full width, it was 100%.

**Do:** locate every blocked point before believing a percentage, in either direction.

## 3. A constraint can harden past what was said

"No folds in the flat cable, ever" came from Zach turning down one specific fold: folding the
stiffened connector end to fit it through a hole. Hardened into a blanket rule, it made a quarter
twist look necessary: ~40 mm of run, with 21 mm available. That blocked the cradle work.

When asked directly, he said mid-cable folds are fine. With one soft 45° fold at the drum's side slot,
the twist disappears entirely.

**Do:** when a rule blocks the design, ask what exactly was rejected and why, before designing around
it. Record the narrower rule (`docs/decisions.md`, 2026-09-27).

## 4. Tables that print typed-in text go stale silently

`step_mesh_prep.py` wrote the flange screw angles as the fixed string "90°/210°/330°". The triad was
rotated to `SCREW_A = 30/150/270` on 09-19, and `features.md` stayed wrong for eight days. Every other
row was computed from the generator's constants and stayed right.

**Do:** every number in a generated table comes from the constant that drives the geometry.

## 5. Check the file, not the picture of it

The plate picture showed 30–78 mm spikes off the drum and the gear bay. The print files had no edge
over 0.9 mm. The spikes came from a 9,000-face simplification done only for the render. The
generator's own planar-quadric settings, at 30,000 faces, render cleanly.

**Do:** when a render looks wrong, measure the file it came from before touching the model.

## 6. Smooth min bulges past named faces (third time)

The input gear's hub blend bulged ~0.2 mm below the gear's face. The gear sat on a ring, with its face
floating 0.05–0.3 mm off the bed: 63 mm² of contact instead of 1,306. The same fault is in
`cradle-audit.md` §1 and the drum's flange.

**Do:** after any `smin`, clip the faces that have to be flat (`np.maximum(s, z0 - z, z - z1)`).
Measure bed contact on the print mesh as part of choosing the orientation.

## 7. Two small ones

- **A faceted STEP is useless for editing in Fusion.** Anything derived from Zach's STL exports is
  triangles. For work in Fusion, send the `ADD_*`/`CUT_*` tool bodies to apply to his own model.
- **A folder moved while a check was running.** The move from OneDrive happened mid-regression. The
  run lost a script partway through and wrote its result to the old path. Claude's memory is keyed by
  folder path too, so it went missing at the new one. After any move, re-run the checks at the new
  path and copy the memory folders across.

## What worked

- **The hand-off loop:** hash-check every copied file both ways, then re-run the build, the regression
  and the generator's own check from the new home, before touching the source. Phase B moved 199
  files with no surprises.
- **Keeping the superseded design one switch away** (`PAN_COIL = False`) instead of deleting it, and
  using it as the negative control for the new checks.
- **A to-scale picture of a decision** (the twist: 21 mm of room against ~40 needed) got a decision
  in one message.
- **A 3D fit view of the real parts in their real positions**, with the problems marked and a button
  per problem, was the thing Zach asked to see.
