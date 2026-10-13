"""Build the "Scorpion Body Options" page from variants.py's renders and numbers (chassis-v2/out/variants.html)."""
import os, json, base64, io
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')

def jpg(name, w=1300, crop=(0.10, 0.12, 0.90, 0.93)):
    im = Image.open(os.path.join(OUT, name)).convert('RGB'); W, H = im.size
    im = im.crop((int(crop[0] * W), int(crop[1] * H), int(crop[2] * W), int(crop[3] * H)))        # less empty floor
    im = im.resize((w, int(im.size[1] * w / im.size[0])), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, 'JPEG', quality=82, optimize=True); return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()

R = {r['name']: r for r in json.load(open(os.path.join(OUT, 'variants.json')))}
ORDER = ['Baseline', 'Scout', 'Crawler', 'Workhorse']
ROWS = [  # label, key/func, unit, better ('hi' | 'lo' | None), decimals
    ('Length x width', lambda r: '%d x %d' % (r['L'], r['W']), 'mm', None),
    ('Height to the top', lambda r: r['H'], 'mm', None),
    ('Lens height', lambda r: r['lens'], 'mm', None),
    ('Ground clearance', lambda r: r['clearance'], 'mm', 'hi'),
    ('Approach angle', lambda r: r['approach'], '°', 'hi'),
    ('Departure angle', lambda r: r['departure'], '°', 'hi'),
    ('Mass (estimate)', lambda r: r['mass'], 'g', 'lo'),
    ('Centre of mass height', lambda r: r['cog'][1], 'mm', 'lo'),
    ('Tips over sideways at', lambda r: r['tip_side'], '°', 'hi'),
    ('Tips over forward at', lambda r: r['tip_front'], '°', 'hi'),
    ('Tips over backward at', lambda r: r['tip_back'], '°', 'hi'),
    ('Room inside', lambda r: r['inside_L'], 'L', 'hi'),
    ('Printed plastic', lambda r: r['printed_g'], 'g', 'lo'),
    ('Print time (rough)', lambda r: r['print_h'], 'h', 'lo'),
]

def table():
    head = '<tr><th scope="col"></th>' + ''.join('<th scope="col">%s</th>' % n for n in ORDER) + '</tr>'
    rows = []
    for lab, f, unit, better in ROWS:
        vals = [f(R[n]) for n in ORDER]
        if better:
            nd = 1 if unit == 'L' else 0
            nums = [round(float(v), nd) for v in vals]; best = max(nums) if better == 'hi' else min(nums)
        cells = []
        for v in vals:
            txt = v if isinstance(v, str) else ('%.1f' % v if unit == 'L' else '%.0f' % v)
            cls = ' class="best"' if better and round(float(v), nd) == best else ''
            cells.append('<td%s>%s<span class="u">%s</span></td>' % (cls, txt, unit))
        rows.append('<tr><th scope="row">%s</th>%s</tr>' % (lab, ''.join(cells)))
    return '<table><thead>%s</thead><tbody>%s</tbody></table>' % (head, ''.join(rows))

def card(name, tag, built_for, moves, gains, costs, img_front, img_side, accent):
    li = lambda xs: ''.join('<li>%s</li>' % x for x in xs)
    return f'''<article class="opt" style="--hue:{accent}" aria-labelledby="h-{name}">
  <figure class="hero"><img src="{img_front}" alt="{name}, three-quarter front view"></figure>
  <div class="body">
    <p class="tag">{tag}</p>
    <h2 id="h-{name}">{name}</h2>
    <p class="for">{built_for}</p>
    <div class="cols">
      <div><h3>What changes</h3><ul>{li(moves)}</ul></div>
      <div><h3>Gains</h3><ul class="plus">{li(gains)}</ul><h3>Costs</h3><ul class="minus">{li(costs)}</ul></div>
    </div>
    <figure class="side"><img src="{img_side}" alt="{name}, side view" loading="lazy"></figure>
  </div>
</article>'''

