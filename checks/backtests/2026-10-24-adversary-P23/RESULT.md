# Backtest 1 result: PARTIAL

Scored 2026-10-24 by the rule in `PROTOCOL.md`, written at 13:33 before the run (sha256 `ec3a7f95…633f6`, not
committed then). The adversary ran blind for 61 minutes: 15 mutants, 5 killed, 10 survivors. Its full report is the
hand-back below, and its mutants, probes and outputs are in `adversary/`.

## The score

**PARTIAL.** The adversary never says the shelf ring can come out of the base. Its closest survivors are about the
ring's seat and key under mutation, in the upright base:
- A05: the rib flush with the ledge, so the ring turns freely.
- A06: the ledge gone, so the ring tips into the lane.

It treated a lifted ring (A11, 0.4 mm high) as a clash with the drum's hub, not as a ring leaving its seat. That the
unmutated design holds the ring down with nothing but gravity and a 0.15 mm slide, and that the base is turned over
during assembly, appears nowhere in its report.

**Secondary (not scored).** It didn't find P14 (the screw tears the stub) or P16 (the gear slips on its spline).
Both are outside the change. They wouldn't have counted as blind anyway: the memory index in its context names
both fixes.

## Blinding

- **Files:** a scan of every tool call in its transcript found no path outside the sandbox.
- **Context:** the harness put the repo's CLAUDE.md and memory index into its context. That's a deviation from the
  protocol, and the agent disclosed it. A grep of both finds no mention of the ring falling out, so P23 stayed blind.
- **Other deviations:**
  - The set 5 and 6 flags (CONE, NOTCH, SPLINE_GEAR) were folded too, removing only pre-set-7 dead code.
  - The brief rewrote adversary.md's paths for the sandbox, and dropped "name the past finding it copies", since
    the logs weren't available to it.

## The lesson: the adversary can't see forces

Three escapes were latent in set 7, and all three are forces:
- P23: gravity, with the base upside down.
- P14: the screw's tension.
- P16: the servo's torque on a printed spline.

Every mutation operator and every check is static geometry. That's no small corner: 8 of the 16 bench escapes from
P03 to P24 are forces (friction P12, P16 and P19; strength P14; fit force P17 and P18; material P22; retention
P23). A geometric adversary finds a force escape only by luck.

**Change made to `.claude/agents/adversary.md`:** a loads step. For each part the change touches, list the forces it
sees in every orientation it's held in during assembly, use and handling: gravity with the part inverted, screw
tension, motor torque, and the pull of taking it apart. Then name what resists each one. A force nothing resists is
a survivor, even with no mutant behind it.

This step was written after seeing this escape, so it can't be scored on P23 again. The next backtest has to use a
held-out escape. Blind candidates are scarce, because the memory index summarises most fixes. A blind run needs an
agent context without the project memory, such as a `claude -p` run from a folder outside the project.

## What it found that is real

Each item was checked against the live code where it says so.

1. **`insertion` has no working negative control.** Its `broken` flag is unused. Both this backtest's setup and the
   adversary found it independently. Registry K02 is updated, and the audit now flags it.
2. **`hub_face`'s control is fragile (A15).** The control rebuilds set 5 from live code, so any edit to the dead
   set 5 branch fails `bearing_races` even when the design hasn't changed. Freeze the control reading, or build a
   fixed bad fixture. (Registry K05.)
3. **`pairs` crashes on any ribbon mutant (A12).** `at_pan` calls `P.ribbon(..., pan_deg=)` itself, so a mutated
   ribbon raises TypeError, and the harness counts the crash as a kill. The real harness run logged no errors, so
   no published number moves. It's latent. (Registry K01.)
4. **`pairs`' 1 mm³ threshold misses slide-fit interference** (A04: 0.34 mm³ at 0.1 mm deep; A14: 0.57 mm³). Judge
   small features by penetration depth, not volume. Treat a slide pair as failing when the mover grown by the slide
   rule overlaps.
