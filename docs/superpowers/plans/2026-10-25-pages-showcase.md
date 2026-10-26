# Scorpion Gallery on GitHub Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A public static site that shows Scorpion's visuals (the interactive 3D design pages, the research figures and the sim video), each with a one-line caption, built from this repo by one command and published from a separate public repo.

**Architecture:** A curated manifest (`tools/gallery/manifest.json`) names each visual, its source on disk, its thumbnail and the command that regenerates it. `tools/gallery/build.py` copies the sources into `site/out/`, gives the artifact-style pages a proper document head and a link back, strips private claude.ai links, makes thumbnails and writes `index.html` from a template. Then it gates the build: every local link resolves, no file is too big, and `tools/leakscan.py --path site/out --strict` (plan `2026-10-25-leak-audit.md`) finds nothing. `tools/gallery/publish.py` pushes `site/out/` to a separate public repo and turns Pages on. This repo stays private and its history never leaves.

**Tech Stack:** Python 3.10 standard library (`json`, `shutil`, `html`, `re`, `unittest`), Pillow 12 (thumbnails), gh 2.95, GitHub Pages (static files, `.nojekyll`), three.js r128 from cdnjs (already used by the pages).

## Global Constraints

- Depends on plan `2026-10-25-leak-audit.md` Tasks 1-3 (`tools/leakscan.py` with `--path` and `--strict`). Don't publish until that plan's Task 5 is done and Task 6 has Zach's decision.
- This repo is PRIVATE and stays private (the leak audit's option A). The site goes to a separate public repo; default name `ZacharyShaver/scorpion-gallery`, Zach's call.
- Creating the public repo, pushing to it and turning on Pages are outward-facing: each runs only with Zach's explicit yes in chat and the `--yes` flag.
- GitHub Pages limits: a published site at most 1 GB, files under 100 MB. Build limits: 95 MB per file, 900 MB in all. The pages today total about 55 MB; `lineup.html` is the largest at 11.1 MB.
- External scripts and fonts only from `cdnjs.cloudflare.com`, `cdn.jsdelivr.net`, `unpkg.com`, `fonts.googleapis.com` and `fonts.gstatic.com`, as the pages already use.
- `site/out/` is build output: covered by `.gitignore`'s `**/out/`; never committed here.
- Captions in plain words, third person, one line each (CLAUDE.md: keep the writing short).

## The inventory (2026-10-25)

Generated pages live in git-ignored `out/` folders; each has the command that rebuilds it:

| Page | Source | Rebuild |
|---|---|---|
| Self-righting shell search | `research/tumble/out/weeble_search.html` | `python research/tumble/view3.py` |
| Chassis Concept, Hull Redesign, Rugged Body, Nose, v2 Legs, Tail Arms, Guard Arm, Guard Arm Flippers, Body Options, Line-up | `chassis-v2/out/{concept,hull,rugged,nose,legs_v2,tail_arms,guard_arm,guard_flippers,variants,lineup}.html` | `python chassis-v2/<script>.py` (`legs_v2` is `SCORPION_LEGS=v2 python chassis-v2/rugged.py`) |
| Trainer, Six-Wheel Trainer, Step Trainer | `chassis-v2/out/{trainer,trainer6,trainerstep}.html` | `python chassis-v2/trainer.py` with `SCORPION_LEGS=wheels` and `SCORPION_WHEELS=4`, `6` or `step` |
| Head v2 fit views (a page plus its mesh files) | `head-v2/out/fit-view/` | `python head-v2/fixes/fit_view.py` |
| Phone tripod adapter | `research/tumble/out/phone_mount_view.html` | `python research/tumble/phone_mount.py` |

Tracked figures: `research/figures/{search3_top_designs,e4_ground,pose3_poses,chassis3_finalists,sim_vs_reality,surrogate_gp,iterations,mutation}.png`, the video `research/figures/sim_drops.mp4`, and `head-v2/generator/concept/ball_head_render_sheet.png`. Thumbnails for the chassis pages: `chassis-v2/out/{concept,hull,rugged,guard,arms,trainer,trainer6,trainerstep}_sheet.png`; the rest get a drawn placeholder card.

Kept off the site unless Zach says otherwise: `research/paper/` (the fellowship application), `reference/` and `chassis-v1/parts/` (third-party files), anything `superseded - …`.

---

### Task 1: The manifest, for Zach to approve

**Files:**
- Create: `tools/gallery/manifest.json`

**Interfaces:**
- Produces: a JSON object `{"title": str, "intro": str, "sections": [{"name": str, "items": [item]}]}`, where an item is `{"id": str, "kind": "page"|"figure"|"video", "title": str, "src": str, "dir": bool (optional, copy src's whole folder), "thumb": str (optional), "make": str, "caption": str}`. Paths are repo-relative with forward slashes; `id` is unique, lowercase, `[a-z0-9-]+`.

- [ ] **Step 1: Write the manifest**

```json
{
  "title": "Scorpion",
  "intro": "Scorpion is a tracked ground robot with a 360-degree pan-tilt camera head, built as a platform for embodied AI. These are the design pages and simulation results from its development: drag the 3D pages to turn them.",
  "sections": [
    {"name": "Self-righting shell", "items": [
      {"id": "weeble-search", "kind": "page", "title": "Self-righting shell search", "src": "research/tumble/out/weeble_search.html", "thumb": "research/figures/search3_top_designs.png", "make": "python research/tumble/view3.py", "caption": "About 145,000 simulated shell shapes; the winners have one place to rest, on their wheels."},
      {"id": "top-designs", "kind": "figure", "title": "The top designs", "src": "research/figures/search3_top_designs.png", "make": "python research/tumble/render3.py", "caption": "The old best against the new family, at one scale, the robot drawn inside."},
      {"id": "e4-ground", "kind": "figure", "title": "E4 on the ground, and as a cage", "src": "research/figures/e4_ground.png", "make": "python research/tumble/fig_e4_ground.py", "caption": "The shell stops 32 mm off the floor; twelve hoops keep the same single rest state."},
      {"id": "sim-drops", "kind": "video", "title": "Simulated drops", "src": "research/figures/sim_drops.mp4", "make": "python research/tumble/render_drops.py", "caption": "Scale bodies dropped in MuJoCo, dead floor against bouncing floor."},
      {"id": "sim-vs-reality", "kind": "figure", "title": "Simulation against real drops", "src": "research/figures/sim_vs_reality.png", "make": "python research/tumble/sim_vs_reality.py", "caption": "Every contact model scored against 541 hand drops of printed bodies."},
      {"id": "surrogate", "kind": "figure", "title": "A surrogate of the shape sweep", "src": "research/figures/surrogate_gp.png", "make": "python research/tumble/surrogate_gp.py", "caption": "A Gaussian process standing in for the simulator, with its uncertainty."}
    ]},
    {"name": "Falls, poses and steps", "items": [
      {"id": "arm-poses", "kind": "figure", "title": "Arm poses through a fall", "src": "research/figures/pose3_poses.png", "make": "python research/tumble/render_pose3.py", "caption": "Where the Trainer lands with its arm held in each pose, 2,000 simulated drops each."},
      {"id": "step-chassis", "kind": "figure", "title": "Chassis search for steps", "src": "research/figures/chassis3_finalists.png", "make": "python research/tumble/render_chassis3.py", "caption": "Wheel size, axles and belly height searched for driving down steps, under length caps."},
      {"id": "trainerstep", "kind": "page", "title": "Step Trainer", "src": "chassis-v2/out/trainerstep.html", "thumb": "chassis-v2/out/trainerstep_sheet.png", "make": "SCORPION_LEGS=wheels SCORPION_WHEELS=step python chassis-v2/trainer.py", "caption": "The search's step layout built: smaller wheels closer together, the belly 54 mm up on drop-plate pods."}
    ]},
    {"name": "Chassis designs (3D)", "items": [
      {"id": "lineup", "kind": "page", "title": "Chassis line-up", "src": "chassis-v2/out/lineup.html", "make": "python chassis-v2/lineup.py", "caption": "Every chassis variation side by side (11 MB)."},
      {"id": "concept", "kind": "page", "title": "Chassis concept", "src": "chassis-v2/out/concept.html", "thumb": "chassis-v2/out/concept_sheet.png", "make": "python chassis-v2/concept.py", "caption": "The first body around the head, the packs and the power bay."},
      {"id": "hull", "kind": "page", "title": "Hull redesign", "src": "chassis-v2/out/hull.html", "thumb": "chassis-v2/out/hull_sheet.png", "make": "python chassis-v2/hull.py", "caption": "The head moved into the nose, a carapace behind it."},
      {"id": "rugged", "kind": "page", "title": "Rugged body", "src": "chassis-v2/out/rugged.html", "thumb": "chassis-v2/out/rugged_sheet.png", "make": "python chassis-v2/rugged.py", "caption": "Skirts and hoops shaped so it rights itself after a roll."},
      {"id": "legs-v2", "kind": "page", "title": "v2 legs", "src": "chassis-v2/out/legs_v2.html", "thumb": "chassis-v2/out/rugged_v2_sheet.png", "make": "SCORPION_LEGS=v2 python chassis-v2/rugged.py", "caption": "Longer tracks on sprung road wheels."},
      {"id": "tail-arms", "kind": "page", "title": "Tail arms", "src": "chassis-v2/out/tail_arms.html", "thumb": "chassis-v2/out/arms_sheet.png", "make": "python chassis-v2/tail_arms.py", "caption": "Four arm designs out of the tail, every pose checked."},
      {"id": "guard-arm", "kind": "page", "title": "Guard arm", "src": "chassis-v2/out/guard_arm.html", "thumb": "chassis-v2/out/guard_sheet.png", "make": "python chassis-v2/guard_arm.py", "caption": "An arm that stows as an arch over the head and pushes the robot upright."},
      {"id": "guard-flippers", "kind": "page", "title": "Guard arm with flippers", "src": "chassis-v2/out/guard_flippers.html", "make": "python chassis-v2/guard_flippers.py", "caption": "The guard arm with front flippers on the idlers."},
      {"id": "trainer", "kind": "page", "title": "Trainer", "src": "chassis-v2/out/trainer.html", "thumb": "chassis-v2/out/trainer_sheet.png", "make": "SCORPION_LEGS=wheels python chassis-v2/trainer.py", "caption": "Four wheels instead of tracks, for training many robots at once."},
      {"id": "trainer6", "kind": "page", "title": "Six-wheel Trainer", "src": "chassis-v2/out/trainer6.html", "thumb": "chassis-v2/out/trainer6_sheet.png", "make": "SCORPION_LEGS=wheels SCORPION_WHEELS=6 python chassis-v2/trainer.py", "caption": "The same module six times."},
      {"id": "nose", "kind": "page", "title": "Nose section", "src": "chassis-v2/out/nose.html", "make": "python chassis-v2/nose.py", "caption": "The head's bench-stand pocket built into the nose floor."},
      {"id": "variants", "kind": "page", "title": "Body options", "src": "chassis-v2/out/variants.html", "make": "python chassis-v2/variants_page.py", "caption": "Scout, Crawler and Workhorse against the baseline."}
    ]},
    {"name": "Camera head", "items": [
      {"id": "head-fit", "kind": "page", "title": "Head v2 fit view", "src": "head-v2/out/fit-view/head-pan-coil-fit.html", "dir": true, "thumb": "head-v2/generator/concept/ball_head_render_sheet.png", "make": "python head-v2/fixes/fit_view.py", "caption": "The pan-tilt ball head with its real servo and camera, in 3D."},
      {"id": "ball-head", "kind": "figure", "title": "Ball head renders", "src": "head-v2/generator/concept/ball_head_render_sheet.png", "make": "(tracked render)", "caption": "The ball head from four sides."}
    ]}
  ]
}
```

- [ ] **Step 2: Check every path and command against the repo** (the manifest is the curation, so it must be right):

Run: `python -c "import json,os;m=json.load(open('tools/gallery/manifest.json',encoding='utf-8'));[print('MISSING',i['id'],p) for s in m['sections'] for i in s['items'] for p in [i['src']]+([i['thumb']] if 'thumb' in i else []) if not os.path.exists(p)]"`
Expected: no `MISSING` lines. For any that print, run that entry's `make` command, or correct the path from `ls chassis-v2/out research/tumble/out head-v2/out/fit-view`.

Then check each `make` command is the script that writes its source: for every page, `grep -l "<output file name>" chassis-v2/*.py research/tumble/*.py head-v2/fixes/*.py` must list the script the entry names. Fix any entry that names the wrong one (the v2 legs page is the likeliest).

- [ ] **Step 3: Zach approves the list.** He reads `tools/gallery/manifest.json` (or the gallery's first build, Task 3) and says what comes off, what's missing, and whether the intro is right. Record his call in the plan.

- [ ] **Step 4: Commit (when Zach asks)**

```bash
git add tools/gallery/manifest.json
git commit -m "site: the gallery's manifest (what goes public, each with its source, thumbnail and rebuild command)"
```

---

### Task 2: Page preparation, tested on its own

**Files:**
- Create: `tools/gallery/__init__.py` (empty)
- Create: `tools/gallery/build.py` (the page helpers first)
- Create: `tools/tests/test_site.py`

**Interfaces:**
- Produces: `wrap_page(html: str, back: str) -> str` (adds `<!doctype html>`, `<meta charset="utf-8">` and the viewport meta when the page has none, and a fixed link back to `back`); `strip_private_links(html: str) -> str` (removes every `https://claude.ai/…/artifact/…` URL, keeping the link text); `local_refs(html: str) -> list[str]` (every `href`/`src` that isn't an external URL, a `data:` URI or an in-page `#anchor`).

- [ ] **Step 1: Write the failing tests**

```python
# tools/tests/test_site.py
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from gallery import build as B   # tools/gallery: not 'site', which is a standard-library module


class Pages(unittest.TestCase):
    def test_wrap_adds_a_head_once(self):
        w = B.wrap_page('<title>T</title><div>x</div>', '../index.html')
        self.assertTrue(w.lower().startswith('<!doctype html>'))
        self.assertIn('<meta charset="utf-8">', w)
        self.assertIn('href="../index.html"', w)
        self.assertEqual(B.wrap_page(w, '../index.html').count('<!doctype html>'), 1)   # idempotent

    def test_page_with_its_own_head_is_left_alone(self):
        p = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>T</title></head><body>x</body></html>'
        self.assertEqual(B.wrap_page(p, '../index.html').count('<meta charset'), 1)

    def test_private_links_are_stripped(self):
        h = '<a href="https://claude.ai/artifact/FakeArtifactId0000000a">the hull page</a> and https://claude.ai/code/artifact/abc-123'
        s = B.strip_private_links(h)
        self.assertNotIn('claude.ai', s); self.assertIn('the hull page', s)

    def test_local_refs(self):
        h = ('<script src="https://cdnjs.cloudflare.com/x.js"></script><img src="thumbs/a.jpg">'
             '<a href="#top">t</a><a href="pages/b.html">b</a><img src="data:image/png;base64,AAAA">')
        self.assertEqual(sorted(B.local_refs(h)), ['pages/b.html', 'thumbs/a.jpg'])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run them to see them fail**

Run: `python -m unittest tools/tests/test_site.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'gallery'`

- [ ] **Step 3: Write the helpers**

```python
# tools/gallery/build.py
"""Build the Scorpion gallery: copy the manifest's pages, figures and video into site/out, give every page a document
head and a way back, strip private links, make thumbnails, write index.html, then refuse the build if a local link
is broken, a file is too big, or tools/leakscan.py finds anything.

    python tools/gallery/build.py                 # -> site/out/ (exit 1 on any failed gate)
    python tools/gallery/build.py --allow-missing # build without entries whose source isn't on disk (listed)
"""
import os, re, sys, json, html, shutil, argparse, datetime, subprocess

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'site', 'out')
CDN = ('https://cdnjs.cloudflare.com/', 'https://cdn.jsdelivr.net/', 'https://unpkg.com/', 'https://fonts.googleapis.com/', 'https://fonts.gstatic.com/')
PRIVATE = re.compile(r'https?://claude\.ai/(?:code/)?artifact/[A-Za-z0-9-]+')
HEAD = ('<!doctype html>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n')
BACK = ('<a href="{back}" style="position:fixed;left:12px;bottom:12px;z-index:9999;font:600 13px system-ui,sans-serif;'
        'background:#1c2124;color:#fff;padding:6px 10px;border-radius:6px;text-decoration:none">&larr; Gallery</a>')
LIMIT_MB, TOTAL_MB = 95.0, 900.0


def wrap_page(page: str, back: str) -> str:
    out = page
    if not out.lstrip().lower().startswith('<!doctype'):
        out = HEAD + out
    if 'data-gallery-back' not in out:
        out = out + '\n' + BACK.format(back=back).replace('<a ', '<a data-gallery-back ', 1) + '\n'
    return out


def strip_private_links(page: str) -> str:
    page = re.sub(r'<a\b[^>]*href="' + PRIVATE.pattern + r'"[^>]*>(.*?)</a>', r'\1', page, flags=re.S)
    return PRIVATE.sub('', page)


def local_refs(page: str) -> list:
    refs = re.findall(r'''(?:href|src)\s*=\s*["']([^"']+)["']''', page)
    return [r for r in refs if not (r.startswith(('http://', 'https://', 'data:', '#', 'mailto:', '//')))]
```


- [ ] **Step 4: Run the tests**

Run: `python -m unittest tools/tests/test_site.py -v`
Expected: 4 tests, `OK`

- [ ] **Step 5: Commit (when Zach asks)**

```bash
git add tools/gallery/__init__.py tools/gallery/build.py tools/tests/test_site.py
git commit -m "site: page helpers (a document head and a way back, private links stripped, local references), tested"
```

---

### Task 3: The build, the gallery page and its gates

**Files:**
- Modify: `tools/gallery/build.py` (add `build`, `thumbnail`, `index_html`, `gates`, `main`)
- Create: `tools/gallery/index.tmpl.html`
- Modify: `tools/tests/test_site.py` (add `class Build`)

**Interfaces:**
- Consumes: `wrap_page`, `strip_private_links`, `local_refs` (Task 2); `tools/leakscan.py`'s `scan_folder(folder) -> list[Finding]` (leak audit plan, Task 3).
- Produces: `build(manifest: dict, root: str, out: str, allow_missing=False, limit_mb=LIMIT_MB) -> dict` returning `{'items': int, 'missing': [(id, make)], 'problems': [str]}`; it raises `SystemExit(1)` from `main` when `problems` is non-empty or (without `--allow-missing`) `missing` is.

- [ ] **Step 1: Write the failing tests**

```python
# append to tools/tests/test_site.py
import json, tempfile
from PIL import Image


def tiny_repo():
    d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, 'a', 'out'))
    open(os.path.join(d, 'a', 'out', 'p.html'), 'w', encoding='utf-8').write('<title>P</title><div>3D</div>')
    Image.new('RGB', (900, 600), 'white').save(os.path.join(d, 'a', 'f.png'))
    m = {'title': 'T', 'intro': 'I', 'sections': [{'name': 'S', 'items': [
        {'id': 'p', 'kind': 'page', 'title': 'Page', 'src': 'a/out/p.html', 'thumb': 'a/f.png', 'make': 'x', 'caption': 'c1'},
        {'id': 'f', 'kind': 'figure', 'title': 'Fig', 'src': 'a/f.png', 'make': 'y', 'caption': 'c2'}]}]}
    return d, m