b, s, c, w = (R[n] for n in ORDER)
cards = [
    card('Scout', 'Low · sleek · quick to print', 'Indoor runs, fitting under furniture, and the fastest first print.',
         ['One flat deck at the height of the head\'s well: only the ball sticks up.',
          'No raised hull: the Pi, the PCA9685 and the power parts move into the August brief\'s low tail bay, which ends in an antenna stub.',
          'Small, light tracks: 22 mm sprockets, 5 road wheels, skirts over the top run.',
          'Claws kept, lowered, for lights and range sensors.'],
         [f'Centre of mass {s["cog"][1]:.0f} mm off the ground, against {b["cog"][1]:.0f}: it tips sideways only past {s["tip_side"]:.0f}°.',
          f'{s["H"]:.0f} mm tall, against {b["H"]:.0f} with the arm.',
          f'{s["printed_g"]:.0f} g of plastic, about {s["print_h"]:.0f} h: {100 * (1 - s["printed_g"] / b["printed_g"]):.0f}% less than the baseline.'],
         [f'Ground clearance {s["clearance"]:.0f} mm, approach {s["approach"]:.0f}°, departure {s["departure"]:.0f}°: the low tracks set those. Floors and carpets only.',
          f'Least room inside ({s["inside_L"]:.1f} L) and nowhere for an arm.',
          f'Longest ({s["L"]:.0f} mm), because the tail bay hangs out the back.'],
         jpg('var_scout_front.png'), jpg('var_scout_side.png', 900), '#5B7A9A'),
    card('Crawler', 'Terrain · survival', 'Outdoors, kerbs and steps, and coming back in one piece.',
         ['Big trapezoid tracks: 30 mm drive sprocket, raised front idler, 64 wide, 5 road wheels on arms.',
          'Front flippers on the idler axle, pincer-tipped: they swing down to climb a step or flip the robot back over (like iRobot\'s PackBot).',
          'Sloped armour, a skid plate under the belly, hooded louvres.',
          'A roll hoop behind the head guards the ball if it rolls over, and doubles as the carry handle.'],
         [f'Ground clearance {c["clearance"]:.0f} mm, approach {c["approach"]:.0f}° (flippers raised), departure {c["departure"]:.0f}°: the best of the four.',
          'The ball survives a roll-over.',
          f'Same room inside as the baseline ({c["inside_L"]:.1f} L).'],
         [f'Widest by far ({c["W"]:.0f} mm across the flippers) and heaviest ({c["mass"]:.0f} g).',
          f'Most plastic: {c["printed_g"]:.0f} g, about {c["print_h"]:.0f} h.',
          'Two more drives for the flippers, each a standard servo or a geared motor.'],
         jpg('var_crawler_front.png'), jpg('var_crawler_side.png', 900), '#B08A4A'),
    card('Workhorse', 'The arm · payload', 'Picking things up, carrying them, working around the robot.',
         ['The long two-joint arm (option B, 110 + 290) moves to mid-ship, over the centre of mass.',
          'It reaches the ground in front, beside and behind the robot. Here it reaches in front of the left track, passing beside the head.',
          'A cargo bed with tie-down slots and rails behind the arm; the packs sit aft as counterweight.',
          'Brain access moves under the arm\'s pedestal and to side panels.'],
         [f'The arm reaches the ground in front of the robot; the baseline\'s rear-mounted arm only reaches over it.',
          f'Lower centre of mass than the baseline ({w["cog"][1]:.0f} vs {b["cog"][1]:.0f} mm), even reaching out with 100 g, and steadier backward ({w["tip_back"]:.0f}° vs {b["tip_back"]:.0f}°).',
          'Same hull as the baseline: almost no new design.'],
         ['The arm swings over the head: software has to keep the forearm high near the ball, the same kind of rule as the turret\'s tilt/pan rule.',
          'A 400 mm arm wobbles at the tip; the pushrod pins need bearings.',
          'No tail: the arm is the scorpion part.'],
         jpg('var_workhorse_front.png'), jpg('var_workhorse_side.png', 900), '#6E8A62'),
]

