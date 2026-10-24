# Brief: attack the set 7 change to the pan coil

You are the adversary in a check library. Your job is to break the checks, not the part: find faults in the changed
design that every current check would pass.

You get the change and the checks. You do not get the designer's reasoning, and you should not go looking for it: a
shared blind spot is the failure you exist to catch.

1. **Read what changed.** List every part, feature and constant the change touches. Slice or probe new geometry
   before assuming anything about it.
2. **Write mutants of the change.** Each mutant is one small, plausible mistake, using the fault operators below,
   plus one mistake this project keeps making: **the real part differs from the model** (a servo modelled from a
   datasheet, not the real one, did not fit). Prefer sizes that matter at the bench: 0.3 to 1 mm moves and
   clearance changes, not 10 mm absurdities.
3. **Run them.** The unmutated design must pass every check first, or nothing is scored. Then run each mutant
   against every check.
4. **Report.** Give a table: mutant, what it breaks, and the checks that killed it. Then list the survivors. For
   each survivor, name the property it violates, and say whether an existing check could cover it by widening its
   scope or a new check is needed.

Never edit the design or any check. A survivor is a finding, not a failure on your part: report it plainly.

## The change: set 6 to set 7

In the designer's words, written when set 7 was built:

> Zach: Orca's supports in the base's wire lane, under the shelf, are impossible to get out, and he wants that
> overhang support-free. A slope can't carry the shelf (30 deg off vertical across the lane's 8.4 mm needs 14.5 mm
> of drop; the lane is 3.5 tall), so the shelf and the ribbon cup's wall became `shelf_ring`, which prints shelf face
> down and drops in from above onto a ledge (pan_coil_b.INSERT, RING_\*, SKIRT_\*, KEY_\*). Widening the deck ring's
> hole for it also took the deck ring out from under the drum's hub, which sat flush on it.

In the code, set 7 is `INSERT = True` and set 6 is `INSERT = False`. The model is a set of signed distance
functions (negative inside), one per part, in `pan_coil_b.PARTS`: name → (function, box low, box high, mesh step,
face target). Units are mm; Z is up and the pan axis is the Z axis.

## The checks (all five that exist)

| Check | What it claims |
|---|---|
| `pairs` | No two parts share solid (each listed pair, turning parts swept over the pan range) |
| `insertion` | The servo reaches its seat through the side window along its real path (-Y) |
| `assembly` | Each part reaches its seat in assembly order |
| `gear_play` | The gear pair has free play, and the teeth overlap through a pitch |
| `bearing_races` | The 6809's turning race touches only turning parts and its fixed race lands on its ledge; nothing fixed sits under the drum's hub |

## The fault operators (`operators.py`)

- `move(part, (dx, dy, dz))`: the part sits elsewhere.
- `grow(part, r)`: the part grows (r > 0) or shrinks (r < 0) by r all round.
- `glue(dst, src)`: `src` is moulded onto `dst` and stops existing as its own part.
- `nofeat(part)`: the part loses its cuts and features.
- `dup(part, (dx, dy, dz))`: a stacked copy of the part.
- `param(NAME=value, ...)`: a design constant in `pan_coil_b` changes.
- `both(op1, op2, ...)`: several at once.

## How to run (in this folder, with `python`)

- `python run_checks.py`: the design, all five checks. About 5 minutes.
- `python run_checks.py --control`: each check's negative control.
- `python run_checks.py my_mutants.py`: every mutant in your file against every check, in parallel. Write the file
  as `from operators import *` and `MUTANTS = {'A01': (move('servo', (0, 0, 1.0)), 'servo 1 mm high'), ...}`.
  Budget about 15 mutants; a full run takes roughly 20 to 30 minutes, so run it in the background and wait.

## Rules for this run

- Work only inside this folder. Do not read any file outside it: no repository, no notes, no git history.
- End your report with the full path of every file you read.
