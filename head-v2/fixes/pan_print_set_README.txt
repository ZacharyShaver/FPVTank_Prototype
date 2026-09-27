PAN COIL TEST PRINT, SET 2 -- 2026-09-27
The 360-degree pan base under the v2 head, and the cradle that bolts onto it.
Still a first test: this print is for finding what doesn't fit.

WHY SET 2
  Set 1 couldn't be put together. The small gear was moulded onto the bottom of the drum (22.6 mm
  across) and had to pass through the well's 10.5 mm hole and the gear bay's 17.2 mm top hole. The
  gear bay was also a closed box, so the big gear couldn't get in either. What changed:
    - the small gear is its own part, pushed onto the drum's shaft from below, one M3 screw;
    - the well and the gear bay are ONE part now (base.stl): there was nowhere on the well to screw
      the bay to;
    - the gear bay's floor is a separate plate (floor.stl), so both gears go in from underneath.
  Set 1's files are in "superseded - set 1, can't assemble/". Don't print from there.

  Fixed in the same pass, before printing (all three also sat in set 1):
    - the gears were drawn touching on both sides of every tooth: zero play, so they'd have jammed.
      The small gear is now 0.3 mm smaller all round (about 1.9 degrees of play at the head as
      drawn; expect less once printed). Your set 1 input gear still meshes with it;
    - the bearing's inner ring (it turns with the drum) sat flat on the fixed ledge and would have
      dragged. The ledge now has a 0.4 mm deep recess under the inner ring, so only the outer ring
      sits on it;
    - the bearing fits were drawn at exactly 58 and 45 mm. Now the seat is 58.1 and the drum's hub
      44.9, the same as the tilt bearings' seats. The rounded corner where the bearing seats against
      the drum's top disc is now a sharp step, so the bearing sits flat against it.

PRINT (plate_pan_coil_set2.3mf has these four, each already turned the way it prints)
  base.stl         the well and gear bay in one piece. Needs supports.
  drum.stl         no gear on it now; its shaft ends in a D-shaped stub (a round stub with one
                   flat side, so the gear can't spin on it).
  floor.stl        the gear bay's bottom plate.
  small_gear.stl   the drum's gear. D-shaped hole; the thin bottom web goes on the bed.
  pan_coil_plate.png is the plate; pan_coil_assembly.png shows every part pulled apart the way it
  goes in.

UNCHANGED FROM SET 1 (keep what you printed)
  cradle.stl, input_gear.stl (copies are here too)

BUY / HAVE
  1 x 6809 bearing (45 x 58 x 7)           on the drum, sits on the base's ledge
  1 x MG90D servo (180 degree)              drives the input gear, 2:1 step-up = 360 degrees at the head
  3 x M3 x 12 socket head                   cradle onto the drum, from above, BEFORE the ball goes in
  1 x M3 x 8 button head (NEW)              small gear onto the drum, from below. Low head: a socket
                                            head would stick 1 mm out under the base
  4 x M2 x 6 (NEW)                          floor plate onto the gear bay, from below
  2 x M2 x 6                                the servo's tabs
  1 x M2 horn screw, ~8 mm                  stock horn screws are likely too short (1.5 mm roof)
  2 x 6704 bearing (20 x 27 x 4)            the head's tilt collars, as before

ASSEMBLY ORDER (checked: each part slides in along this path without hitting anything)
  1. Servo into the base through the side window, shaft pointing down. Two M2 x 6 through its tabs.
  2. Push the 6809 bearing onto the drum from below, up to the wide disc at the top.
  3. Drop the drum into the base from above. Its shaft comes out the bottom of the gear bay.
  4. Put the horn in the input gear's pocket. Push the gear up from below until the horn slides onto
     the servo's shaft. Drive the horn screw up from underneath.
  5. Small gear up onto the drum's D-shaped stub. Turn the drum until the flats line up; wiggle it
     so its teeth slide in between the big gear's teeth. M3 x 8 button head up the middle.
  6. Floor plate on, 4 x M2 x 6.
  7. Ribbon, then the cradle, as before (below).

HOW THE RIBBON GOES (decided 2026-09-27, unchanged)
  Down the cradle's groove, straight down the middle of the drum's 18 mm hole, then ONE soft 45-degree
  fold at the drum's side slot turns it on edge to wrap the drum. Make that fold by hand with the drum
  out, where you can see it; nothing gets threaded after it's folded. No twist anywhere.
  Keep the connector ends straight. No folds in the tilt loop behind the ball or in the coil.

CLOCKING: bolt the cradle on with the drum's side slot facing FORWARD (the camera side). The three bolt
  holes let it go on three ways round; only that one lines the slot up with the ribbon.

STILL GUESSES -- check on this print
  - The input gear's horn pocket is a placeholder size. Re-cut it in Fusion with your real horn model
    (zero offset, 1-2 mm roof), the way you did the others. When you do: the servo's shaft must end
    inside the horn. The placeholder pocket is 0.8 mm shallower than the shaft stand-in the checks use.
  - The small gear's D-hole is 0.15 mm looser than the stub all round (the slide rule). If it's
    sloppy or won't go on, say which.
  - Gear play: 0.3 mm off the small gear is a guess at how fat your printer makes gears. If they
    bind, or the head wobbles more than you like, say which.
  - Bearing: if the 6809 won't press into the base or onto the drum, or falls out, say which.
  - Ribbon thickness 0.2 is assumed. The groove's tightest bend is 6.3 mm radius, safe even at 0.3.
  - Where the base screws down to the tank body is still open. Nothing on this plate fixes that yet.

WHAT TO LOOK FOR
  - Assembly: does each step above go the way it says?
  - Gear pair: servo holding still, how much the drum rocks by hand (backlash; ~1 degree expected).
  - Drum turning on the bearing: smooth over the whole travel, no rubbing.
  - Ribbon: roll the drum to both ends of travel and look at the loop. Test with a SPARE ribbon first.
  - Cradle on the drum: the 3 bolts reach and pull it down flat; the ribbon drops through clean.

Rebuild: head-v2/fixes/pan_print_set.py (its docstring lists the generator steps to run first).
Checks: head-v2/generator/generators/pan_coil_b_check.py (and --broken, the negative control).
3D fit view, set 2 (Pull apart shows the assembly): https://claude.ai/artifact/NKDFgbD3YuAp3xg7JZudVj
  Rebuild: head-v2/fixes/fit_view.py