class Build(unittest.TestCase):
    def test_a_clean_build(self):
        d, m = tiny_repo(); out = os.path.join(d, 'site')
        r = B.build(m, d, out)
        self.assertEqual(r['problems'], []); self.assertEqual(r['items'], 2)
        idx = open(os.path.join(out, 'index.html'), encoding='utf-8').read()
        self.assertIn('Page', idx); self.assertIn('Fig', idx); self.assertIn('c1', idx)
        self.assertTrue(os.path.exists(os.path.join(out, 'pages', 'p.html')))
        self.assertTrue(os.path.exists(os.path.join(out, 'thumbs', 'p.jpg')))
        self.assertTrue(os.path.exists(os.path.join(out, '.nojekyll')))

    def test_missing_source_names_its_rebuild_command(self):
        d, m = tiny_repo(); os.remove(os.path.join(d, 'a', 'out', 'p.html'))
        r = B.build(m, d, os.path.join(d, 'site'), allow_missing=True)
        self.assertEqual(r['missing'], [('p', 'x')])

    def test_broken_link_fails_the_gate(self):                      # the control on the link check
        d, m = tiny_repo()
        open(os.path.join(d, 'a', 'out', 'p.html'), 'w', encoding='utf-8').write('<title>P</title><img src="nothere.png">')
        self.assertTrue(any('nothere.png' in p for p in B.build(m, d, os.path.join(d, 'site'))['problems']))

    def test_leak_fails_the_gate(self):                             # the control on the leak check
        d, m = tiny_repo()
        open(os.path.join(d, 'a', 'out', 'p.html'), 'w', encoding='utf-8').write('<title>P</title><p>C:\\Users\\jane\\Desktop</p>')
        self.assertTrue(any('user_path' in p for p in B.build(m, d, os.path.join(d, 'site'))['problems']))

    def test_size_limit_fails_the_gate(self):                       # the control on the size check
        d, m = tiny_repo()
        self.assertTrue(any('MB' in p for p in B.build(m, d, os.path.join(d, 'site'), limit_mb=0.0001)['problems']))
