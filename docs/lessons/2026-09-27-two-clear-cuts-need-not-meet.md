# Two clear cuts need not meet

**2026-09-27.** Found when Zach said the cradle's way down into the drum had no room for the ribbon
and the tilt servo's plug together.

## What happened

The cradle carries the ribbon down two cuts: the **track**, the gap behind the ball where the loop
rolls, and the **groove**, which takes the ribbon from the track's lower end down into the drum's bore.
`tree_parts_b_check.py` had a row for each: "ribbon track vs nest" and "ribbon trough vs nest", both
**0.00 mm³**. The fit view's card said "the ribbon's full 16 mm width is clear the whole way".

Zach's complaint was about the plug, a rigid block. Sliding and turning a plug-sized block through
the open space (`head-v2/checks/plug_passage.py`) found it blocked at 3 and 4 mm slot thickness
alike. The control, a 1 mm block, was blocked too, and so was a 0.3 × 0.2 sliver. Measured on the
cradle's own distance field at 0.01 mm: the widest thing that fits from the track into the groove
is **0.00 mm**, at Y 0, 4 and 8. The two cuts touch at a corner and never open into each other.
The groove started 1.2 mm inside the shroud wall, and the track stopped 0.4 mm short of it.

## Why the checks missed it

Each row measured a cut against the part it had been cut from. A cut subtracted from a solid can
never overlap it, so both rows would read zero whatever the cuts looked like. That's the same
vacuous shape as "sampling a surface does not check a solid" (2026-09-19). Nothing asked the actual
question: is there a path from where the cable comes in to where it goes out?

## What to do

- For a cable or part that has to get through, check **connectivity from entry to exit**, with
  something the size of the thing that travels. Clearance along each piece isn't enough. Slide and
  turn it (`plug_passage.py`); a sliver of the ribbon counts too.
- Give the passage check a positive control as well as a negative one. A tiny block must pass,
  or the search itself is broken. Here the "positive" control failing on the old cradle was the
  finding.
- A "0.00" for a cut against its own part is not a check. Delete such rows or reword them as what
  they are, a sanity check that the cut exists.
