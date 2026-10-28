# A pool rank measures the search

2026-10-28, the capability search (`gauges/capability.py`, `gauges/README.md` "The capability search").

**What happened.** Zach asked for every gauge maxed with no weights between them. Beside one stream per gauge, an
all-rounder stream raised a design's worst percentile rank: each gauge ranked against every design screened so far.
It settled on a heavy six-wheeler that steps 50 mm, turns in 659 mm and lands upright half the time. On the same
score T3 ranked 0.17, though it meets every target and nothing beats its step and turn together.

**Why.** The pool was the search's own output. The hill and push streams filled it with designs that out-hill T3,
so T3's 45° hills sat near the bottom of the pool, while a 50 mm step beat most of the pool's poor steppers. The rank
said where a design stood among what the search had already made, not what the robot could do. The single-gauge
streams also never went near T3's corner, which needs the step and the turn at once.

**How to apply.** Score an all-rounder against fixed scales (each gauge's target or ceiling, or T3 as the bar), never
against a pool the search is still filling. When two gauges only pay together, give the pair a stream of its own.
Related: `2026-10-28-small-effects-add-up.md`.