```

- [ ] **Step 2: Run them to see them fail**

Run: `python -m unittest tools/tests/test_site.py -v`
Expected: FAIL, `AttributeError: module 'gallery.build' has no attribute 'build'`

- [ ] **Step 3: Write the gallery template**

```html
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITLE}}</title>
<style>
/* layout: a lab notebook's contents page: sections in build order, cards to open */
:root{--bg:#f4f6f4;--card:#fff;--ink:#1c2124;--mute:#59646a;--line:#dbe1de;--accent:#13824f}
@media (prefers-color-scheme:dark){:root{--bg:#141819;--card:#1c2224;--ink:#e5eae8;--mute:#9aa6aa;--line:#2d3538;--accent:#3cc488;color-scheme:dark}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,"Segoe UI",sans-serif}
.wrap{max-width:1120px;margin:0 auto;padding:28px 16px 56px;display:grid;gap:34px}
h1{font-size:clamp(28px,4vw,40px);margin:0}h2{font-size:20px;margin:0 0 12px}
p.intro{margin:6px 0 0;max-width:70ch;color:var(--mute)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px}
a.card{display:grid;grid-template-rows:auto 1fr;background:var(--card);border:1px solid var(--line);border-radius:8px;overflow:hidden;color:inherit;text-decoration:none}
a.card:hover,a.card:focus-visible{border-color:var(--accent);outline:none}
.thumb{aspect-ratio:3/2;background:var(--line) center/cover no-repeat;display:grid;place-items:center;color:var(--mute);font:600 14px ui-monospace,monospace}
.meta{padding:10px 12px;display:grid;gap:4px}.meta b{font-size:15px}.meta span{font-size:13.5px;color:var(--mute)}
.kind{font:600 11px ui-monospace,monospace;letter-spacing:.06em;text-transform:uppercase;color:var(--accent)}
footer{color:var(--mute);font-size:13px}
</style></head><body><div class="wrap">
<header><h1>{{TITLE}}</h1><p class="intro">{{INTRO}}</p></header>
{{SECTIONS}}
<footer>Built {{BUILT}} from the FPVTank_Prototype repository. 3D pages load three.js from cdnjs.</footer>
</div></body></html>
```

- [ ] **Step 4: Write the build**

```python
# append to tools/gallery/build.py
KIND = {'page': '3D, drag to turn', 'figure': 'figure', 'video': 'video'}


def thumbnail(src, dst, width=640):
    from PIL import Image
    im = Image.open(src).convert('RGB'); h = round(im.height * width / im.width)
    os.makedirs(os.path.dirname(dst), exist_ok=True); im.resize((width, h)).save(dst, 'JPEG', quality=82)


def index_html(manifest, cards):
    t = open(os.path.join(HERE, 'index.tmpl.html'), encoding='utf-8').read()
    sec = []
    for s in manifest['sections']:
        items = ''.join(cards[i['id']] for i in s['items'] if i['id'] in cards)
        if items:
            sec.append(f'<section><h2>{html.escape(s["name"])}</h2><div class="grid">{items}</div></section>')
    return (t.replace('{{TITLE}}', html.escape(manifest['title'])).replace('{{INTRO}}', html.escape(manifest['intro']))
             .replace('{{SECTIONS}}', '\n'.join(sec)).replace('{{BUILT}}', datetime.date.today().isoformat()))


def card(item, href, thumb):
    bg = f' style="background-image:url({thumb})"' if thumb else ''
    label = '' if thumb else html.escape(KIND[item['kind']])
    return (f'<a class="card" href="{href}"><div class="thumb"{bg}>{label}</div><div class="meta">'
            f'<span class="kind">{KIND[item["kind"]]}</span><b>{html.escape(item["title"])}</b><span>{html.escape(item["caption"])}</span></div></a>')


def gates(out, limit_mb=LIMIT_MB):
    problems, total = [], 0
    for base, _, files in os.walk(out):
        for fn in files:
            p = os.path.join(base, fn); mb = os.path.getsize(p) / 1e6; total += mb
            if mb > limit_mb:
                problems.append(f'{os.path.relpath(p, out)} is {mb:.1f} MB (limit {limit_mb} MB)')
            if fn.endswith('.html'):
                page = open(p, encoding='utf-8', errors='replace').read()
                for r in local_refs(page):
                    tgt = os.path.normpath(os.path.join(base, r.split('#')[0].split('?')[0]))
                    if r.split('#')[0] and not os.path.exists(tgt):
                        problems.append(f'{os.path.relpath(p, out)} links to {r}, which is not in the site')
    if total > TOTAL_MB:
        problems.append(f'the site is {total:.0f} MB (limit {TOTAL_MB} MB)')
    sys.path.insert(0, os.path.join(ROOT, 'tools')); import leakscan
    for f in leakscan.scan_folder(out):
        problems.append(f'leakscan {f.grade} {f.rule} in {f.path}: {leakscan.redact(f.value)}')
    return problems


def build(manifest, root=ROOT, out=OUT, allow_missing=False, limit_mb=LIMIT_MB):
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out); open(os.path.join(out, '.nojekyll'), 'w').close()
    cards, missing, n = {}, [], 0
    for s in manifest['sections']:
        for it in s['items']:
            src = os.path.join(root, it['src'])
            if not os.path.exists(src):
                missing.append((it['id'], it['make'])); continue
            ext = os.path.splitext(src)[1].lower()
            if it['kind'] == 'page':
                if it.get('dir'):                                    # a page that loads its sibling files
                    dst_dir = os.path.join(out, 'pages', it['id']); shutil.copytree(os.path.dirname(src), dst_dir)
                    dst = os.path.join(dst_dir, os.path.basename(src)); href = f'pages/{it["id"]}/{os.path.basename(src)}'; back = '../../index.html'
                else:
                    dst = os.path.join(out, 'pages', it['id'] + '.html'); href = f'pages/{it["id"]}.html'; back = '../index.html'
                    os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copyfile(src, dst)
                page = open(dst, encoding='utf-8', errors='replace').read()
                open(dst, 'w', encoding='utf-8').write(wrap_page(strip_private_links(page), back))
            else:
                dst = os.path.join(out, 'media', it['id'] + ext); os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(src, dst); href = f'media/{it["id"]}{ext}'
            th = it.get('thumb') or (it['src'] if it['kind'] == 'figure' else None)
            thumb = None
            if th and os.path.exists(os.path.join(root, th)):
                thumbnail(os.path.join(root, th), os.path.join(out, 'thumbs', it['id'] + '.jpg')); thumb = f'thumbs/{it["id"]}.jpg'
            cards[it['id']] = card(it, href, thumb); n += 1
    open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(index_html(manifest, cards))
    return dict(items=n, missing=missing, problems=gates(out, limit_mb))


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument('--allow-missing', action='store_true'); a = ap.parse_args(argv)
    r = build(json.load(open(os.path.join(HERE, 'manifest.json'), encoding='utf-8')), allow_missing=a.allow_missing)
    for i, mk in r['missing']:
        print(f'missing {i}: rebuild with  {mk}')
    for p in r['problems']:
        print('PROBLEM', p)
    print(f"{r['items']} items in {OUT}; {len(r['missing'])} missing; {len(r['problems'])} problems")
    return 1 if r['problems'] or (r['missing'] and not a.allow_missing) else 0


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 5: Run the tests**

Run: `python -m unittest tools/tests/test_site.py -v`
Expected: 9 tests, `OK`

- [ ] **Step 6: Build the real site and look at it**

Run: `python tools/gallery/build.py`
Expected: `23 items in …\site\out; 0 missing; 0 problems` (rebuild any missing page with the command printed). If leakscan reports problems inside the pages (for example `user_path` in a page's notes), fix the page's generator or template so the text is clean at the source, rebuild that page and rerun; don't allowlist for the site.

Then preview it: add to `.claude/launch.json`

```json
{ "name": "site-out", "runtimeExecutable": "python", "runtimeArgs": ["-m", "http.server", "8769", "--directory", "site/out"], "port": 8769 }
```

and open `http://localhost:8769`: every card opens its page, each 3D page turns and shows "← Gallery", and the browser console shows no errors. Show Zach a screenshot of the gallery and one 3D page (this is his Task 1 Step 3 review if he hasn't done it).

- [ ] **Step 7: Commit (when Zach asks)**

```bash
git add tools/gallery/build.py tools/gallery/index.tmpl.html tools/tests/test_site.py .claude/launch.json
git commit -m "site: build the gallery (pages, figures, video, thumbnails, index) behind link, size and leak gates, each with a control"
```

---

### Task 4: Publishing to a separate public repo (only with Zach's yes)

**Files:**
- Create: `tools/gallery/publish.py`
- Modify: `tools/tests/test_site.py` (add `class Publish`)

**Interfaces:**
- Consumes: `build.main` (Task 3).
- Produces: `publish.main(argv) -> int`. `--repo OWNER/NAME` (default `ZacharyShaver/scorpion-gallery`); without `--yes` it rebuilds, prints what it would push and where, and returns 2 without touching the network.

- [ ] **Step 1: Write the failing test**

```python
# append to tools/tests/test_site.py
from gallery import publish as Pub


class Publish(unittest.TestCase):
    def test_refuses_without_yes(self):
        self.assertEqual(Pub.main(['--repo', 'nobody/none', '--dry-run-dir', tempfile.mkdtemp()]), 2)
```

- [ ] **Step 2: Run it to see it fail**

Run: `python -m unittest tools/tests/test_site.py -v`
Expected: FAIL, `ImportError: cannot import name 'publish'`

- [ ] **Step 3: Write `publish.py`**

```python
# tools/gallery/publish.py
"""Publish site/out to a separate PUBLIC repo and turn GitHub Pages on for it. Outward-facing: it pushes only with --yes,
which Zach gives in chat each time. This repo (private) is never pushed and its history never leaves.

    python tools/gallery/publish.py                       # rebuild, then say what would go where (no network)
    python tools/gallery/publish.py --yes                 # rebuild, create the repo if needed, push, turn Pages on
"""
import os, sys, shutil, argparse, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from gallery import build as B


def sh(*a, cwd=None):
    return subprocess.run(a, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument('--repo', default='ZacharyShaver/scorpion-gallery')
    ap.add_argument('--yes', action='store_true'); ap.add_argument('--dry-run-dir', help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    out = a.dry_run_dir or B.OUT
    if not a.dry_run_dir and B.main([]) != 0:
        print('the build failed its gates: nothing published'); return 1
    files = sum(len(f) for _, _, f in os.walk(out))
    owner, name = a.repo.split('/')
    print(f'would push {files} files from {out} to https://github.com/{a.repo} and serve https://{owner.lower()}.github.io/{name}/')
    if not a.yes:
        print('not published: rerun with --yes once Zach has said yes'); return 2
    if subprocess.run(['gh', 'repo', 'view', a.repo], capture_output=True).returncode != 0:
        sh('gh', 'repo', 'create', a.repo, '--public', '--description', 'Scorpion robot: design pages and simulation results')
    work = tempfile.mkdtemp()
    sh('gh', 'repo', 'clone', a.repo, work)
    for e in os.listdir(work):
        if e != '.git':
            p = os.path.join(work, e); shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    shutil.copytree(out, work, dirs_exist_ok=True)
    src = sh('git', '-C', B.ROOT, 'rev-parse', '--short', 'HEAD')
    sh('git', 'add', '-A', cwd=work)
    if sh('git', 'status', '--porcelain', cwd=work):
        sh('git', 'commit', '-m', f'Gallery build from FPVTank_Prototype {src}', cwd=work)
        sh('git', 'push', 'origin', 'HEAD:main', cwd=work)
    if subprocess.run(['gh', 'api', f'repos/{a.repo}/pages'], capture_output=True).returncode != 0:
        sh('gh', 'api', '-X', 'POST', f'repos/{a.repo}/pages', '-f', 'source[branch]=main', '-f', 'source[path]=/')
    print(f'published: https://{owner.lower()}.github.io/{name}/ (Pages can take a minute)'); return 0


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 4: Run the tests**

Run: `python -m unittest tools/tests/test_site.py -v`
Expected: 10 tests, `OK`

- [ ] **Step 5: Dry run on the real build**

Run: `python tools/gallery/publish.py`
Expected: the build's summary with `0 problems`, then `would push N files … to https://github.com/ZacharyShaver/scorpion-gallery and serve https://zacharyshaver.github.io/scorpion-gallery/`, then `not published`, exit code 2.

- [ ] **Step 6: Publish (only after Zach says yes in chat, naming the repo)**

Run: `python tools/gallery/publish.py --yes --repo ZacharyShaver/<the name he chose>`
Expected: `published: https://zacharyshaver.github.io/<name>/`. Open it, check the gallery and two 3D pages load, and give Zach the link.

- [ ] **Step 7: Commit (when Zach asks), and record the decision**

```bash
git add tools/gallery/publish.py tools/tests/test_site.py
git commit -m "site: publish the gallery to a separate public repo with Pages (dry run by default; --yes to push)"
```

Add to `docs/decisions.md`: the gallery is published from `ZacharyShaver/<name>`, built from this private repo by `tools/gallery/build.py`, gated by `leakscan --strict`; this repo stays private (leak audit, option A).