5. **Nothing checks set 7's purpose, a support-free base** (A01 and A02 survive). Its overhang probe tells the cases
   apart: set 6 has 2635 mm² of downward faces more than 30° off vertical, set 7 has 195 mm², A01 1233 mm² and A02
   1112 mm². Two real escapes share the cause (P11 and P13, supports that couldn't be removed), so the rule of two
   says to make it a check. Proposed.
6. **The ring's key, ledge support and play** (A05, A06, A07): sweep the ring through its free play, the "seated
   isn't assembled" rule applied to a drop-in part. Proposed.
7. **The ribbon is drawn with a sharp 90° corner at the exit (A13),** so no check can see a window too narrow for
   its real bend. Lower priority.

## The adversary's hand-back (condensed; the numbers are its own)

```
## Result: 5 of 15 mutants killed (3 genuinely); 10 survive, and set 7's main purpose is unchecked

**Precondition.** Design passes all five checks (baseline.txt, 187 s). Controls (control.txt): pairs, assembly,
gear_play, bearing_races fail as they should; **insertion passes its own negative control** -- it reads `P.servo`
directly, so the shifted servo in `fns` never reaches it (the check's own `main(broken=True)` has the same flaw).
Insertion has no working negative control.

| Mutant | Breaks | Killed by |
|---|---|---|
| A01 glue(well, shelf_ring) | set 6 lane roof back (needs support) | none |
| A02 CONE_OUT_DEG=60 | 30 deg read from horizontal: cone, slit and teardrop roofs 60 deg off vertical | none |
| A03 RING_OR=22.65 | elephant foot on the bed-face shelf: 0.15 slide -> 0 | none |
| A04 KEY_SLIDE=-0.1 | key notch prints small: 0.1 interference on the rib | none |
| A05 KEY_H=0 | rib flush with the ledge: nothing stops the ring turning | none |
| A06 LANE_R=22.6 | lane widened: ledge gone | none |
| A07 RING_OR=21.8 | 0.85 play a side > 0.6 drum clearance | none |
| A08 LANE_Z1=-20.3 | ring shelf 0.3 thick | none |
| A09 nofeat(shelf_ring) | ribbon window and wire mouth gone | pairs (ring vs ribbon 10 mm3) |
| A10 move ring -0.3 z | ring sunk into ledge | pairs (67 mm3), assembly |
| A11 move ring +0.4 z | cup top touches the turning hub | bearing_races (hub_face) only; pairs reads touch as 0 |
| A12 move ribbon -1 z | ribbon resting on its shelf, as the pair note says | pairs -- **by crash only** |
| A13 WINDOW_W=2.0 | window too narrow for the real ribbon's bend | none |
| A14 move ring +0.2 x | 0.05 crescent into the skirt | none |
| A15 DECK_IR=23 | nothing (set-5-only constant) | bearing_races -- **false kill** |

Survivors, property violated, how to cover:
- A01, A02 -- the base prints support-free (the reason set 7 exists). New check. Overhang probe (overhang.py):
  set 7 195 mm2, A01 1233, A02 1112, set 6 2635.
- A03, A04, A14 -- a drop-in slide needs clearance, not just zero overlap. Pairs, widened: grow the mover by the
  slide rule, or judge by penetration depth; exclude the intended ring-on-ledge contact.
- A05 -- the ring is keyed against rotation. New check (move the part through its free play): design +-0.45 deg;
  A05 turns to 180 deg.
- A06 -- the ring rests on its ledge. New check (drop test + contact coverage): design 186 mm2 all round; A06 10 mm2.
- A07 -- ring play smaller than its running clearance to the drum. Sweep the ring through its play.
- A08 -- minimum section of the printed shelf (0.30 vs 0.80 mm). Lower priority.
- A13 -- the ribbon's bend radius at the exit; the ribbon model needs it.

Harness/check findings: A12's kill is a crash (at_pan calls P.ribbon with pan_deg; re-scored without the crash the
tail runs 0.6 into the sill, 0.43 mm3, passes). A15 is a false kill (hub_face's control re-runs the live set 5
branch). hub_face covers one plane only.

Disclosure: CLAUDE.md and the memory index were injected into my context at start (not opened); they include the
slide rule, "zero overlap isn't a fit", "seated isn't assembled", and a one-line note that set 7 has a drop-in shelf
ring and a support-free well. I opened no file outside the sandbox.
```
