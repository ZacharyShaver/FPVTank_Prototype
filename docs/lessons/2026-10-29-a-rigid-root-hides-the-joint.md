# A rigid root hides the joint

2026-10-29, body_tree's printed legs (`gauges/body_tree.py`, `gauges/snap.py`) against one-piece bodies
(`gauges/unibody.py`, `gauges/fem.py`).

**What happened.** snap.py sized each printed leg as a round beam clamped rigidly at the body and called the sheet's
designs safe (8-24 MPa). Zach looked at the sheet and said the shapes looked weak in key areas, weakest landing on one
wheel at an angle. The same designs, solved as one printed shape with the body a shell, read 41-136 MPa, every peak
where a leg meets the body's side: the one joint the beam model had clamped.

**Why it slipped.** The README listed the root as "not modelled", and the check passed what it could see. A model that
clamps a joint can't find that joint weak, and a leg's root into a printed wall is where a rod's bending ends up.

**How to apply.** Before trusting a strength check, find what it holds rigid and ask whether the part breaks there.
Prefer solving the shape itself over a stick model of it. When Zach says a shape looks weak, check it with a model that
could disagree with the last one. Related: `2026-09-27-zero-overlap-is-not-a-fit.md`.
