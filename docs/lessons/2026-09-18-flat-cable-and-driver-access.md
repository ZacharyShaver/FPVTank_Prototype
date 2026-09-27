# Flat cable routing, and driver access — rules from the 2026-09-18 print review

**What happened.** Zach printed the TEST-PRINT-2 head and the tree-head parts and
reviewed them in the hand. Three things came out of it, in his words: there was
*"not enough room for a screwdriver to even make this connection"*, the horn-carrying
part *"blocks the ability to screw that in since it has to face to both the ball and
the [mount]"*, and on the ribbon coil, *"the area is way too small to handle the
amount needed for the fold, plus it feels like a bad idea to bend those wires so
hard… I'd suggest a curved shape."*

All three are design rules, not one-off fixes. They are recorded here because both
were found by handling a print, and neither would have shown up in a CAD check.

## Rules

1. **No creases in a flat cable. Ever.** Polyimide FPC wants a bend radius of about
   10 × its thickness — roughly 3 mm for a 0.3 mm ribbon. A hard fold work-hardens
   the copper at the fold line. Turns are made with drawn-out curves.

2. **At a rotary joint, the cable's width must be parallel to the joint axis.**
   That is what lets it coil. It follows that a cable can turn freely *within* its own
   plane, and that any change of travel direction *out* of that plane costs either a
   crease (forbidden by rule 1) or a twist.

3. **A twist needs length and a bore.** Budget roughly 40 mm of run per 90°, inside a
   round hole about as wide as the cable. A 16 mm ribbon will not twist inside a 10 mm
   channel, however long it is.

4. **Prefer to put the unavoidable transition where it never cycles.** A transition
   between two parts that rotate *together* is set once at assembly and then holds
   still. That is a different fatigue problem from one that flexes every time the head
   moves, and it can be much tighter.

5. **Size a cable channel from the cable, not from its plug.** The tree head's branch
   channels were sized 10.4 × 5.2 to pass a servo plug, and the 16 mm camera ribbon
   could never have gone down them. Caught on review, not by any geometry check.

6. **Every fastener needs a driver path that still exists after the parts around it are
   fitted.** Check it in the assembly order, not on the part alone. A captured servo
   horn is the classic trap: the part carrying it mates to two things at once, and the
   centre screw becomes unreachable the moment either one goes on.

## What this changed in the tree head

- The camera ribbon no longer runs down a branch. It leaves the coil tangentially and
  drops down an enclosed trough moulded into the −Y pod wall and the stem below it,
  staying in its own plane the whole way. Minimum bend radius on that path: 7.3 mm.
- The branch channel is servo leads only, and its exit out of the back of the saddle is
  a curve rather than the box it used to be.
- The tilt horn is screwed to the ball's hub on the outside of the ball half, before
  assembly, with no screw into the servo shaft. The spline carries torque only; the
  housing traps both parts axially.
- Still open at the time of writing: the static twist where the ribbon crosses from the
  camera board, inside the ball, to the coil chamber outboard of it. It needs a round
  bore about the ribbon's width, which drives the axle and bearing choice.

Related: `head-v2/generator/tree-parts/README.md`,
`head-v2/generator/ball-head-validation-handoff.md`.
