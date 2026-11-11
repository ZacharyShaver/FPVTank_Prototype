# Fable review of the Scorpion project, 2026-11-10

Zach asked Claude (Fable 5.2) to review the project the way a consultant brought in from outside would: the ideas it is
trying to prove, how they have been built so far, the decisions in `docs/decisions.md`, the paper, the code, and how
Zach himself works. This is that review. It is critical on purpose, and where it criticises work Claude did, it says so.

**What was read:** all 47 entries of `docs/decisions.md`; `CLAUDE.md`; `gauges/README.md` to the noisy-copies section;
the paper's draft v6 and the review of v5; `checks/README.md` and its registry; the 2026-11-03 code audit;
`gauges/SHOPPING.md`; the top of FPVTank_Control's `ROADMAP.md`; and samples of the code in `gauges/`, `twin/` and
`research/`. The ideas were checked against the literature on OpenAlex (section 10). Section 11 lists what was not read.

Nothing in this review is a decision. Every recommendation is for Zach to accept or turn down.

## 1. The short version

**What is good here, and uncommon**

- **Negative controls.** Every check has to fail on a broken version. This habit has caught 19 wrong checks and is the
  best engineering idea in the project.
- **Zach's plain questions and bench verdicts.** "How does the gear get in?", "the design is getting away from us",
  "eyeballing this it looks very thin". These have beaten the automated checks more often than the reverse.
- **An honest log.** Reversed decisions stay, guesses are starred, failed controls are reported. Few projects can be
  audited this way.

**Five findings**

1. **No number has ever been measured on a robot that drives.** About 23,000 designs were screened in the simulator.
   Six of the eight gauge cards still say "Trust: none yet". The 2026-11-08 working rules name this, but the work since
   then (the brain box) does not close it.
2. **Most of the critical-path parts are not ordered, and the robot's code has stood still.** One drive motor is on its
   way (Zach, 2026-11-07); the other four, and everything else on the list, are not ordered. FPVTank_Control's last commit is 2026-10-13,
   with a bench session (Task 18) still owed.
3. **The simulator is validated for one thing and used for eight.** It is checked for how a passive printed shell comes
   to rest after a short drop. It is used to rank steps, turns, hills, crests, tows, rough ground and tail righting,
   on a guessed tyre grip, a motor rated at a voltage the packs don't supply, and a tail servo that never tires.
4. **The paper's method stopped being used when the paper went in.** The live findings log ends on 2026-10-17. The check
   library's own README says "Nothing gates a print yet", and its files have not changed since 2026-10-30. The box
   prints of 2026-11-09 went out with no committed prediction, and their failures were not logged as escapes.
5. **The brain box is the head's story again.** Six holder designs in three days (frame, caps, bricks, boxes, Gridfinity
   boxes, spring stack), two of them printed, fits drawn inside the printer's noise, for a robot that has no wheels yet.

**Five pieces of advice, in order of value**

1. Order the other four motors today (section 9, step 1). Nothing else in the project is as cheap or as blocking.
2. Name one goal for the next two weeks: a robot that drives off the wall, with gauges predicted before and measured
   after. Park everything that doesn't serve it, the brain box included.
3. Measure four numbers before printing any body: the motor's stall torque and free speed on the 2S pack, the tyres'
   grip on Zach's floor, and the built robot's mass and centre of mass.
4. Do the software now, while the parts ship. Encoder firmware and a logger are Zach's own trade, and without a log
   there is no sim-against-reality comparison at all.
5. Put the paper's method back to work on this project: a committed prediction before every print and every bench test.

**The one big thing** (section 8): the project plans to validate the simulator with one finished design. A design search
is a claim about *differences* between designs, and one robot can't test a difference. Build an adjustable test rig, a
"mule", that can be many designs in an afternoon, and test the simulator's slopes and cliffs, starting with its plainest
design, the box.

## 2. What the project is trying to prove

There are three goals, written in three places, and they ask for three different robots.

| Goal | Where | What it needs next | What it does not need |
|---|---|---|---|
| An FPV tank that is "dumb in the chassis and smart on the desktop", with a ROS 2 and Isaac Sim twin | Control `ROADMAP.md`, north star | The owed bench session, desktop driving, battery power | A shape search, a modular box |
| AI embodiment: "dropped anywhere", survives, gets where it needs to, moves things; learned policies first | `docs/decisions.md`, 2026-10-26 | A policy-training pipeline and actuators that match the sim | A hand-scripted reflex tuned to one body |
| "A working robot for pitching the sim vs reality" | `docs/decisions.md`, 2026-11-08 | A driving robot with logging, and predictions committed before tests | Self-righting, a head, a tail camera, a tumble-proof box |

Each pivot since September followed whichever goal was most interesting that week. The third goal is the newest and the
only one with a deadline-like pull, so this review takes it as the current one. It needs a written exit test, which it
doesn't have yet. A suggestion: *"Four gauges, each predicted by the sim in a commit, then measured on a robot driving
untethered, with the scores published either way."*

Two smaller notes on the goals:

- **The roadmap still names Isaac Sim and ROS 2**, while all the simulation work is in MuJoCo (a sound choice,
  2026-09-27). One of the two documents is out of date.