html = f'''<meta charset="utf-8">
<title>Scorpion Body Options</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: three option spreads (render left, notes right; stacked on phones), then one comparison table. Same tokens as the
   project's other pages. */
:root{{--bg:#EEF0EC;--panel:#FFFFFF;--ink:#1C211E;--muted:#5E6862;--line:#D4D9D3;--accent:#D9622B;--good:#2F7A5A;--good-bg:#E3F1EA;--bad:#B8332A;--sans:"Barlow",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,monospace}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{color-scheme:dark;--bg:#151917;--panel:#1D2320;--ink:#E4E9E5;--muted:#9AA59E;--line:#313934;--accent:#E8804A;--good:#6CC49B;--good-bg:#1F3129;--bad:#E8756A}}}}
:root[data-theme="dark"]{{color-scheme:dark;--bg:#151917;--panel:#1D2320;--ink:#E4E9E5;--muted:#9AA59E;--line:#313934;--accent:#E8804A;--good:#6CC49B;--good-bg:#1F3129;--bad:#E8756A}}
body{{background:var(--bg);color:var(--ink);font:15.5px/1.55 var(--sans);padding-inline:16px;padding-block:22px 40px}}
.wrap{{max-width:1240px;margin:0 auto;display:grid;gap:22px}}
h1{{font-size:clamp(24px,3.2vw,34px);font-weight:700;margin:0;letter-spacing:.005em;text-wrap:balance}}
.sub{{color:var(--muted);margin:4px 0 0;max-width:80ch}}
.opt{{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden;border-top:4px solid var(--hue)}}
@media (max-width:900px){{.opt{{grid-template-columns:1fr}}}}
.hero{{margin:0;background:#F3F3F1;display:flex;align-items:center}}
.hero img,.side img{{display:block;width:100%;height:auto}}
.body{{padding:18px 20px;display:grid;gap:10px;align-content:start;min-width:0}}
.tag{{margin:0;font:500 12px var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--hue)}}
h2{{margin:0;font-size:26px;font-weight:700}}
.for{{margin:0;font-weight:500}}
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
@media (max-width:560px){{.cols{{grid-template-columns:1fr}}}}
h3{{margin:4px 0 4px;font-size:12px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}}
ul{{margin:0;padding-left:18px;display:grid;gap:5px;font-size:14.5px}}
ul.plus li::marker{{content:"+  ";color:var(--good);font-weight:700}}
ul.minus li::marker{{content:"−  ";color:var(--bad);font-weight:700}}
.side{{margin:4px 0 0;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#F3F3F1}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px}}
.card h2{{font-size:20px;margin-bottom:8px}}
.tw{{overflow-x:auto}}
table{{border-collapse:collapse;width:100%;min-width:640px;font-size:14px}}
th,td{{padding:7px 10px;border-top:1px solid var(--line);text-align:right;font-variant-numeric:tabular-nums}}
thead th{{border-top:0;font-weight:600}}
tbody th{{text-align:left;font-weight:500;color:var(--muted)}}
td{{font-family:var(--mono);font-size:13px}}
td .u{{color:var(--muted);margin-left:3px;font-size:11.5px}}
td.best{{background:var(--good-bg);color:var(--good);font-weight:500}}
.note{{color:var(--muted);font-size:13.5px;margin:10px 0 0;max-width:95ch}}
.base{{display:grid;grid-template-columns:minmax(0,320px) minmax(0,1fr);gap:16px;align-items:center}}
@media (max-width:700px){{.base{{grid-template-columns:1fr}}}}
.base img{{width:100%;border-radius:8px;border:1px solid var(--line);display:block}}
.pick p{{margin:0 0 8px;max-width:85ch}}
</style>
<div class="wrap">
  <header>
    <h1>Scorpion: three bodies, three jobs</h1>
    <p class="sub">The same robot inside every one: head v2, the Pi with the Hailo, the PCA9685, both packs, the ESCs and the power parts. Each body is pushed toward one goal, rendered and measured the same way, against the redesign you liked (bottom). A brainstorm: nothing here is fit-checked yet.</p>
  </header>
  {cards[0]}
  {cards[1]}
  {cards[2]}
  <section class="card" aria-labelledby="h-cmp">
    <h2 id="h-cmp">Side by side</h2>
    <div class="tw">{table()}</div>
    <p class="note">Green is the best in each row. Masses are guesses: packs 300 g each, motors 170, head 210, Pi stack 95, ESCs 55 each; printed parts are their volume × PLA × fill, the tracks TPU. Tip angles are static (a slope it would roll over on, standing still), with the Workhorse's arm reaching out holding 100 g. Approach and departure leave the arm out (it can move); the Crawler's include its raised flippers. Print time assumes about 25 g an hour.</p>
  </section>
  <section class="card" aria-labelledby="h-base">
    <h2 id="h-base">The baseline</h2>
    <div class="base"><img src="{jpg('ideal_arm2_reach_front.png', 700)}" alt="The current redesign with the arm on the rear deck" loading="lazy">
      <p style="margin:0">The hull redesign with the ideal tracks and the two-joint arm on the rear deck. Its arm can reach over the head but not down in front; everything else is the middle of the pack.</p></div>
  </section>
  <section class="card pick" aria-labelledby="h-pick">
    <h2 id="h-pick">If I had to pick</h2>
    <p><b>The Workhorse, with the Crawler's roll hoop.</b> It's the baseline hull with the arm where it can actually work, and it comes out steadier, not worse. The ball is the most expensive thing on the robot to break; the hoop costs one bent tube.</p>
    <p><b>Steal from the Scout for the first print:</b> its flat deck and low tail bay are the cheapest way to get the electronics, the packs and the head into one body and driving.</p>
    <p><b>The Crawler's flippers</b> are the only option that climbs a stair. Worth it only if stairs or self-righting become goals.</p>
  </section>
</div>
'''
p = os.path.join(OUT, 'variants.html'); open(p, 'w', encoding='utf-8').write(html); print('wrote', p, '%.1f MB' % (os.path.getsize(p) / 1e6))
