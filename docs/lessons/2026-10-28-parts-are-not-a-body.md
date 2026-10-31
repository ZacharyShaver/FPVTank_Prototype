# A list of parts is not a body

2026-10-28, the capability search (`gauges/capability.py`, `gauges/README.md` "One body").

**What happened.** Zach looked at the capability page's shapes and saw "a lot of floating parts". A design was a body
hull plus a list of mass items: motors, packs, a push plate, a tail mount. The knobs moved the items, and nothing tied
them to the hull. Without a skin the body was the Trainer's tub with its wheel pods left out, so wheels could sit
250 mm from it. 55 % of the 3,423 designs had a loose part, and so did two of the champions, which had been reported.

**Why it slipped.** Every check before this one asked whether a design could be simulated: tyres apart, the step
gauges' controls, the timestep. None asked whether it could be built. MuJoCo welded every geom to one free body, so a
loose part behaved as if it were on a perfect bracket, and the numbers looked fine.

**How to apply.** When a generator places parts by knobs, check that they connect (each part touches the body or
stands off it on a stated bracket), with a control that fails. Prefer growing the body to the part over refusing the
design, so the search keeps its range. Look at the shapes, not just the numbers, before calling a champion. Related:
`2026-09-27-zero-overlap-is-not-a-fit.md`.
