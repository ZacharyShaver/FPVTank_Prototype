# 2026-09-27: Parts that fit when seated can still be impossible to assemble

The pan coil's first print set went to the printer with every check green. Zach looked at the parts and
asked how the small gear gets into its hole. It doesn't:
- the gear was moulded onto the drum, 22.6 mm across, below a 10.5 mm hole;
- the gear bay was a closed box around a 43.3 mm gear, with no opening bigger than 17.2 mm.

The pair check placed every part in its final position and measured shared volume, and all of it read
zero. The parts fit perfectly once they were there. Nothing asked how they got there. The servo was the
one exception: its side-window insertion had its own sweep, which is why it was the only part that
could actually go in.

**Do:** for every part, write down the direction it goes in and what is already in place by then. Then
slide it in along that path against those parts (`pan_coil_b_check.assembly()`). One-piece parts that
pass through a hole are the first suspects: compare each part's widest section with every opening it
passes.

**Negative control:** the same sweeps with the old parts (gear back on the drum, floor back in the bay)
must read blocked.

**Watch the stand-ins.** The first run of the sweeps read two blocks that weren't real:
- the M3 shank drawn at full size overlapped the drum's pilot hole, where the thread is meant to bite;
- the servo's 4 mm shaft stand-in ran 0.8 mm past a placeholder horn pocket.

Locate every nonzero result before calling it anything, whether a fault or an artefact.

## And a green run on a broken part

While making the fix, a new constant `BOSS_R = 3.0` (the floor screws' bosses) reused the name of the
well's `BOSS_R = 31.0`. Python took the later one without complaint, and the well lost its bearing
ledge. The pair checks and the new sweeps all came back clear. They were measuring gaps around a part
that had quietly lost material, and a missing part collides with nothing. The print mesh's size gave it
away: 76 × 51 × 31.5 mm for a part that has to be at least 62 mm across and 38 mm tall.

**Do:** before trusting a clean check, read each printed part's bounding box against the size it has to
be. In a generator module, check that no module-level name is assigned twice (an `ast` walk does it in
ten lines).

## Moving parts need a motion check, not a clash check

Asked "anything else before I print?", the first things measured were ones no check had looked at:
- the gear pair's free play: 0.0°. The teeth touched on both sides at every angle;
- what the bearing's turning inner race sat on: 100% solid fixed ledge.

Both read zero overlap in the pair check, correctly, because touching isn't overlapping. A zero-overlap
row can't tell a running clearance from a rubbing face or a jam.

**Do:** for every pair of surfaces that move against each other, measure the gap or the play itself,
and say what it should be (`gear_play()` wants 0.5–4°). For every bearing, check that the rotating race
touches only rotating parts and the fixed race only fixed ones (`bearing_races()`).
