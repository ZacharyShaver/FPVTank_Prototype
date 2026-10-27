# A pass must outlast the slowest fall

2026-10-27, the hill gauges (`gauges/hills.py`).

**What happened.** The first hill gauge passed a try once the robot had driven 300 mm along the slope still on its
wheels. T3 read 45° down, and that went to Zach. Its static tip angle is 42°. A trace at 45° showed it reaching the
300 mm mark at 1.3° of tilt with its uphill wheels already off: it was going over, too slowly to finish in time. The
hill went to 800 mm, and T3 read 40°. Then the hills run searched on the descent, and its finalists sat 0.3-0.9° past
their tip angles: at the 800 mm mark they were mid-topple at 5-20° of tilt (under the 30° the gauge allows), and they
went over by 1-1.9 m. 90 of the 712 screened designs read above their static tip angle.

**Why.** Just past its tip angle, the overturning lever is a few millimetres and a top-heavy body is slow to rotate.
The time to fall grows without limit near the tip angle, so any window lets something through, and a search on the
gauge walks straight into that gap.

**What didn't work.** A stop and a 1 s hold on the slope failed every design from 35°, the box too: at a set speed of
0 the wheels back-drive and creep. It read the speed loop, not the design.

**What holds now.** At constant speed, with the tail stowed, the static tip angle is the exact limit (the tyres'
forces act through the pivot). So the hill is 2.5 m, and `static_check` lists any stowed reading above its static
angle: none may. On the 800 mm readings it lists 90, its control.

**Rule.** Before trusting a "survived the run" verdict, trace a case just past the limit and check it has finished
failing by the end of the window. Where an exact bound exists, check every reading against it, above all before a
search optimises the reading.
