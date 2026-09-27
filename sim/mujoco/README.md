# The head in MuJoCo

The v2 pan/tilt head as a physics model, for moving it by hand now and training on it later.
Chosen over Isaac Sim on 2026-09-27 (`docs/decisions.md`).

```
python sim/mujoco/build_head.py    # writes out/head.xml and out/head.png, prints masses and a servo test
python sim/mujoco/view_head.py     # opens the viewer: servo sliders, Ctrl+drag to shove the head
python sim/mujoco/mouse_look.py    # look through the head's camera and steer it with the mouse
python sim/mujoco/butterfly.py     # the head tracks a butterfly by finding it in its camera image
python sim/mujoco/train_bird.py    # trains the bird predictor (~30 s on the RTX 5070)
python sim/mujoco/bird.py          # the head tracks a bird smoothly, by predicting where it's going
python sim/mujoco/pan_stop.py      # how much the pan overshoots when it stops, and what fixes it
```

`build_head.py` reads the current exports (its docstring lists the build steps that write them), so
rebuild after any CAD change. Everything it and the trainer write goes in `out/`, which is untracked.
Each viewer script has a `--selftest` that runs without a window and checks itself against a control.

## The windows

**Keys everywhere:** click the window to steer with the mouse, Esc frees the cursor (again to quit),
Q quits, R recentres, +/- change the mouse sensitivity, Tab hides the outside view.

**`mouse_look.py`** shows the head camera's view. The servos keep their MG90D speed, so a fast flick lags.

**`butterfly.py`** tracks a butterfly by camera. Every frame (30 a second) it finds the butterfly's
pixels and, after the camera delay, turns the servos to centre them. The detector is perfect, a
stand-in for YOLO: MuJoCo labels the pixels. Space locks on or lets go (T does the same), [ and ]
change the delay, B changes the butterfly's speed. The green box is what the detector saw, drawn where
it was when the frame was taken, so it trails by the delay.

**`bird.py`** does the same with a pigeon-sized bird, flown by `flight.py` 1.5–5 m out and 0.5–2.5 m up.
Its detector is made more like YOLO: 640×480, a 2-pixel jitter, and 5% of frames missed. M switches
between three ways of steering:

| Mode | What it does |
|---|---|
| hold | today's tracker: jump the servos to the last sighting |
| line | draw a straight line through the last 7 sightings and follow it forward |
| learned | the trained network predicts the next 0.5 s of the path, and the head follows that |

In line and learned, the servo target moves continuously rather than once a frame, and each new
prediction fades in over 50 ms. That's what makes it smooth; the prediction is what keeps it on the
bird. The teal dots are the predicted path.

## The bird predictor

`train_bird.py` flies 2,000 birds for 40 s each and sees them as the camera would: 30 frames a second,
with jitter and missed frames. It then trains a small network on the RTX 5070. The network has three
layers and 80,000 numbers. Its input is the last 12 sightings (0.4 s); its output is the path over the
next 0.5 s. It's saved as plain numpy weights (`out/bird_predictor.npz`), so running it needs no PyTorch.
It's small enough for the Pi's CPU.

On 500 test birds it never trained on, the mean miss is (`out/bird_training.png`):

| Predicting ahead | 100 ms | 150 ms | 200 ms | 300 ms | 500 ms |
|---|---|---|---|---|---|
| hold (today) | 4.9° | 7.2° | 9.5° | 14.2° | 23.3° |
| line, last 7 sightings | 1.8° | 2.5° | 3.3° | 5.1° | 9.5° |
| learned | 1.3° | 1.8° | 2.3° | 3.5° | 6.3° |

"line" had its look-back picked to suit it best, so the network is beating the strongest version of it.

**In the sim** (`bird.py --selftest`): the same 60 s flight each run, scored from the first sighting.
"On target" means the lens is within 3° of the bird. Jumpiness is how hard the head accelerates, which
is what shakes the picture.

| | on target | mean miss | jumpiness (deg/s²) |
|---|---|---|---|
| tracking off (control) | 0% | 86° | — |
| hold, 100 ms delay | 13% | 9.0° | 9,050 |
| line, 100 ms | 77% | 5.4° | 6,610 |
| **learned, 100 ms** | **83%** | **4.9°** | **5,150** |
| hold, 200 ms | 3% | 13.4° | 9,000 |
| line, 200 ms | 55% | 7.0° | 7,880 |
| **learned, 200 ms** | **62%** | **6.0°** | **6,400** |

## Findings

- **Camera delay costs more than servo speed.** The butterfly with no delay is on target 79% of the
  time; with 100 ms, 30%. Measure the real camera-to-detection delay. Prediction wins most of it back.
- **The pan's ±180° stop costs about 0.3 s each time a bird circles behind.** The head has to swing
  about 340° the other way. In the bird runs, every miss over 20° after the first sighting was one of
  these swings (7 in 60 s). Unwinding early, while the bird is still out front, would hide it.
- **The pan overshoots about 8° when it stops a 90° move; smooth commands cut that to about 1°**
  (`pan_stop.py`). The 2:1 step-up makes the drum feel four times heavier to the servo. Drag, a lighter
  cradle, or a servo that brakes itself help less. Gear play isn't modelled.
- **A wide lens trades range for coverage.** At 320×240 through the 100° lens, a pigeon 6 m out is
  about 3 pixels and gets missed one frame in five. Real YOLO wants 10 or more pixels.
- **The butterfly misses by 2–4° even with no delay.** Its wingbeat bob (±2°, 5 times a second) is
  too fast for 30 frames a second, and its wings sit above its body (0.7°). With the bob and flap
  switched off (`BOB, FLAP = 0`), it's on target 100% of the time.

Two bugs in the sim itself were found by checking where the misses came from:
- The first flight model let birds sink through the floor (95% dipped under 0.25 m) and wander out to
  9.5 m. The limits are firm now: 0.34–2.7 m up, and at most 6.3 m out.
- The bird was "seen" at its placeholder spot before it first moved. That phantom sighting sent the
  head the wrong way at the start.

## What's in the model

| Piece | Parts | Moves |
|---|---|---|
| base | well, gear bay, pan servo, 6809 bearing | fixed |
| pan | drum, cradle, post, bearings, screws | about Z, ±180° |
| input gear | the pan servo's gear | tied to pan: turns −½ as far |
| tilt | both ball halves, the tilt servo (a box), the camera | about Y at Z 52, −35…+145°, + = lens up |

Also: `head_cam`, a camera at the lens tip; a red `target` ball; the butterfly; the bird; blocks and
posts to look at.

## What's a guess

- **Every mass.** Printed parts are volume × 1.35 g/cm³ (PETG-GF) × 0.8 fill. Replace them with slicer
  grams in `SLICER` at the top of `build_head.py`. The camera's 6 g is a guess too.
- **The servos** are the MG90D datasheet at 4.8 V: 0.196 N·m stall, 60° in 0.10 s. The 5° "pushing
  flat out" band and the motor inertia are guesses. Measure the real servo's speed and overshoot, and
  tune `DEADBAND` and `ROTOR` until the sim matches.
- **The bird's flight** is made up: smooth random turns, climbs and speed changes, around 4 m/s. Real
  birds dart, perch and land. Film some, and the predictor can be trained on real tracks.
- **Not modelled yet:** the pan gears' ~1° backlash (the play between the teeth), friction in the
  bearings, and the fisheye lens (`head_cam` is an ordinary 100° camera).
- **Nothing collides.** The joints hold the parts together, and the joint limits stand in for the
  stops.
