---
name: design-part
description: Design a new printed part for the Scorpion robot, or change one (a holder, box, bracket, mount, gear, clip, a piece of the mule) — the order of work, and the failure each step came from. Use before drawing anything new, before changing a part, and when Zach reports that a part failed on the bench.
---

# Design a part

The order of work for a part that will be printed, with the failure behind each step. Collected 2026-11-11 from
`docs/decisions.md`, `docs/lessons/` and CLAUDE.md's rules (Zach: "lets also formalize a design skill with lessons
learned"). CLAUDE.md is still the rule book; this is the checklist that applies it. Dates are 2026, and each points at
its entry in `docs/decisions.md` or its file in `docs/lessons/`.

Related: fits, print shapes and slicing are in the `print-on-k2` skill, section 5. His Fusion exports go through the
`review-revision` skill.

## 1. Before drawing

1. **Ask what the last print showed**, and what is printed or printing, before touching anything it covers.
2. **Write the requirement first:** what the robot needs from the part, why, and what would kill it. Name the bench test
   that will judge it. The head had 11 print sets before the roll question was asked. The holders' test, once written
   (11-08): it stays in the floor and keeps its part in when flipped and shaken under the lid, wires and air get out, a
   pack swaps by hand, and a fit change is a small reprint.
3. **Count the sets.** Three sets on one subsystem means stop patching: redraw from the requirement and ask what forces
   the route. The wire lane ran six sets. Two earlier rejections (the gear's screw sat on the pan axis; a 6704 ran into
   the off-axis wire hole) both fell away once the wires went straight down the axis, because that route removes the screw
   and the hole (10-11). Four holder shapes were drawn with one printed (11-08): print
   one and test it before drawing another.
