"""The scorecard as one static page for the public Scorpion gallery (2026-10-28): the "Scorpion Gauges" page's own
markup and script (dashboard.html), its four row files inlined, and a small stand-in for the dashboard's runtime (the
data, the computed values, the theme's colours and spacing). Zach: "having gauges is fine too actually throw both in".

    python gauges/export.py && python gauges/scorecard_page.py   -> gauges/out/dash/scorecard.html
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config

DASH = os.path.join(config.GAUGES_OUT, 'dash')
# The dashboard's theme tokens, light then dark. Series colours: the dataviz skill's reference categorical order.
LIGHT = dict(bg='#f7f7f5', panel='#ffffff', fg='#1a1a19', muted='#5c5b56', line='#dddcd6', ok='#1a7f45', warn='#a86b00', bad='#c23a3a',
             grid='#ecebe6', axis='#b9b8b1', cmuted='#b9b8b1', ref='#7a7972', pop='#ffffff', shadow='0 4px 14px rgba(0,0,0,.12)',
             series=('#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948'))
DARK = dict(bg='#141413', panel='#1d1d1c', fg='#f0efec', muted='#a9a8a0', line='#33332f', ok='#4cc184', warn='#e2a73a', bad='#ee6b6b',
            grid='#262624', axis='#4a4a45', cmuted='#4a4a45', ref='#8c8b84', pop='#262624', shadow='0 4px 14px rgba(0,0,0,.5)',
            series=('#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767'))


def tokens(t):
    s = (f"--color-bg:{t['bg']};--color-panel:{t['panel']};--color-fg:{t['fg']};--color-fg-muted:{t['muted']};"
         f"--color-border-line:{t['line']};--color-ok:{t['ok']};--color-warn:{t['warn']};--color-bad:{t['bad']};"
         f"--cds-chart-grid:{t['grid']};--cds-chart-axis:{t['axis']};--cds-chart-muted:{t['cmuted']};--cds-chart-reference:{t['ref']};"
         f"--cds-surface-popover:{t['pop']};--cds-border:{t['line']};--cds-shadow-popover:{t['shadow']};--cds-text-secondary:{t['muted']};")
    return s + ''.join(f'--s{i + 1}:{c};' for i, c in enumerate(t['series']))


CSS = """:root{%s
  --font-anthropic-sans:"Source Sans 3",system-ui,-apple-system,"Segoe UI",sans-serif;--font-anthropic-serif:"Source Serif 4",Georgia,serif;
  --cds-gap-xs:4px;--cds-gap-sm:8px;--cds-gap-md:16px;--cds-gap-xl:40px;--cds-pad-xs:4px;--cds-pad-sm:8px;--cds-pad-lg:20px;
  --cds-radius:8px;--cds-font-size-title:2rem;--cds-font-size-heading:1.1rem;--cds-font-size-body:0.95rem;--cds-font-size-caption:0.8rem;
  --cds-font-weight-medium:600;--cds-dur-slow:.3s;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){%s color-scheme:dark}}
:root[data-theme="dark"]{%s color-scheme:dark}
body{margin:0;background:var(--color-bg);color:var(--color-fg);font:16px/1.5 var(--font-anthropic-sans)}
#dash-root{max-width:1180px;margin:0 auto;padding-block:28px 72px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.dash-skeleton{color:var(--color-fg-muted)}
.sg-src{font-size:var(--cds-font-size-caption);color:var(--color-fg-muted);max-width:72ch;margin:0}
"""

SHIM = """// A stand-in for the dashboard's runtime: its data calls, computed values and colours, for a static copy of the page.
(() => {
  const DATA = %s, calcs = {}, subs = [];
  const rowsOf = (id) => (id in DATA ? DATA[id] : id in calcs ? value(id) : []);
  function value(id) { const c = calcs[id]; if (!('v' in c)) c.v = c.fn(...c.inputs.map(rowsOf)); return c.v; }
  window.dash = {
    colors: [1, 2, 3, 4, 5, 6, 7, 8].map((i) => 'var(--s' + i + ')'),
    data(id) {
      if (id in DATA) return {status: 'ok', data: DATA[id], columns: Object.keys(DATA[id][0] || {}), meta: [], refreshing: false};
      if (id in calcs) return {status: 'ok', data: value(id), meta: [], refreshing: false};
      return {status: 'missing', data: [], meta: [], refreshing: false};
    },
    calc(id, o) { calcs[id] = o; },
    onData(fn) { subs.push(fn); fn(); },
    params: () => ({}), setParams() {}, resetParams() {}, setLink() {}, refresh() {},
  };
  let w = innerWidth, t = 0;
  addEventListener('resize', () => { if (innerWidth === w) return; w = innerWidth; clearTimeout(t); t = setTimeout(() => subs.forEach((f) => f()), 150); });
})();
"""


def main():
    rows = {n: json.load(open(os.path.join(DASH, f'{n}.json'))) for n in ('designs', 'physics', 'climb', 'checks')}
    page = open(os.path.join(HERE, 'dashboard.html'), encoding='utf-8').read()
    src = ('<p class="sg-src">A static copy of the Scorpion Gauges scorecard, built from the repo\'s gauges/ (export.py, '
           'scorecard_page.py). Every number is a MuJoCo reading; the sim has not been checked against the real robot except '
           'for falls of printed bodies.</p>')
    page = page.replace('<p class="sg-take" id="takeaway">', src + '\n    <p class="sg-take" id="takeaway">', 1)
    html = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n<title>Scorpion Gauges</title>\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600&family=Source+Serif+4:wght@400&display=swap">\n'
            f'<style>{CSS % (tokens(LIGHT), tokens(DARK), tokens(DARK))}</style>\n'
            '<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>\n'
            f'<script>{SHIM % json.dumps(rows, separators=(",", ":"))}</script>\n</head>\n<body>\n'
            f'<div id="dash-root">\n{page}\n</div>\n</body>\n</html>\n')
    out = os.path.join(DASH, 'scorecard.html'); open(out, 'w', encoding='utf-8').write(html)
    print(out, f'{len(html.encode()) / 1024:.0f} kB')


if __name__ == '__main__':
    main()
