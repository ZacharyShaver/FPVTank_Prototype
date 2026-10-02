# The camera, as a solid

2026-09-20. Built by `../generators/camera_dummy.py`. STEP (Fusion opens it as a body, no
Convert Mesh) and STL.

| file | frame |
|---|---|
| `camera_dummy_centred.step` / `.stl` | **use this one.** The head's frame, lens midway between the board's holes |
| `camera_dummy_centred_origin.step` / `.stl` | the same, board back face at the origin |
| `camera_dummy.step` / `.stl` | **superseded 2026-09-27**: lens 1.6 off the board's centre (a photo value). Kept because the rev-1 regression table was run with it |
| `camera_dummy_origin.step` / `.stl` | the superseded one, board back face at the origin |

All four: the **head's** frame puts the **lens axis** on Z 52.0, the board back face at X 8.0 and the
lens tip at X 29.0 (`kit.camera(2.5)` moves it onto Zach's wall at X 10.5).

**2026-09-27: the lens is centred on the holes.** Zach: "the lens is directly center to the posts, your
camera model had it sitting off center". He moved his rev-2 post tubes +2.0 to match, by hand. The
photo put the lens 1.6 above the board's centre (`LENS_OFF_PHOTO`); it is 0 now (`LENS_OFF`).

The part is the Arducam OV5647 IR-CUT day-night module (`HARDWARE.md`): board, the round
motorised IR-CUT holder, the fisheye dome, the CSI ribbon socket, and the day/night light
sensor. Envelope 21.0 × 36.2 × 39.8, 9148 mm³.

It took four passes. The first three were wrong in ways worth keeping: two of them about
*how to read a photograph* rather than about the camera, and one about the model itself.

## Pass 1 → 2: the scale was 5% small

The caliper in the photo is **closed** — it is lying there as a ruler, not holding a reading
— so the scale has to come from a feature of known size. Pass 1 used the FFC connector's
1.00 mm pin pitch. Those pins sit about 3 mm **above** the PCB, and the photo was taken
close (~90 mm — the board fills a third of the frame), so 3 mm is a 3.2% magnification.
The right reference is a feature **in the board plane**: the 2.54 mm header pads.

| reference | reads | |
|---|---|---|
| header pads — flat, in plane | **17.87 px/mm** | **used** |
| FFC pins — 3 mm proud | 18.44 px/mm | = 17.87 × 1.032 |

The header row measures **2.537 mm** at this scale, against the 2.54 it was drawn to. Two
more checks agree: the FFC body de-magnifies to 20.6 mm (a 15-way 1.0 mm ZIF is 20.6), and
the implied camera distance matches the framing. ±1.5%, so about ±0.5 mm on the outline.

## Pass 2 → 3: the lens axis was on the highlight

Pass 2 put the lens axis on the bright pinpoint at the centre of the dome. On a fisheye that
pinpoint is **wherever the light source happens to reflect**, not the optical centre — here
it sat 66 px, **3.7 mm**, high.

The axis is now the centre of a least-squares circle fitted to the IR-CUT holder's outer
edge by radial gradient search (r 238.7 px, rms 5.1 px). It converges to the same answer
from every seed, and the holder's own two fastening screws settle it: they sit at 184 and
172 px from this centre, and at 155 and 238 px from the old one.

## Pass 3 → 4: the light sensor was not attached to anything

Zach, looking at the STEP: *"the top section for the ir sensor on the camera model is too
short."*

It was not short. It was **floating**. Pass 3 modelled the sensor with a 1.5 mm stand-off
above the board face, so the union came out as **two solids** — 96 mm³ of disc hovering in
front of the board with nothing joining it. Fusion shows that as a loose body; the render
sheet does not show it at all, because a floating lump and an attached one look identical
from outside.

The sensor now runs from the board face forward, and `camera_dummy.py` **refuses to write a
file that comes out in more than one piece**, printing each stray piece's volume and box. A
gap you cannot see in a render is a gap you ship.

## What the photo gives

| | |
|---|---|
| board | **36.2** across (along the tilt axis) × **36.0** |
| lens axis vs board centre | **1.6 mm toward the header edge**, centred across to within 0.4 |
| board edges from the lens axis | ±18.1 across · **−16.4 header side, +19.6 connector side** |
| IR-CUT holder | **round**, Ø26.7 — three quarters of the board's width, reaching down to the socket |
| fisheye dome | Ø14.8 at its base, tip at the measured 19.0 stand-off |
| mounting holes | **eight**, Ø2.0 on Ø4.0 pads |
| — outer set | 29.4 × 28.9 |
| — inner set | 29.4 × 14.0 ← **the second set** |
| | both sets centred on the **board**, 1.6 off the lens |
| CSI socket | 20.6 × 6.1, **on the lens face**, centred 16.3 below the axis, running to the board's edge |
| light sensor | Ø7.0 boot over a Ø4.87 cell — a stock 5 mm CdS — 16.6 above the axis and 4.9 across, standing **4.0 forward** of the board face |
| top header | 6 pads at 2.54, 14.8 above the axis and 4.5 to one side — flat, nothing to model |

Caliper, Zach: board **2.0** thick · stand-off board-front-face → lens tip **19.0** (*"21 mm
off the board, −2 for the board itself"*) · across the lens end **14–15**.

A radial fit to the dome's silhouette says 16.3 rather than 14.8. That fit is the poor one
here — rms 6.2 px against the holder's 5.1 on a bigger circle, because the highlight drags
it — and it is probably catching the holder's lip. **The caliper wins:** a number Zach
measured beats two off one photo.

A top-down photo cannot see height **at all**, so every out-of-plane number is either a
caliper reading or a call. `LDR_H = 4.0`, reaching forward the same way the lens looks, is
Zach's call (2026-09-20). Still assumed: holder height (`HOLDER_X1 = 18.6`), socket
stand-off, board corner radius.

**Not modelled:** the two IR LED pods. They are not in this print — later.

## Two things that survived all three passes

**1. The ribbon socket is on the lens side**, at the board's edge — not behind the board.
The ribbon leaves **forward**, into the gap between the board and the ball's front, and has
to turn to reach the rolling-loop track at the back. Nothing in the head models that run.

**2. There is a light sensor**, and after the lens it is the tallest thing on the board. It
hangs **3.8 mm past the header edge**, into space the head treats as empty.

## ⚠ What pass 2 claimed, and pass 3 withdrew

Pass 2 reported the board's two bottom corners standing **1.36 mm past the ball's inner
wall**, 7.1 mm³ of interference. **That was the mis-located lens axis, not the camera.**
With the axis 3.7 mm high the board hung 23.2 mm down on the connector side; it actually
hangs 19.6. The corners are clear, and so is everything else:

| | pass 3 | pass 2 | pass 1 |
|---|---|---|---|
| camera ∩ ball solid | **3.0 mm³** | 45.7 | 33.5 |
| … board into the **rails** | 3.0 | 38.6 | 32.1 |
| … past the ball's **inner wall** | **0.00** | 7.1 | 1.4 |
| camera past the inner wall at all | **0.00** | 7.1 | 20.5 |
| vs axle / post / nest | 0.00 | 0.00 | 0.00 |

What is left is 3.0 mm³ of board into the rails, and it is the same model bug as before,
now trivial: the groove is cut over `H ± 19.5` and the board reaches −19.6. **It is over by
0.1 mm** — inside the photo's own error bar, so it may not be real at all.

**The ball is untouched**, as asked. Nothing above needs it changed any more.

## What is still owed

1. **Board width and height with the caliper.** Everything scales off one photo-derived
   number. 36.2 × 36.0 is the claim; ±0.5 is the error bar, and the one remaining
   interference is 0.1 mm.
2. Hole Ø — 2.0 is read off the photo, not measured.
3. How high the IR-CUT holder stands off the board.
4. The IR LED pods, if they are to be modelled.
5. Which way the board is clocked in the head, which decides where the ribbon has to turn
   and which side the light sensor overhangs.
