"""The gauge films page: every gauge's clips on the top designs (test_films.py's films.json), a section a gauge, each with
what the gauge does and what to look for, for judging the gauges themselves.

    python gauges/test_films_page.py   -> gauges/out/test_films/index.html (the gallery's "gauge-films" page)
"""
import os, sys, json, html
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import test_films as TF

TESTS = {   # (short name, gauge, what it does, what to look for)
    'up': ('Upright', 'G1',
           'Dropped from 300 mm in a random orientation with a random spin, wheels unpowered. A design with a tail then gets 10 s of '
           'scripted righting moves. The reading is the share of 200 falls that end on the wheels, at three floor grips, the worst counting. '
           'Left: a fall that ends upright. Right: one that stays down.',
           'Do the bounces and tumbles look like a real 300 mm drop? Could a real tail servo push this hard, this fast (6 rad/s, the '
           'tail torque knob)? A fall counts only by its final pose, so a slow, ugly righting scores the same as a clean one.'),
    'climb': ('Step', 'G2',
              'Drives at a step 0.5 m/s, square on within 10 degrees, for 4 s. A pass is on top and on its wheels. A tail pushes down when '
              'the robot stalls nose up, or kicks when it stalls level. 20 tries a rung, nose first and tail first, the better counting. The '
              'reading is the height where the pass rate, smoothed so it never rises with height, falls to 90 %. '
              'Left: the tallest rung below the reading. Right: the next rung up.',
              'Is it climbing, or is the tail throwing it up the step? A real servo stalls under load. Does the failure look like the real one '
              '(nose caught on the lip, or flipping over backwards)? The step edge is rounded and the floor never gives.'),
    'turn': ('Turn', 'G3',
             'Spins in place: left wheels back, right wheels forward, both at 60 % of no-load speed, until it has turned 180 degrees '
             '(6 s at most). The reading is the diameter of the circle round the starting point that holds everything the body swept. '
             'Smaller is better. Dashed ring: the final reading. Solid ring: the sweep so far. Left: from above. Right: the same run, three-quarter view.',
             'A spin that drifts reads bigger than its footprint, since the circle stays round the start. The sim\'s skid-steer slip '
             '(chi about 1.5 to 1.8) is close to published tank and rover measurements (about 1.5), but the wheels here are rigid.'),
    'h_up': ('Hill up', 'G4',
             'Drives 2.5 m up a slope at 0.5 m/s. The floor stays flat and gravity tilts, so these frames are turned to match. Grip is x2.5 '
             'so the robot tips before it slides: this gauge reads the tip limit, not traction. A pass gets there under 30 degrees off the '
             'slope. 5 degree rungs; a tail may hold a braced pose. Left: the reading. Right: 5 degrees steeper.',
             'Real floors and tyres slide well before x2.5 grip, so a real hill limit will be lower. Does the failure look like going over '
             'backwards (the real danger), or a stall?'),
    'h_down': ('Hill down', 'G5',
               'As the hill up, driving down. It also fails if it slides: the body running ahead of its wheels for 0.2 s, or faster than '
               'twice the set speed. Left: the reading. Right: 5 degrees steeper.',
               'Going over nose first is the failure this guards against. Is the braced tail actually doing anything?'),
    'crest': ('Crest', 'G6',
              'Crawls at 0.15 m/s over a ridge: two planks meeting at a rounded peak 150 mm high, each at the rung\'s angle. A pass is '
              'over and on its wheels. Fails: stuck, stuck with its belly on the ridge, or tipped. 5 degree rungs. Left: the reading. '
              'Right: 5 degrees steeper.',
              'Belly clearance and wheelbase decide this one. Is the failure a hang-up on the peak, or a tip on the way down?'),
    'push': ('Push', 'G7 (realistic run)',
             'Pushes a 200 x 260 x 150 mm box of the rung\'s mass 0.5 m at 0.3 m/s within 6 s, holding its heading. Fails: stalled, tipped, '
             'or rode up (its front 40 mm up onto the box). Mass rungs 0.5 to 12 kg, the worst grip counting. Left: the reading. Right: the next rung.',
             'This is the gauge that fought the step: a curved, climbing nose rides up the box. Zach\'s call (2026-11-02) replaces it with the tow.'),
    'tow': ('Tow', 'G7 (new)',
            'Drags a 300 x 300 x 60 mm sled of the rung\'s mass 0.5 m at 0.3 m/s within 8 s, on a 250 mm rope from a hitch on the body\'s '
            'rear at axle height. Fails: stalled, or tipped past 45 degrees (a wheelie onto its back). Not in the realistic run: '
            'its reading here is quick, 6 tries a rung at x1 grip. Left: the reading. Right: the next rung.',
            'Does the pull lift the nose? A real hitch, rope and sled on carpet or concrete will differ: the sled\'s friction scales with '
            'the floor\'s here. Today\'s sweep reads it properly.'),
    'rough': ('Rough', 'G8 (new)',
              'Drives 2 m across a field of rounded rocks at 0.4 m/s, holding its heading, within 12 s. Each rung raises the same rocks '
              'taller (10 to 150 mm), so a taller rung is never easier. Grip x2.5. Fails: stuck (under 20 mm of progress in 3 s) or over. '
              'The reading is the rock height where the pass rate, smoothed so it never rises with height, falls to 90 %. Its reading here '
              'is quick, 6 tries a rung. Left: the tallest rung below the reading. Right: the next rung up.',
              'Belly clearance decides most of it: a robot beaches with a rock under its belly and its wheels spinning. Do the rocks look '
              'like real ground? Real rocks shift and crumble; these never give.'),
}