4. **Get his real part.** His model or a caliper number, not a datasheet, a photo or "a typical board". The servo's
   datasheet box, the camera posts and the ESP32 box each cost a print. Ask which face a caliper number was taken across
   (the ESC's 24 was never pinned down, 11-08). Keep his measurements apart from his guesses. "Ish" means measure it.
5. **Ask what screws and bearings he has now,** and size to those. Set 10 used M3 × 16 because he had "quite a few" and
   few M2 left.
6. **When one of his rules blocks the design, ask what exactly he rejected.** "No folds, ever" turned out narrower.
7. **Ask for the goal, and bring at most three calls.** Of 11 picks approved together, 8 changed within a day.

## 2. Drawing it

**His four plain questions, answered while drawing.** They caught what the checks missed.

- **How does it get in?** Every part and every tool, in assembly order.
  - Set 1 printed with every check green and couldn't be assembled: the small gear had no way into its hole (09-27).
  - A bearing that can't pass a hole goes in before the part that makes the hole (set 10).
  - Every fastener needs a driver path that still exists once its neighbours are fitted (09-18).
- **What holds it?** In each direction, along the axis and upside down.
  - Nothing held the ball along the tilt axis (post v3, 09-25). The first snap pins could slide 0.75 mm past their
    click (09-25). The shelf ring could fall out with the base upside down (10-12).
  - The ESC "can fall out in all those designs" (11-08). "The lid holds it" was withdrawn the same day: it isn't an
    answer until the lid and its fastening are drawn.
  - A test stand-in needs the same answer. The hoop had no pegs, by design, and he couldn't tell how it went on (11-11).
- **Why does it go this way?** If the only reason is an earlier drawing, it isn't one.
- **What happens upside down?**

**Then, by subject.**

- **Wires are parts.** Model the leads, plugs and bend room, or measure them.
  - The ESC frame held partly because a lead was squashed against it (11-08).
  - Jumpers squashed in the lane held the pan to a sliver of its sweep, and they spring back like solid wire (10-11).
  - Wire lengths set how far apart parts can sit (11-08).
  - Size a channel from the cable and from its plug (09-18, 09-27). Two cuts that each clear the cable need not meet
    (`2026-09-27-two-clear-cuts-need-not-meet.md`).
  - Threading: straight holes, a funnel at the mouth, and thread before bolting down. A bent hole was "a massive
    pain" (set 8).
- **Flat cable.** No crease at the stiffened connector end, and none pre-folded through a gap; soft mid-cable folds are
  allowed where nothing flexes (09-27). At a turning joint the ribbon's width runs parallel to the axis. A twist needs
  about 40 mm a quarter turn and a round bore (09-18).
- **Hardware is geometry.** Put the screw heads, pins, and the real servo and camera solids in the model. Heads on the
  ball's curve jammed it (rev 1). A screw should squeeze its own joint: set 6's screw pulled the gear up against the
  servo (10-10).
- **Bearings.** Each race touches only its own kind. The 6809's inner race sat on a fixed ledge (09-27), and the drum's
  hub had sat flush on the deck ring since set 2, found when he called the pan "finicky" (10-04). A shoulder is a sharp step, not a blend.
- **Gears.** Not at the exact pitch distance: 0.3 off the small gear gave 1.9° of play (09-27).
- **Printed joints.** Locate on two pegs, let the rest clear, and hold with a spring that travels further than the print's
  error (11-09; on the bench 11-11). A part that has to bend to go together snaps (10-03).
- **Split a part when it blocks its own assembly** (the gear off the drum, the hub as a sleeve). **Merge it back when
  the reason has gone** (the shelf ring, 10-12).
- **His eye is a check.** "Weak in key areas" was right: the beam model had clamped the one joint that failed
  (`2026-10-29-a-rigid-root-hides-the-joint.md`). "Flimsy" (set 10's gear) and "very thin" (the first boxes) each got a
  redraw before anything printed.
- **A list of parts isn't a body** (10-28). Weigh what will be printed: the printed shell came out 0.8 to 1.2 kg over the
  sim's skin (10-31). A new part has to reach every measure that reads the robot (10-31).
- **Shape it for the printer:** bridges, supports, layers and screws are in `print-on-k2`, section 5.
- Mark every picked number with `*` in the generator, with what it was picked from.

## 3. Checking it

CLAUDE.md's checking rules, with what each one caught.

- **Every zero needs a negative control.** A boolean cut silently did nothing; the control against the blank caught it
  (10-10).
- **Zero overlap isn't a fit.** Probe the bolt axes, bores and cable paths for open space, with the old version as the
  control (`2026-09-27-zero-overlap-is-not-a-fit.md`).
- **Seated isn't assembled.** Slide each part in along its real path, measure gear play, check what each race sits on.
- **Place a part by the feature it has to pass through,** not a proxy.
- **Locate a small overlap before naming it.** 3.8 mm³ of "skin" was the servo's tabs on the seam posts.
- **One position at a time.** Twelve stacked copies hid most of an overlap (`2026-10-05`). Sampling a surface doesn't
  check a solid (`2026-09-19`). An SDF value is a bound, not a distance (`2026-10-02`).
- **Exact OCC booleans** on anything shipped (`tools/kit.py`), every cut overrunning its face, the mesh report on every
  export.
- **A new printed joint goes through `twin/print_noise.py`** before it prints.
- The fuller gate, when he asks for it: the `adversary` and `gatekeeper` agents.

## 4. Showing it

- An interactive 3D view of the part in its assembly, with his real part meshes, published as an Artifact so it opens on
  his phone. A change gets a before and after.
- Beside it: every guessed number, for him to OK or measure; his four questions, a line each; what the change
  supersedes; which parts still carry open guesses, so he can print the settled ones first.
- A flag for him leads with the question in bold, then short evidence.
- Then the `print-on-k2` skill. It needs this view again before the printer.

## 5. After the bench

- Write down what the bench should show before the print, so the result scores it.
- Record his verdict in his own words. An obvious verdict from the bench stands; don't make him finish a formal run.
- A number he tested goes into `print-on-k2` section 5 with what it was tested on. Past that range it's a guess again.
- Mark what the change supersedes; never delete it. A check that read green on a broken part gets a lesson file.
- Log his calls in `docs/decisions.md`, and ask whether to commit.

The hand-off's contents are in CLAUDE.md, "Deliverables".