- **"Learned policies first" has no work behind it.** Every gauge runs a hand-written reflex. That is fine for now, but
  it means the search has been answering "which body suits this script", not "which body is best" (section 3.1).

## 3. The ideas, reviewed

### 3.1 Designing by simulator search

**Verdict: a good tool, run far past what it has been checked for.**

What has been checked physically, against what the sim is used to conclude:

| The sim is used to conclude | Physical check so far |
|---|---|
| How a passive printed shell comes to rest after a 6 to 30 cm drop | About 540 drops, predictions committed first. Brier scores 0.48 to 0.69 against a best possible 0.44 to 0.61. **Validated.** |
| The effect of moving weight on that | **Over-predicted** at 15 and 30 cm (the paper's H3) |
| G1 with a tail righting the robot | None |
| G2 step, G3 turn, G4 and G5 hills, G6 crest, G7 tow, G8 rough ground | None: "Trust: none yet" on six cards |
| Drive torque and speed | The seller's 12 V figures. The packs are 7.4 V, so both are about 0.62 of that (2026-11-03 audit) |
| Tyre, body and floor grip | Guesses: 0.9, 0.4, 0.6 |
| Tail servo torque | Ideal. Upright falls from 1.00 to 0.76 at 85 % strength (`noisy.py`) |
| Wheel speed control | Closed loop in the sim. The real ESC is open loop |

The second row matters more than it looks. The one sensitivity the project has tested for real, moving coins to shift
the centre of mass, is the one the sim got wrong. The gauge search's sharpest conclusions are centre-of-mass effects: G3
moves 12 to 15 mm per millimetre of it, and T3's step drops from 150 to 57 mm when it moves 5 mm.

**The search's findings match a known pattern.** Koos, Mouret and Doncieux (2012) studied exactly this situation and put
it in one sentence: "the most efficient solutions in simulation often exploit badly modeled phenomena". Lehman et al.
(2020) collected dozens of cases. This project has its own collection:

- hills passed by toppling slowly (90 of 712 screens beat their static tip angle);
- 55 % of the capability run's designs with parts floating off the body;
- T3's nose parked within 10 mm of the climb cliff;
- centres of mass placed to the millimetre;
- tail servos that appear to be sized just above the strength where righting fails (the README's own "probably").

The lessons folder records each one as it was caught. What it doesn't record is the general rule: **an optimiser's best
design is the design most likely to be an error**, because it was chosen for scoring high, and errors score high. Smith
and Winkler (2006) call the statistical half of this the optimiser's curse. So the finalists are the last designs to
trust without a test, not the first.

**Zach's own instinct here was right and came three weeks late.** His noisy-copies idea from the ST5 antenna is Jakobi's
(1997) "envelope of noise": make the simulator disagree with itself so a design can't rely on any one detail. It should
be in every search from the first screen, not read on the finals afterwards. It is cheap and it is already written.

**The body was searched with the controller held fixed.** Cheney et al. (2018) showed why this misleads: a new body
usually needs its controller re-tuned before it shows what it can do, so a fixed script rewards bodies that happen to
fit the script. The project found this three times without naming it: "G2 reads the controller as much as the body",
the G3 spin is open loop, and hill climbing depends on the speed loop (K6).

**T3's 150 mm step should be read as a hypothesis.** Its wheels are 45 mm in radius, so the step is 3.3 wheel radii. The
sim's own plain box climbs 30 mm on 55 mm wheels, about half a radius. The whole gain comes from two mechanisms: the nose
riding up the step's face, and the tail pushing from behind. Both rest on guessed numbers (body friction 0.4, an ideal
3.3 N m servo), and the result sits on a cliff. It may be real. It is the first thing a real test should try to break.

**What the sim has already told the project, that needs no validation to act on:** the numbers that move the gauges are
tyre grip, motor torque, servo torque, where the centre of mass sits, and the controller. None of them is a body shape.
All but the controller can be measured in one evening once the parts are in hand.

### 3.2 Requirements as gauges

**Verdict: the right framing, with the discipline lost inside a day.**

Fixed tests that read a number, a plain box read every time as the baseline, the worst over a friction band, a control
that must read worse: all sound. The friction band is a crude form of the dynamics randomisation that sim-to-real work
relies on (Peng et al., 2018).

- **The count grew from three to eight in a week.** The card for iteration 1 says three gauges "on purpose: fewer things
  to test". G4 to G7 were adopted the next day, G8 a week later. Rule 5 says the sim is trusted only as far as a real
  test has checked it; no gauge was held to that.
- **Two gauges read something else.** G3 mostly reads the centre of mass's offset and open-loop drift. G7 tow reads the
  robot's weight (r 0.88). The project found both itself. Neither should rank a design until it is fixed or dropped.
- **No gauge has a bench version.** A gauge is only a requirement once it says how to run it for real: what surface,
  what step, how the robot is launched, how many tries, how long it takes. Section 9 proposes writing that line for four
  of them. G1 as written (200 random drops from 300 mm) can never be run on the real robot, only on a weighted dummy.
- **The readings are noisy by construction.** "18 of 20, every lower rung passing" is a minimum over many coin flips; a
  design that truly passes 90 % of the time passes 18 of 20 only about two times in three. The pooled rule
  (`STEP_RULE = 'pooled'`) fixes this for the step. It should be the rule everywhere, with an interval beside each number.

### 3.3 A tail in place of a righting shell

**Verdict: plausible and supported by the literature, unproven here, and mechanically the riskiest part of the robot.**

Tails on robots are established. Casarez and Fearing (2017) right a small robot from the ground through tail contact in
about a quarter of a second. Johnson et al. (2012) derive design rules for tails that turn a falling robot in mid-air,
on robots of 177 g and 8.1 kg. Shin et al. (2022) found tails improved a stair-climbing platform in simulation and
confirmed it by experiment. Kessens et al. (2014) give a metric for how well a given body and limb can right itself,
with limb length and limb-to-body mass as its variables: a direct reference for sizing this tail. So the idea is not
exotic.

Three risks are specific to this project:

- **The servo.** The sim's tail gives its full stall torque for as long as asked. A hobby servo can't; its torque sags
  as it heats. `noisy.py` shows righting is the gauge most sensitive to this, with a cliff between 90 and 85 %.
- **The mechanism.** A tail on a turntable, with power and signal wires through a rotating joint, is the same class of
  problem as the pan coil, which took eleven print sets. A tail camera later adds a ribbon to it.
- **The power.** Two or three large servos stalling together draw several amps each. The slot kept for an 8 A servo
  regulator is a guess until a real servo's stall current is measured.

**Recommended:** before any body is designed round it, bolt a tail to a weighted brick of the robot's mass and test two
things on the floor: does it right the brick from its back and sides, and how hard can it push down for 0.9 s. That is
one small print, two servos, and it tests the sim's largest claim (upright 0.68 without the tail, 1.00 with).

### 3.4 Checks that can fail

**Verdict: the strongest idea in the project, and currently not in use.** Section 5 covers the paper. As practice:

- The check library was designed on 2026-10-24 with five roles (designer, adversary, gatekeeper, intake, auditor). It has
  gated no print. Five roles is heavy for one person; that may be why.
- The lightest version that keeps the idea is one line: **before every print or bench test, commit a sentence saying
  what Zach should see.** The paper's best results (H2, H3) came from exactly that. It costs a minute.
- The mutation harness covers geometry. The paper itself says 13 of 16 bench findings were forces and wiring. Every box
  failure on 2026-11-09 was a force or fit failure. The method is aimed at the minority of the faults.

### 3.5 The modular brain box

**Verdict: premature. Freeze it until the robot drives.**

The history: Zach proposed a modular floor on 2026-11-08 ("i have a very cool idea to make this modular"). Three days
later there had been six holder designs, two of them printed, and the second print showed that pegs, holes and pads
drawn to 0.1 mm sit inside the printer's noise. The working rule "three sets on one subsystem means stop patching" was noted at
the fourth design and then passed.

Claude's part in this deserves plain words. Claude drew all six, and each one answered the question asked instead of
asking whether a fastening system was the next thing the robot needed. On the last two:

- **`print_noise.py` reinvents a standard method.** Rolling dice on every hole's position and asking how often the part
  assembles is Monte Carlo tolerance analysis (Yan et al., 2015; Qureshi et al., 2011). The method is sound. The inputs
  are not: the printer's real error has never been measured, so the table's percentages are placed by a guess.
- **The spring stack's locating is not the textbook answer.** It uses two loose pegs and lets the slop absorb the error
  in their spacing, so the box can shift 0.25 mm until the clip clamps it. The standard way to locate a part on two pins
  is a round pin and a *diamond pin*: a second peg with flats cut on the two sides that face the first peg, so it touches
  its hole only crosswise. The first pin fixes position, the second fixes rotation, and the spacing can be off by half a
  millimetre without jamming. Both pegs can then be the snug 5.0 in 5.1 fit Zach liked, with no rattle, and the floor
  stays a plain pegboard. This is exact-constraint design (Slocum, 2010). It is untested here.
- **The TPU clip is a designed part where a bought one does the job.** Its force rests on a guessed stiffness, and
  printed TPU relaxes under a held load. A strip of closed-cell foam under the lid does the same work, costs nothing to
  design, and can be tested in ten minutes. Foam first; the clip only if foam fails.

For the pitch robot none of this is needed. Hobby RC cars and drones settled this long ago: packs under hook-and-loop
straps, ESCs on double-sided foam tape with a zip tie, boards on screws. Those joints tolerate millimetres. The Pi's
friction box already works and stays.

## 4. The decisions, reviewed

| Date | Decision | Verdict | Note |
|---|---|---|---|
| 08-03 | Fusion for design, Blender for mesh surgery | Sound | |
| 09-18 | Head v2, the ball in a nest | Costly | Eleven pan sets, working on 10-12, shelved 11-07 by a roll question nobody asked first. The lesson is recorded. Keep it shelved. |
| 09-19 to 09-27 | Negative controls, exact booleans, Zach's Fusion model as the source of truth | Sound | The best decisions in the log. |
| 09-27 | MuJoCo, not Isaac Sim | Sound | The Control roadmap still says Isaac. |
| 10-05 | Wheels for training, tracks on hold | Sound | The consequence wasn't drawn: the built drivetrain (tracks, 540 motors) left with it, so a new drivetrain became the longest job, and it wasn't started. |
| 10-26 | Repo public, history rewritten first | Sound | |
| 10-26 | Requirements as gauges, three to start | Right, not held | Eight gauges in a week (section 3.2). |
| 10-26 | A tail instead of a righting shell | Unproven | Section 3.3. |
| 10-28 | The capability search: "max out every single goal" | Low value | 55 % impossible bodies; two families already known. No real test was named for it. |
| 10-29 | One-piece bodies grown by a voxel FEM | Park | 1,273 lines that no test in reach can check. |
| 10-30 | JGB37-520 motors; keep the RC ESCs | Motor fine; ESC a risk | One is on its way, not yet calipered. Closing a speed loop through a brushed RC ESC at a crawl is likely to be awkward (many have a drag brake and a reverse delay; check his). Two MDD3A drivers are $25: order them with the motors as a hedge. |
| 10-30 | A 12 V motor on 2S packs | Open | Every ranking used the 12 V figures. Either re-read at 0.62, or run the drive on a 3S pack if the ESCs allow it. Measuring the real motor settles which. |
| 11-07 | Bodies capped at 250 mm | Open | The reason is fair (long prints in tough materials fail). But 3 of 394 capped bodies hold the parts. The cap or the part list has to give, and the two 5200 packs are the longest parts. |
| 11-07 | Head off, fixed nose camera | Sound | |
| 11-08 | One pack for the motors, one for the Pi | Workable | One pack for both, through the Pololu, would drop about a quarter kilogram and the longest part in the box. Four small gearmotors barely load a 5200 pack. Test for a Pi brownout at motor stall on the bench before choosing. |
| 11-08 | Stop button in the OE line | Sound | One gap, already written down: a hung Pi with its power still up leaves the motors on their last throttle. The ESP32 is already on board; let it hold OE and release it only while the Pi sends a heartbeat. |
| 11-08 | IMU on its own serial wire | Sound for logging | That mode gives no gyro rates. A tail reflex will want them: a second I2C bus later, not a shared one. |
| 11-08 | A modular pegboard floor | Premature | Section 3.5. |
| 11-08 | The working rules | Sound | Two were passed within two days: three sets, and requirement before part. |
| 11-09 | The lid is the hold | Sound | It removed a requirement, which is the cheapest kind of fix. |

**The log itself.** `decisions.md` is 1,004 lines. The word "superseded" appears 42 times, about a dozen of those reversals
came on the day of the decision, and "not printed" or "never printed" appears seven times. That is honest record-keeping of a real
problem: decisions are being made faster than the bench can test them. The log also has no page that says what is true
*now*. A reader has to replay it from the top.

## 5. The paper, "Checks That Can Fail" (draft v6)

**Strengths.** It is candid to a degree reviewers rarely see: "That pass was partly luck" is its best sentence. H3 is
good science: predictions committed first, a ceiling computed from the drops' own randomness, a blind third test that
held. The framing (test the tests) is clear and transfers. The transition test ("a second team runs the harness on its
own vehicle without me") is concrete.

**Weaknesses, most serious first**

1. **The opening claim outruns the evidence.** Section 1 says simulation and surrogates "can replace most builds". The
   pilot's own data says 16 of 26 flaws surfaced only at the bench, and that most of those were forces and wiring that
   no check models. The data supports a narrower and more interesting thesis: *checks reliably catch geometry and
   assembly faults before printing; they do not yet catch force faults; the contribution is a way to know which is
   which.* The paper nearly says this in its "Escapes" bullet and should lead with it.
2. **The surrogate (H2) solves a problem the pilot doesn't have.** A full 200-tumble evaluation costs about 0.19 s
   (400 designs in 74 s). A surrogate that saves 95 % of those saves almost nothing, and only 10 of the 280 held-out
   designs clear the bar, so answering "no" every time is right 270 times. Its error (3.9 points) is at the simulator's
   own noise (about 3.5). What H2 does show is valuable but is buried: the intervals failed at the six best designs,
   "exactly where a design gets chosen". That is the optimiser's curse again (Smith and Winkler, 2006), and it should be
   the headline of H2, with conformal intervals (Angelopoulos and Bates, 2023) as the named fix.
3. **H1's numbers are small and partly circular.** 21 of 22 has a 95 % interval of roughly 78 to 99 %; the out-of-sample
   7 of 8 spans roughly 53 to 98 %. "22 of 22" includes a check written for the one survivor. The mutants and the
   checks came from the same model. The backtest of 2026-10-24, where a separate adversary agent found two surviving
   mutants and three faults in the checks' own controls and scoring, is stronger evidence than H1. It appears in the
   paper only inside the count of 19; it deserves to be H1's main result. Equivalent mutants (a planted change that
   isn't really a fault) aren't discussed; Kavak et al. (2026) name them among the main practical challenges of
   mutation testing design models in industry.
4. **"Never by the check itself" is true almost by definition**, and "19 times" has no denominator. The v5 review flagged
   both. A count of check runs, or of checks, would make it a rate.
5. **H4 has no baseline.** A median of 1.6 hours from finding to fix-ready says nothing about speed-up without a
   comparison. And a sceptical vehicle engineer will read "11 design iterations in 16 days" for one pan drive as low
   first-pass yield, not as pace. The answer exists (iterations are cheap at this scale, and the method is aimed at
   scales where they aren't) but the paper doesn't give it.
6. **It doesn't place itself against engineering practice.** Tolerance analysis, design-for-assembly checklists and
   failure-mode analysis are how mechanical engineers already catch many of these faults. The claim should be that
   mutation scoring measures such checks, not that checking is new. The validation literature is also thin for a
   national-lab panel: Oberkampf and colleagues' reports on validation and predictive capability are the standard
   references, and the idea of a *validation domain* (a model is trusted only near where it was tested) is exactly the
   paper's point about its own simulator.
7. **Related work in its own field is missing.** Mutation testing of design models is established for Simulink (Bartocci
   et al., 2023). Agents that generate CAD and verify it are an active area: CADCodeVerify (Alrashedy et al., 2024),
   BenchCAD (Zhang et al., 2026), and "Physics-in-the-Loop" (Berger et al., 2026) on OpenAlex by title. Two searches
   found nothing applying mutation testing to mechanical CAD checks, so the novelty claim looks open. Citing the
   neighbours makes that claim believable.
8. **External validity.** One engineer, one agent, one robot, printed plastic. The Risks section admits it.

**What to do with it now**

- **For an interview:** the strongest new material is what happened after submission. A simulator search ran for two
  weeks without bench gating, screened 23,000 designs, produced floating parts and slow topples, and carried five code
  bugs that only an audit found. Told straight, that is a case study for the paper's thesis, not against it.
- **Restart the live log.** `iterations_live.csv` stops at L17 on 2026-10-17. The paper promises "a dataset of design
  iterations, escapes and cycle times". The box prints alone are five or six rows.
- **Minor:** the draft in the public repo still carries the `[Your name]` and `[Org]` placeholders. Fine if deliberate.

## 6. Code quality

**What is good:** checks with controls built into most modules; code stamps on resumable runs (`tools/stamp.py`); pinned
dependencies; exact booleans for shipped parts; the leak scanner has real tests; the 2026-11-03 audit found and fixed
real physics bugs with a control for each.

**What is wrong, most costly first**

1. **Zach can't review it.** The code is written densely, for an agent to re-read: `gauges/search.py` has 161 lines that
   join statements with semicolons; `twin/part_boxes.py` has 66 lines over 160 characters and one of 695; names are
   single letters (`P`, `H`, `W`, `S`). He is a software engineer of many years and the one person placed to catch
   software faults in his own project, and the style takes him out of that loop. The tyre-spring unit bug sat in every
   landing result until an agent audit found it.
2. **Guessed numbers are bare constants.** Zach asks for a list of every guessed number with each design. Those lists
   are written by hand, so they drift from the code. A small wrapper, `guess(value, why)` beside `measured(value, how)`,
   would let the list be generated, let `noisy.py` and `print_noise.py` draw their errors from the same registry, and
   show at a glance how much of a result rests on guesses. This is the single most useful refactor.
3. **Superseded code stays live.** `holders.py` (543 lines) and `bricks.py` (547) were superseded before anything was
   printed. The head generator carries about 15 on/off flags that rebuild old sets. "Never delete a decision" is right
   for the log; applied to code it multiplies paths, and it caused check failure C17 (a control rebuilt from a dead
   branch). Git already keeps history. Tag the commit, name the tag in the log, delete the code.
4. **No package, no fast tests.** Every module edits `sys.path`; runs are selected by environment variables
   (`SCORPION_SEARCH`, `SCORPION_CAP`), so reading the wrong run's results takes one forgotten `set`. The `check`
   subcommands are good but take minutes and run by hand. The only pytest files cover the leak scanner and the gallery.
   Pure functions such as `hull_dist`, `spring_solref`, `inertia` and the ladder rules could have unit tests that run
   in a second on every change.
5. **The 3D viewer exists 23 times.** There are 27 page templates, and 23 of them set up their own three.js viewer.
   "fix that viewer its buggy as hell" was the result. One viewer module and one scene format would end it.
6. **Pages are written inside geometry modules.** The longest lines in `twin/part_boxes.py` are paragraphs of page text
   in Python strings. Copy belongs in the template or a data file.
7. **Units cross in many places.** Specs are in millimetres and grams, MuJoCo in SI, with `S = 1e-3` applied by hand.
   One conversion boundary would have prevented the spring bug's class.
8. **Repeated geometry.** `limb_mount`, `rear_surface` and `nose_mount` in `gauges/robots.py` are the same ray-and-hull
   routine written three times.
9. **History lives in docstrings.** "Until 2026-11-03 k went in as it was..." is a changelog entry. It belongs in the
   commit message, where it is dated for free.

None of this needs fixing before the robot drives. Items 1 and 2 are worth doing first when it does.

**Uncommitted work.** The last commit is 2026-11-03. A week of work (43 paths, including `decisions.md`, `CLAUDE.md` and
all of the brain box) is only on one disk. The paper's central claim, predictions "committed to version control before
their tests", depends on commit times being routine.

## 7. How Zach works: what to keep, what to change

**Keep**

- The plain questions. They are worth more than any check in the registry.
- Calling a result from the bench and stopping runaway work out loud.
- Quoting himself in the log, and never deleting a reversal.
- Asking for a review like this one.

**Change**

1. **The tool has been setting the agenda.** An AI agent produces designs, simulations and pages at almost no cost, so it
   fills any gap with them. Zach's scarce resource is bench hours, and the project isn't budgeted in them. A rule that
   would have prevented most of October: *each session ends with something Zach can hold or a number he can measure.*
   If the honest answer to "what will I hold?" is "a page", park it.
2. **Approvals come in batches and in two words.** "Yes, do it", "unlock those yes", "Yes, print it". The audit already
   found that of 11 picks approved together, 8 changed within a day. A short approval of a long proposal approves the
   agent's framing along with it. Before saying yes, ask what real test will check the result, and when.
3. **Ideas are acted on the moment they arrive.** The modular floor came in the middle of a parts review and took over
   the next three days. The ideas are often good (the noisy copies, the tail, the lid as the hold). They need a parking
   list and one question: does this shorten the path to the first drive?
4. **Subsystems are dropped just before they are joined to anything.** The head worked on the bench on 10-12 and was
   never mounted. The tumble shells, the tail search, the one-piece bodies and the brain box each stopped at the same
   point. The interesting sub-problem gets solved; the dull work of joining it to the rest is deferred. Joining is where
   the failures the prototype exists to find actually live.
5. **Buying is treated as later.** The motor was chosen on 10-30 with the note "buy one first and caliper it". One is on
   its way; the other four wait on it. They are $12 parts with a shipping delay, and everything since has been designed to
   the listing. His own rule, never design
   round a datasheet when he could own the part, only works if the part is ordered the day it is chosen.
6. **Measurements are owed.** The log carries open asks that became guessed numbers in prints: which feature sets the
   ESC's 24 mm (noted 10-11, never asked), the ESP32 board's size (the box was drawn round a typical board and failed),
   the pack, whether the tight ESC top follows the ESC or the box, C10. Part of this is Claude's doing: it ends long
   messages with four questions and gets one answer. One list, kept in one place, worked through with calipers once a
   week, would clear it.
7. **Design is reviewed on a phone.** Approving a start over Remote Control is fine. Judging a 3D design there is not;
   the things Zach catches, he catches by looking closely.
8. **Elegance before function.** Modular, generative, unified: each is a property of a finished system. A prototype's
   job, in the roadmap's own words, is "to find the failure modes worth designing against". Tape and straps find them
   faster.

**Prompting, specifically**

- **Give the goal, the fixed things and the kill test, and leave the mechanism open.** "It must survive being flipped
  and shaken; the Pi's box stays; if a pack swap takes a tool it's dead" gets a better design than a description of
  Gridfinity. Analogies ("like a lego brick") get built literally.
- **When the mechanism matters, send a photo of a pencil sketch.** Several superseded designs came from Claude guessing
  at a sentence ("flip it", "snaps into another lid", "no folds, ever"). The log has about six places where Claude wrote "I
  read this as".
- **Ask these before any design:** *What is the cheapest test that could kill this? What could we buy instead of print?
  Which guess, if wrong, costs a reprint?*
- **Ask for the case against.** "Argue against this as a mechanical engineer would" before approving, not after.
- **Use the stronger model at the forks:** requirements, kill tests, choosing experiments, reviews. Use the other for
  carrying them out. Have every new session read a one-page state file first (section 9, step 3).
- **Say when a number is his caliper's and when it is a hunch.** He already does this with "ish"; the log shows it works.

**What to watch for in Claude,** so that Zach can prompt against it: it answers the question asked instead of
questioning it; it treats an offhand idea as a specification; it designs from a datasheet without stopping when the part
isn't in hand; it produces a page where a sentence would do; it logs faithfully and at a length nobody can re-read; and
it stacks its questions at the end of long messages.

## 8. The one big thing: test slopes, not points

The plan of record is to build a design the simulator likes and see whether it behaves as predicted. That tests one
point. But everything the simulator has been used for is a claim about differences: this nose climbs and that one
doesn't; a longer wheelbase buys hills and costs the step; 5 mm of centre of mass costs 90 mm of climb. **One robot can't
test a difference.** If T3 is built and climbs 80 mm, nobody will know whether the simulator's physics, its ranking, or
the build was wrong.

The project's own results are almost all slopes and cliffs:

| Knob | What the sim says happens |
|---|---|
| Nose reach ahead of centre | Climb jumps from 50 to 60 mm up to 140 to 150 mm between 197 and 205 mm |
| Centre of mass, fore and aft | Turn circle grows 12 to 15 mm per millimetre; T3's step falls off at +5 mm |
| Gap between the tyres (wheelbase) | Hills go from 25° / 30° to 50° / 50°; the step falls from 150 to 40 mm past 82 mm |
| Ride height | Below 52 mm the step goes; above it the hills go |
| Tail servo strength | Righting falls off between 90 and 85 % |

**So build a mule, not a robot.** In the car industry a mule is an ugly, adjustable test vehicle that exists to answer
questions before the real design is drawn. For Scorpion:

- a flat deck with rows of slots (a slot takes a screw anywhere along it, so nothing has to fit to 0.1 mm);
- the four motors on brackets that bolt through the slots, so the wheelbase changes with a screwdriver;
- a nose plate on slots, so its reach changes by 30 mm either way;
- the pack on a strap: by a rough sum, sliding a 5200 pack 40 mm moves the whole robot's centre of mass about 5 mm;
- spacer blocks under the deck for ride height;
- later, a rear plate for the tail.

Each knob the simulator calls a cliff becomes a wing nut instead of a reprint. An afternoon gives a five-point curve.

**Then use the paper's method on it.** Model the mule in the sim (it is close to the box the gauges already read every
run). Commit the predicted curves. Measure. Score two things: does the sim put each cliff in the right place, and does
it rank the settings in the right order. Koos et al. (2012) steered a whole search this way with "about ten experiments
on the physical robot". The ranking is what a design search needs, and it is what transfers even when the absolute
numbers are off.

**Start with the box.** Every gauge run reads the plain box as its baseline, so the sim has predicted it hundreds of
times: step 30 mm, turn 594 mm, hills 45° / 45° on grippy ground. A plain deck on four wheels is the cheapest robot
there is. Its measured numbers put a trust line on every gauge at once.

**Cost.** The shopping list already has the motor with a bracket and a wheel at about $12 each, so four are under $50;
the deck prints in two halves or is cut from plywood; the screws are on hand. Complete metal chassis kits with encoder
motors exist but ran about $200 when searched ([Hiwonder, RobotShop](https://www.robotshop.com/products/hiwonder-hiwonder-large-metal-4wd-vehicle-chassis-arduino-raspberry-pi-ros-robot-with-12v-encoder-geared-motor)),
which is over the budget.

**What this dissolves.** The brain box question (slots take straps). The 250 mm question (the mule can be run long and
short). The 2S question (measure it). The paper's missing evidence (predicted against measured, with commit hashes). And
it gives the pitch its figure: the simulator's curve and the bench's curve on the same axes.

**What it isn't.** It isn't T3, it won't right itself, and it won't look like a scorpion. That robot comes after, and
it will be drawn from measured numbers.

## 9. A two-week plan

Each step has a done-test. Nothing here needs a new search, gauge, knob or page.

| # | Step | Done when | Needs |
|---|---|---|---|
| 1 | Order the other four motors with brackets and wheels (one is already coming). Consider two MDD3A drivers with them. | The order is placed | 20 minutes, about $60 to $85 |
| 2 | Commit the working tree | `git status` is clean | Zach's go-ahead |
| 3 | Write `STATE.md`, one page: what is built, what is measured, what is guessed, what is owed to the bench, what is parked | A new session can start from it alone | An hour |
| 4 | Run the owed Control bench session (Task 18) on the robot as it stands | Phase 4c closes or its faults are listed | One evening |
| 5 | ESP32 firmware that counts four encoders, and a Pi logger that writes wheel speeds, commands and time to a file | A bench motor's speed appears in a CSV | Zach's own trade; no parts beyond one motor |
| 6 | Clear the measurement list: ESC, ESP32 board, pack, the ESC swap test | The stars come off those numbers | 30 minutes with calipers |
| 7 | When the motors arrive, measure four numbers: stall torque on 2S (a lever on a kitchen scale), free speed on 2S (the encoder), tyre grip on the test floor (pull the robot with a luggage scale, wheels locked), mass and centre of mass (balance the built mule on a dowel) | The four numbers replace their guesses in the sim | One evening |
| 8 | Build the mule's deck and brackets. Hold everything down with straps, tape and screws | It drives untethered and logs | Two or three prints |
| 9 | Write the bench version of four gauges: step (stacked boards), turn (a taped circle), static tip angle (a tilting board and a phone's level), tow (a luggage scale) | Each card says equipment, steps, tries and minutes | An hour |
| 10 | Commit the sim's predictions for the mule at two nose reaches and two pack positions | The commit exists before the test | A sim run of minutes |
| 11 | Run the four gauges. Score them. Log every surprise in `iterations_live.csv` | A table of predicted against measured | Two evenings |
| 12 | Only then: the tail on a brick (section 3.3), and the next design | | |

**Parked until step 11 is done:** the brain box and spring stack, the head, one-piece bodies, the 250 mm run, flippers,
any new search. When the brain box comes back, the version to hand to Opus is the diamond pin and foam of section 3.5.

## 10. References, checked on OpenAlex (2026-11-10)

Read as abstracts unless marked. DOIs as OpenAlex gave them.

**Simulation against reality**
- Koos, Mouret and Doncieux (2012). The Transferability Approach: Crossing the Reality Gap in Evolutionary Robotics. *IEEE Trans. Evolutionary Computation.* 10.1109/tevc.2012.2185849
- Jakobi (1997). Evolutionary Robotics and the Radical Envelope-of-Noise Hypothesis. *Adaptive Behavior.* 10.1177/105971239700600205 (title only)
- Acosta et al. (2022). Validating Robotics Simulators on Real-World Impacts. *IEEE Robotics and Automation Letters.* 10.1109/lra.2022.3174367. Drake, MuJoCo and Bullet on a tossed cube: inelastic impacts captured well, elasticity not. This matches the project's own floor-bounce finding.
- Peng et al. (2018). Sim-to-Real Transfer of Robotic Control with Dynamics Randomization. *ICRA.* 10.1109/icra.2018.8460528 (title only)
- Hwangbo et al. (2019). Learning agile and dynamic motor skills for legged robots. *Science Robotics.* 10.1126/scirobotics.aau5872. Known for modelling the actuators from data; cited here for the point that actuators carry much of the gap (from memory of the paper, beyond its abstract).
- Lehman et al. (2020). The Surprising Creativity of Digital Evolution. *Artificial Life.* 10.1162/artl_a_00319 (title only)
- Cheney et al. (2018). Scalable co-optimization of morphology and control in embodied machines. *J. R. Soc. Interface.* 10.1098/rsif.2017.0937
- Smith and Winkler (2006). The Optimizer's Curse. *Management Science.* 10.1287/mnsc.1050.0451
- Oberkampf et al. (2003). Verification, Validation, and Predictive Capability in Computational Engineering and Physics. Sandia report. 10.2172/809603 (title only)
- Angelopoulos and Bates (2023). Conformal Prediction: A Gentle Introduction. *Foundations and Trends in Machine Learning.* 10.1561/2200000101 (title only)

**Checks and mutation**
- Just et al. (2014). Are mutants a valid substitute for real faults in software testing? *FSE.* 10.1145/2635868.2635929. Found a significant correlation between detecting mutants and detecting real faults, and "some inherent limitations".
- Papadakis et al. (2018). Mutation Testing Advances: An Analysis and Survey. *Advances in Computers.* 10.1016/bs.adcom.2018.03.015 (title only; newer than the paper's reference [1])
- Barr et al. (2014). The Oracle Problem in Software Testing: A Survey. *IEEE Trans. Software Engineering.* 10.1109/tse.2014.2372785 (title only)
- Bartocci et al. (2023). Property-Based Mutation Testing. *ICST.* 10.1109/icst57152.2023.00029
- Kavak et al. (2026). Mutation Testing of Simulink Cyber-Physical System Models: Challenges and Solutions in Practice. 10.1145/3832783.3834529
- Alrashedy et al. (2024). Generating CAD Code with Vision-Language Models for 3D Designs. arXiv. 10.48550/arxiv.2410.05340
- Zhang et al. (2026). BenchCAD. arXiv. 10.48550/arxiv.2605.10865
- Berger et al. (2026). Physics-in-the-Loop: A Hybrid Agentic Architecture for Validated CAD Engineering Design. *IJCAI.* 10.24963/ijcai.2026/714 (end of abstract only)

**The robot**
- Johnson et al. (2012). Tail Assisted Dynamic Self Righting. 10.1142/9789814415958_0079. Righting in free fall, not on the ground.
- Casarez and Fearing (2017). Dynamic terrestrial self-righting with a minimal tail. *IROS.* 10.1109/iros.2017.8202174
- Shin et al. (2022). Design exploration and comparative analysis of tail shape of tri-wheel-based stair-climbing robotic platform. *Scientific Reports.* 10.1038/s41598-022-24179-5
- Kessens et al. (2014). A metric for self-rightability and understanding its relationship to simple morphologies. *IROS.* 10.1109/iros.2014.6943081
- Mandow et al. (2007). Experimental kinematics for wheeled skid-steer mobile robots. *IROS.* 10.1109/iros.2007.4399139. A measured model of how skid-steer robots slip in a turn: the reference for fixing or replacing G3.

**Printing and joints**
- Slocum (2010). Kinematic couplings: A review of design principles and applications. *Int. J. Machine Tools and Manufacture.* 10.1016/j.ijmachtools.2009.10.006 (title only)
- Qureshi et al. (2011). A statistical tolerance analysis approach for over-constrained mechanism based on optimization and Monte Carlo simulation. *Computer-Aided Design.* 10.1016/j.cad.2011.10.004 (title only)
- Yan et al. (2015). Application of Monte Carlo Method in Tolerance Analysis. *Procedia CIRP.* 10.1016/j.procir.2015.04.079 (title only)

Searches that found nothing useful: mutation testing applied to mechanical CAD checks (two queries), printed hole and
peg tolerances, and the creep of printed TPU. The claims in section 3.5 about TPU relaxing and about RC practice are
general engineering knowledge, not cited findings.

## 11. What this review did not check

- No code was run, and no result was reproduced. The numbers quoted are the project's own.
- `gauges/README.md` past the noisy-copies section, `twin/README.md`, the lessons' bodies and `head-v2/` were not read.
- `sim/mujoco/` holds `bird.py`, `butterfly.py`, `flight.py` and `train_bird.py`, which were not opened.
- Control's code, `HARDWARE.md` and the roadmap past its decision log were not read. "Task 18 still owed" is from the
  roadmap's own text and the date of its last commit.
- **Corrected 2026-11-10:** the first draft said no motor was ordered. It read the shopping list's "On hand" column and
  missed the note beside it: one is on its way (Zach, 2026-11-07, "next weekend").
- The submitted paper may differ from draft v6 in the repo.
- Prices and the RC-ESC behaviour described in section 4 are general knowledge to confirm against Zach's own parts.
- The diamond pin, the foam pad and the mule are proposals. None has been drawn, screened or tested.