def clip_line(test, c, side):
    o = c.get('outcome'); found = c.get('found', True)
    if test == 'turn':
        return ''
    if test == 'up':
        s = f"landed {c.get('rest')}, ended {o}"
    elif test == 'climb':
        s = f"{c['h']} mm: {o} (the gauge: {c.get('n')}/20)"
    elif test in ('h_up', 'h_down', 'crest'):
        s = f"{c['deg']}°: {o}"
    elif test == 'rough':
        s = f"{c['mm']} mm rocks: {o}"
    else:
        s = f"{c['kg']:g} kg: {o}"
    if not found:
        s += ' (no ' + ('pass' if side == 0 else 'fail') + ' found in the tries searched)'
    return s


def main():
    F = json.load(open(os.path.join(TF.OUT, 'films.json'), encoding='utf-8'))
    by = {(x['key'], x['test']): x for x in F}
    order = [k for k, _ in TF.DESIGNS]; names = dict(TF.DESIGNS)
    # the overview: each design's readings, a link per clip
    head = ''.join(f'<th><a href="#{t}">{html.escape(TESTS[t][0])}</a><span>{html.escape(TESTS[t][1])}</span></th>' for t in TF.TESTS)
    rows = ''
    for k in order:
        cells = ''
        for t in TF.TESTS:
            x = by.get((k, t))
            v = '–' if x is None or 'err' in x else html.escape(x['reading'].split(' ')[0] if t == 'up' else x['reading'].split(' (')[0])
            cells += f'<td><a href="#{t}-{k.replace(" ", "_")}">{v}</a></td>'
        rows += f'<tr><th>{html.escape(names[k])}</th>{cells}</tr>'
    secs = ''
    for t in TF.TESTS:
        name, g, what, look = TESTS[t]; cards = ''
        for k in order:
            x = by.get((k, t))
            if x is None:
                continue
            anchor = f'{t}-{k.replace(" ", "_")}'
            if 'err' in x:
                cards += f'<figure class="card" id="{anchor}" data-d="{html.escape(k)}"><figcaption><b>{html.escape(names[k])}</b><span class="bad">not filmed: {html.escape(x["err"])}</span></figcaption></figure>'
                continue
            lines = [clip_line(t, c, i) for i, c in enumerate(x['clips'])]
            lines = ''.join(f'<li class="{"warn" if not c.get("found", True) else ""}">{html.escape(("Left: " if i == 0 else "Right: ") + l)}</li>'
                            for i, (l, c) in enumerate(zip(lines, x['clips'])) if l)
            cards += (f'<figure class="card" id="{anchor}" data-d="{html.escape(k)}">'
                      f'<video src="{html.escape(x["src"])}" poster="{html.escape(x["poster"])}" muted loop playsinline preload="none" controls></video>'
                      f'<figcaption><b>{html.escape(names[k])}</b><span class="rd">{html.escape(x["reading"])}</span>'
                      f'{"<ul>" + lines + "</ul>" if lines else ""}</figcaption></figure>')
        secs += (f'<section id="{t}"><h2>{html.escape(name)} <small>{html.escape(g)}</small></h2>'
                 f'<div class="about"><p><b>What it does.</b> {html.escape(what)}</p><p><b>Look for.</b> {html.escape(look)}</p></div>'
                 f'<div class="grid">{cards}</div></section>')
    chips = ''.join(f'<button class="chip on" data-d="{html.escape(k)}">{html.escape(names[k])}</button>' for k in order)
    nav = ''.join(f'<a href="#{t}">{html.escape(TESTS[t][0])}</a>' for t in TF.TESTS)
    page = PAGE.replace('%TABLE%', f'<table><thead><tr><th></th>{head}</tr></thead><tbody>{rows}</tbody></table>') \
               .replace('%SECTIONS%', secs).replace('%CHIPS%', chips).replace('%NAV%', nav)
    p = os.path.join(TF.OUT, 'index.html'); open(p, 'w', encoding='utf-8').write(page); print(p)


