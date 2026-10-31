# A new part must reach every measure

2026-10-30/31, the two-link tail (`gauges/robots.py`, `gauges/gauges.py`) and the wide overnight search
(`gauges/capability.py`, SCORPION_CAP=capability_tail).

**What happened.** The second link was added to the sim's model (the MuJoCo body, its joint and servo), and the
reflexes and IK used it. But `robots.limb_points`, which every measure reads for the tail's extent (the turn circle,
where a step try starts, the strict build's tail clearance, the dims), still drew the first link alone. The overnight
run screened 5,288 designs with two-link tails measured short. Re-screened after the fix, 14 two-link winners kept every
gauge but the turn: up to 25 mm wider, and one (a 178 mm second link) 144 mm wider. The day before, the same shape of
fault: T3's tail mount boss went into the sim's hulls, and the tail jammed in it.

**Why it slipped.** The new part was tested where it was built (IK within 2 mm; the straight elbow climbing like one
long link), not where the old part's size was read. Nothing listed the readers of the tail's geometry.

**How to apply.** When a part changes shape, grep for every function that reads its size (`limb_points`, `extremes`,
`dims`, the hull lists) and test each with the new part, before a long run. A long run is the expensive place to find
it. Related: `2026-10-30-a-voxel-mask-terraces-the-surface.md`.

**Again, the same day.** `film.Rec` (the gauges' Sim on a visual model) re-read the tail's joints as two, so the first
film of a two-link tail crashed. Readers of a part's joints count as readers of its size.

**And a third time.** `unibody.make` re-attached a given tail with `add_limb(L, tq, ...)` alone, so a two-link tail
came out one link, without its rear-up or its foot; the search's winners were gauged in one piece that way until it
was fixed the same evening.