PAGE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gauge films</title>
<style>
:root { --bg: #f6f6f3; --card: #ffffff; --ink: #1d2024; --mute: #5d636b; --line: #dcdcd6; --accent: #b4561a; --warn: #9a6a00; --bad: #b3261e; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg: #16181b; --card: #1f2226; --ink: #e6e6e1; --mute: #9aa0a7; --line: #33373c; --accent: #e08a4a; --warn: #e0b13f; --bad: #f2867c; } }
:root[data-theme="dark"] { --bg: #16181b; --card: #1f2226; --ink: #e6e6e1; --mute: #9aa0a7; --line: #33373c; --accent: #e08a4a; --warn: #e0b13f; --bad: #f2867c; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 1320px; margin: 0 auto; padding: 24px 16px 64px; }
h1 { font-size: 28px; margin: 0 0 6px; }
.lede { color: var(--mute); max-width: 860px; margin: 0 0 18px; }
.bar { position: sticky; top: 0; z-index: 5; background: var(--bg); border-bottom: 1px solid var(--line); padding: 8px 0; margin: 0 0 18px; }
.bar nav, .bar .chips, .bar .speed { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.bar nav a { color: var(--ink); text-decoration: none; padding: 3px 9px; border: 1px solid var(--line); border-radius: 14px; font-size: 13px; }
.bar nav a:hover { border-color: var(--accent); }
.bar .row2 { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 6px; align-items: center; }
.chip, .sp { font: inherit; font-size: 12px; padding: 2px 9px; border-radius: 12px; border: 1px solid var(--line); background: transparent; color: var(--mute); cursor: pointer; }
.chip.on, .sp.on { background: var(--accent); border-color: var(--accent); color: #fff; }
.lbl { font-size: 12px; color: var(--mute); }
.tablewrap { overflow-x: auto; margin: 0 0 28px; }
table { border-collapse: collapse; font-size: 13px; min-width: 760px; }
th, td { border-bottom: 1px solid var(--line); padding: 5px 9px; text-align: left; white-space: nowrap; }
thead th { font-weight: 600; vertical-align: bottom; }
thead th span { display: block; font-weight: 400; color: var(--mute); font-size: 11px; }
td a, th a { color: var(--ink); text-decoration: none; }
td a:hover, th a:hover { color: var(--accent); }
section { margin: 0 0 40px; scroll-margin-top: 110px; }
h2 { font-size: 21px; margin: 0 0 8px; }
h2 small { font-weight: 400; color: var(--mute); font-size: 14px; }
.about { max-width: 980px; color: var(--ink); margin: 0 0 14px; }
.about p { margin: 0 0 6px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 600px), 1fr)); gap: 14px; }
.card { margin: 0; background: var(--card); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; scroll-margin-top: 110px; }
.card.off { display: none; }
.card video { display: block; width: 100%; aspect-ratio: 8 / 3; background: #ddd; }
figcaption { padding: 8px 12px 10px; font-size: 13px; }
figcaption b { margin-right: 8px; }
.rd { color: var(--mute); }
figcaption ul { margin: 4px 0 0; padding-left: 18px; }
.warn { color: var(--warn); }
.bad { color: var(--bad); }
.foot { color: var(--mute); font-size: 12px; margin-top: 30px; }
</style>
</head>
<body>
<main>
<h1>Gauge films</h1>
<p class="lede">Every gauge, filmed on the realistic run's top designs, to judge the gauges themselves. Each clip runs the gauge's own
code: the design at its reading on the left, and at the next rung up on the right, at the floor grip that set the reading. A pass
and a fail side by side show what the gauge counts. Real time. Only the look is added (colours, floor, lights). Click a reading to jump to its clip.</p>
<div class="tablewrap">%TABLE%</div>
<div class="bar">
<nav>%NAV%</nav>
<div class="row2"><span class="lbl">Designs</span><div class="chips">%CHIPS%</div>
<span class="lbl">Speed</span><div class="speed"><button class="sp" data-r="0.5">0.5×</button><button class="sp on" data-r="1">1×</button><button class="sp" data-r="2">2×</button></div></div>
</div>
%SECTIONS%
<p class="foot">Designs: the finalists of the realistic capability run (2026-11-01: a buildable body, motors and parts that fit, flippers
mounted), T3 at its real build and the box robot with the same parts. Simulated in MuJoCo; none of these readings has been checked on the
real robot yet. Made by gauges/test_films.py; each clip's rung, try and outcome: <a href="films.json">films.json</a>.</p>
</main>
<script>
(function () {
  var rate = 1;
  var vids = Array.prototype.slice.call(document.querySelectorAll('video'));
  function play(v) { v.playbackRate = rate; var p = v.play(); if (p && p.catch) p.catch(function () {}); }
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) play(e.target); else e.target.pause(); });
    }, { threshold: 0.4 });
    vids.forEach(function (v) { io.observe(v); });
  }
  document.querySelectorAll('.sp').forEach(function (b) {
    b.addEventListener('click', function () {
      rate = parseFloat(b.getAttribute('data-r'));
      document.querySelectorAll('.sp').forEach(function (x) { x.classList.toggle('on', x === b); });
      vids.forEach(function (v) { v.playbackRate = rate; });
    });
  });
  document.querySelectorAll('.chip').forEach(function (b) {
    b.addEventListener('click', function () {
      b.classList.toggle('on'); var d = b.getAttribute('data-d'), on = b.classList.contains('on');
      document.querySelectorAll('.card[data-d="' + d + '"]').forEach(function (c) {
        c.classList.toggle('off', !on); if (!on) { var v = c.querySelector('video'); if (v) v.pause(); }
      });
    });
  });
})();
</script>
</body>
</html>
'''

if __name__ == '__main__':
    main()
