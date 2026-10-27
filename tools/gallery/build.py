"""Build the Scorpion gallery: copy the manifest's pages, figures and video into site/out, give every page a document
head and a way back, strip private links, make thumbnails, write index.html, then refuse the build if a local link
is broken, a file is too big, or tools/leakscan.py finds anything.

    python tools/gallery/build.py                 # -> site/out/ (exit 1 on any failed gate)
    python tools/gallery/build.py --allow-missing # build without entries whose source isn't on disk (listed)

A manifest item may carry "hold": "<reason>" (not built, listed); on a page, "standin": [<regex>, ...] (each mesh whose label matches is
built as a plain box of the same bounds) and "licence": "<text>" (credit for the third-party parts the item shows: its page prints it in a
footer with links to the sources, and its card in the index has a Credits line). Every 3D page's footer also says who "you" is.
An item of kind "link" has an https "href" and opens it in a new tab; a section may carry an "intro".
"""
import os, re, sys, json, html, shutil, argparse, datetime, subprocess, urllib.parse, base64, binascii
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'site', 'out'); MANIFEST = os.path.join(HERE, 'manifest.json')
CDN = ('https://cdnjs.cloudflare.com/', 'https://cdn.jsdelivr.net/', 'https://unpkg.com/', 'https://fonts.googleapis.com/', 'https://fonts.gstatic.com/')
ALLOWED_HOSTS = tuple(urllib.parse.urlsplit(u).hostname for u in CDN)     # the only hosts a page may load anything from
MARKER = '.gallery-build'                                                  # build() writes it; it only deletes an out folder that has it

# Parts that come from other people's models. UNCLEARED ones have no recorded licence (the PCA9685 board, the MG90S servo and its horn):
# their geometry must not be published, so a page may show each only as a plain box (standin_page makes the boxes). CREDITED ones may be
# shared with credit (FPV-Rover V2.0 by Markus_p, CC BY-NC-SA 4.0; the Luengoa flex track, CC BY-NC; the Raspberry Pi 5 model, CC0): a
# page that shows one needs its manifest item to carry a "licence" field, which the page prints. Both are matched against the labels of
# the meshes in a page's data, not against its prose.
UNCLEARED = [re.compile(p, re.I) for p in (r'PCA9685', r'MG90', r'servo[-_ ]?horn|^horn\b')]
CREDITED = {kind: [re.compile(p, re.I) for p in ps] for kind, ps in {
    'FPV-Rover V2.0': (r'outer[-_ ]?frame', r'inner[-_ ]?frame', r'track pod', r'sprocket', r'\bcogs?\b', r'crown gear', r'bevel', r'pinion',
                       r'\brollers?\b', r'body[-_ ]?rover', r'\bcovers?\b', r'motor[-_ ]?mount'),
    'Luengoa flex track': (r'luengoa', r'flex[-_ ]?track', r'tpu track'),
    'Raspberry Pi 5': (r'raspberry[-_ ]?pi',)}.items()}
# nose.html stores its meshes under keys alone; these are the names nose.py gives them.
KEY_NAMES = {'pca': 'PCA9685 (Adafruit size)', 'servo': 'Pan servo (MG90S)', 'tilt_servo': 'Tilt servo (MG90S)', 'horn': 'Servo horn (MG90S)',
             'pi': 'Raspberry Pi 5 + active cooler'}
# The MG90S model is fused into a bigger mesh in most chassis pages (the pan coil base holds it), under a label that does not name it.
# A connected piece of a mesh counts as that part when, however it is turned, the box around it along its principal axes has these sides
# (large to small, mm) and its volume (mm3) is this: both within the tolerances (mm, fraction). Measured on the models in the pages (the
# horn is the double-arm one); the servo comes in two versions, the chassis pages' (box 37.1 x 33.4 x 12.2, 7762 mm3) and the nose and fit
# views' (37.5 x 34.2 x 12.2, 7415 mm3, in two connected pieces whose larger is 36.0 x 34.5 x 12.2, 7248 mm3), so the reference sits
# between them.
SHAPES = (('MG90S servo', (36.8, 33.9, 12.2), 7500.0, 1.0, 0.07), ('MG90S servo horn', (31.35, 6.9, 3.7), 241.5, 0.4, 0.06))

# One pattern for every shape a private claude.ai artifact link takes: any case, http or https, with or without www.,
# scheme-less or protocol-relative; slashes plain, JS-escaped (backslash-slash, even doubled), URL-encoded (%2F, even
# twice), JS unicode-escaped or an HTML entity; the paths artifact, code/artifact and public/artifacts; an id of
# letters, digits, '-' and '_'; then any path, query or fragment after the id.
# tools/leakscan.py's artifact_link rule must match the same forms: copy this pattern there (the controller mirrors it;
# leakscan.py is not edited with this file).
_SL = r'(?:/|\\+/|%(?:25)*2F|\\+u002F|&#0*47;|&#x0*2F;|&sol;)'                       # one slash
_CO = r'(?::|%(?:25)*3A|\\+u003A|&#0*58;|&#x0*3A;|&colon;)'                           # the colon after the scheme
_STOP = r"""\s"'<>`\\)"""                                                             # where a URL ends in plain text
_TAIL = (r'(?:' + _SL + r'|\?|\#|%(?:25)*(?:3F|23)|\\+u00(?:3F|23))'                  # starts at / ? # (or their escapes)
         r'(?:[^' + _STOP + r']|\\+/|\\+u00[0-9A-F]{2})*')
PRIVATE = re.compile(
    r'(?:https?' + _CO + _SL + r'{2}|' + _SL + r'{2})?(?:www\.)?claude\.ai' + _SL
    + r'(?:code' + _SL + r')?(?:public' + _SL + r')?artifacts?' + _SL + r'[A-Za-z0-9_-]+(?:' + _TAIL + r')?', re.I)

HEAD = ('<!doctype html>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n')
BACK = ('<a data-gallery-back href="{back}" aria-label="Back to the gallery" style="position:fixed;'
        'left:calc(12px + env(safe-area-inset-left,0px));bottom:calc(12px + env(safe-area-inset-bottom,0px));z-index:9999;'
        'font:600 13px system-ui,sans-serif;background:#1c2124;color:#fff;padding:6px 10px;border-radius:6px;'
        'text-decoration:none"><span aria-hidden="true">&larr;</span> Gallery</a>')
# The credit is a footer in the page's flow (never fixed, so it covers nothing); only the way back stays fixed. It holds the item's licence
# text, the sources that text names, a link to the list of third-party files, and, for 3D pages, a note about who 'you' is.
SOURCES = (('FPV-Rover V2.0', r'FPV-Rover', 'CC BY-NC-SA 4.0', 'https://www.printables.com/model/3150-fpv-rover-v20-tank'),
           ('Luengoa tracks', r'Luengoa', 'CC BY-NC', 'https://www.thingiverse.com/thing:7127065'),
           ('Raspberry Pi 5 model', r'Raspberry Pi 5', 'CC0', 'https://printables.com/model/727155-raspberry-pi-5'))     # (label, a regex for the licence text, licence, link)
THIRD_PARTY_URL = 'https://github.com/ZacharyShaver/FPVTank_Prototype/blob/research-sprint/THIRD_PARTY.md'
PAGE_NOTE = "These pages began as design notes written to Zach during development, so 'you' and 'your' mean him."
FOOTER_CSS = ('footer[data-gallery-footer]{display:block;box-sizing:border-box;margin:28px 0 0;padding:16px 16px calc(64px + env(safe-area-inset-bottom,0px));'
              'background:#eef1ef;color:#1c2124;border-top:1px solid #c9d1ce;font:13px/1.5 system-ui,"Segoe UI",sans-serif;text-align:left}'
              'footer[data-gallery-footer] p{margin:0 0 6px;max-width:80ch;font:inherit;color:inherit}'
              'footer[data-gallery-footer] a{color:#0b5a37;text-decoration:underline}'
              '@media (prefers-color-scheme:dark){footer[data-gallery-footer]{background:#1c2224;color:#e5eae8;border-top-color:#2d3538}'
              'footer[data-gallery-footer] a{color:#7fdcae}}')                      # room under the text (64px) for the fixed back link; own colours either way
BOM = chr(0xFEFF)                                              # U+FEFF, the byte-order mark some editors put first
LIMIT_MB, TOTAL_MB = 95.0, 900.0


_DOCTYPE = re.compile(r'<!doctype', re.I)
_OLD_BACK = re.compile(r'\n?<a data-gallery-back\b[^>]*>.*?</a>\n?', re.S)
_OLD_FOOTER = re.compile(r'\n?<footer data-gallery-footer\b[^>]*>.*?</footer\s*>\n?', re.S)
_BODY_END = re.compile(r'</body\s*>(?=\s*(?:</html\s*>\s*)?\Z)', re.I)          # a </body> that ends the page, not one inside a script string


def _has_doctype(page: str) -> bool:
    """True when the page opens with a doctype; a BOM, whitespace and HTML comments before it count as nothing."""
    i, n = 0, len(page)
    while i < n:
        if page[i] == BOM or page[i].isspace():
            i += 1
        elif page.startswith('<!--', i):
            j = page.find('-->', i + 4)
            if j < 0:
                return False
            i = j + 3
        else:
            break
    return _DOCTYPE.match(page, i) is not None


def credited_sources(licence) -> list:
    """The SOURCES that a licence text names, in SOURCES order."""
    return [s for s in SOURCES if re.search(s[1], licence or '', re.I)]


def credit_footer(credit=None, note=None) -> str:
    """The footer for a page: the `credit` (a licence text), the sources it names and the list of third-party files, then the `note`.
    All text is escaped. '' when there is neither."""
    esc = lambda s: html.escape(s, quote=True)
    rows = []
    if credit:
        rows.append(f'<p data-gallery-credit>{esc(credit)}</p>')
        named = ', '.join(f'<a href="{esc(url)}">{esc(label)}</a>' for label, _, _, url in credited_sources(credit))
        rows.append(f'<p data-gallery-sources>{"Sources: " + named + ". " if named else ""}The full list of third-party files: '
                    f'<a href="{esc(THIRD_PARTY_URL)}">THIRD_PARTY.md</a>.</p>')
    if note:
        rows.append(f'<p data-gallery-note>{esc(note)}</p>')
    return f'<footer data-gallery-footer><style>{FOOTER_CSS}</style>\n' + '\n'.join(rows) + '\n</footer>' if rows else ''


def wrap_page(page: str, back: str, credit: str = None, note: str = None) -> str:
    """Give the page a document head if it lacks a doctype and exactly one fixed link back to `back`. With a `credit` or a `note` it also
    gets one footer in its flow, at the end of the body (credit_footer; escaped). A link and a footer from an earlier wrap are replaced,
    so wrapping twice gives the same page."""
    out = page
    if not _has_doctype(out):
        out = HEAD + out.lstrip(BOM)
    if 'data-gallery-back' in out:
        out = _OLD_BACK.sub('', out)
    if 'data-gallery-footer' in out:
        out = _OLD_FOOTER.sub('', out)
    foot = credit_footer(credit, note)
    if foot:
        end = _BODY_END.search(out, max(0, len(out) - 2000))
        at = end.start() if end else len(out)
        out = out[:at] + '\n' + foot + '\n' + out[at:]
    return out + '\n' + BACK.format(back=html.escape(back, quote=True)) + '\n'


_ATTRS = r"""(?:[^>"']|"[^"]*"|'[^']*')*"""                  # the rest of a tag: quoted values may hold a '>'
_P = PRIVATE.pattern
_ANCHOR = re.compile(                                          # <a ... href=<private url> ...>text</a>  ->  text
    r'<a\b' + _ATTRS + r'?\bhref\s*=\s*(?:"[^"]*?' + _P + r'[^"]*"|\'[^\']*?' + _P + r'[^\']*\'|' + _P + r'[^\s>]*)'
    + _ATTRS + r'>(?P<t>(?:(?!<a\b|</a\s*>).)*)(?:</a\s*>)?', re.I | re.S)
_MDLINK = re.compile(                                          # [text](<private url> "title")  ->  text
    r'\[(?P<t>[^\[\]\n]{0,500})\]\(\s*<?' + _P + r'>?(?:\s+(?:"[^"\n]*"|\'[^\'\n]*\'))?\s*\)', re.I)


_LEAD = 64                                                     # how far before 'claude.ai' a scheme and slashes can start


def _private_matches(page: str) -> list:
    """The non-overlapping PRIVATE matches, in order. Scanning 11 MB for the whole pattern takes over a second, so look
    only where 'claude.ai' occurs (any case) and try a match from just before it. A scheme or slashes further back than
    _LEAD stay behind; the id never does."""
    low = page.lower()
    if len(low) != len(page):                                    # a few characters change length when lowercased
        return list(PRIVATE.finditer(page))
    found, end, i = [], 0, low.find('claude.ai')
    while i != -1:
        if i >= end and page[i + 9:i + 10] in ('/', '\\', '%', '&'):       # a slash, or the start of an escaped one
            for start in range(max(end, i - _LEAD), i + 1):
                m = PRIVATE.match(page, start)
                if m:
                    found.append(m); end = m.end()
                    break
        i = low.find('claude.ai', i + 1)
    return found


def strip_private_links(page: str) -> str:
    """Remove every private claude.ai artifact URL (see PRIVATE). An <a href> to one is unwrapped to its text, a markdown
    link [t](url) becomes t, and anywhere else (text, JSON, JS strings, other attributes) only the URL goes."""
    if not _private_matches(page):
        return page
    page = _ANCHOR.sub(r'\g<t>', page)
    page = _MDLINK.sub(r'\g<t>', page)
    out, pos = [], 0
    for m in _private_matches(page):
        out.append(page[pos:m.start()]); pos = m.end()
    out.append(page[pos:])
    return ''.join(out)


_COMMENT = re.compile(r'<!--.*?(?:-->|\Z)', re.S)               # an unclosed comment runs to the end, as in a browser
_ATTR = re.compile(r'''(srcset|src|href|style|poster)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'<>`;(){}\[\]]+)(?=[\s>]|$))''', re.I)
_STYLE_BLOCK = re.compile(r'<style\b[^>]*>(.*?)(?:</style\s*>|\Z)', re.I | re.S)
_CSS_URL = re.compile(r'''url\(\s*(?:"([^"]*)"|'([^']*)'|([^)\s"']*))\s*\)''', re.I)
_SCHEME = re.compile(r'[A-Za-z][A-Za-z0-9+.\-]*:')              # http:, javascript:, tel:, blob:, file:, mailto:, data: ...
_SLASHES2 = re.compile(r'[\\/]{2}')                              # protocol-relative (a browser reads \\ as // too)


_TAG_OPEN = re.compile(r'<[A-Za-z][A-Za-z0-9:-]*\s')
_CONCAT = re.compile(r'''['"]\s*\+|\+\s*['"]|\$\{''')           # a piece of JS string building, not a path


def _in_tag(page: str, pos: int) -> bool:
    """True when `pos` lies inside an open tag: the last '<' before it starts a tag and no '>' has closed it."""
    lt = page.rfind('<', max(0, pos - 4000), pos)
    return lt != -1 and page.find('>', lt, pos) == -1 and _TAG_OPEN.match(page, lt) is not None


def _srcset_urls(value: str):
    """The URL of each candidate in a srcset ('a.png 1x, b.png 2x'); a comma inside a data: URI is not a separator."""
    i, n = 0, len(value)
    while i < n:
        while i < n and (value[i].isspace() or value[i] == ','):
            i += 1
        j = i
        while j < n and not value[j].isspace():
            j += 1
        url, i = value[i:j], j
        if not url:
            break
        if url.endswith(','):
            url = url.rstrip(',')                                # no descriptor: the comma ends the candidate
        else:
            while i < n and value[i] != ',':                    # skip the descriptor (1x, 100w)
                i += 1
        yield url


def _as_path(ref: str):
    """The file path a reference points at, or None for an external URL, data: URI, #anchor or empty value."""
    ref = (html.unescape(ref) if '&' in ref else ref)
    ref = re.sub(r'[\t\r\n]', '', ref).strip()                  # a browser drops tabs and newlines in a URL, trims its ends
    if not ref or _SLASHES2.match(ref) or _SCHEME.match(ref):         # '#anchor' and '?query' alone come out empty below
        return None
    ref = re.split(r'[?#]', ref, 1)[0]
    return urllib.parse.unquote(ref) or None


def local_refs(page: str) -> list:
    """Every href, src, srcset candidate and CSS url(...) (style blocks and style attributes) that points at a local file,
    in page order, as a path: query and fragment removed, %-escapes decoded. HTML comments are ignored."""
    if '<!--' in page:
        page = _COMMENT.sub('', page)
    found = []                                                   # (position, raw reference)
    for m in _ATTR.finditer(page):
        name, dq, sq, uq = m.group(1).lower(), m.group(2), m.group(3), m.group(4)
        before = page[m.start() - 1] if m.start() else ' '
        if before.isalnum() or before == '_':                    # 'xsrc=' or 'data_src=' is another attribute
            continue
        if uq is not None and not (before.isspace() and _in_tag(page, m.start())):   # not 'var src = y;' or prose
            continue
        value = dq if dq is not None else sq if sq is not None else uq
        if name not in ('style', 'srcset') and _CONCAT.search(value):                # '<a href="' + url + '">' in a script
            continue
        if name == 'style':
            value = html.unescape(value) if '&' in value else value
            found += [(m.start(), next(g for g in c.groups() if g is not None)) for c in _CSS_URL.finditer(value)]
        elif name == 'srcset':
            found += [(m.start(), u) for u in _srcset_urls(html.unescape(value) if '&' in value else value)]
        else:
            found.append((m.start(), value))
    for m in _STYLE_BLOCK.finditer(page):
        found += [(m.start(1) + c.start(), next(g for g in c.groups() if g is not None)) for c in _CSS_URL.finditer(m.group(1))]
    found.sort(key=lambda f: f[0])
    return [p for p in (_as_path(raw) for _, raw in found) if p]


# ---------------------------------------------------------------- the build

KIND = {'page': '3D, drag to turn', 'figure': 'figure', 'video': 'video', 'link': 'link, opens in a new tab'}


def strip_all(page: str, passes: int = 5) -> str:
    """strip_private_links until the page stops changing: removing one URL can join its neighbours into a new one
    ('claude' + 'https://claude.ai/artifact/Z' + '.ai/artifact/Q'). Capped; whatever survives the cap is the leak gate's."""
    for _ in range(passes):
        s = strip_private_links(page)
        if s == page:
            break
        page = s
    return page


# A link object whose url was a private link and is now empty: {"url":"","title":"..."}. The title says which site page it was.
_LINK_OBJ = re.compile(r'\{\s*"url"\s*:\s*""\s*,\s*"title"\s*:\s*("(?:[^"\\]|\\.)*")\s*\}')


def rewrite_links(page: str, mapping: dict, built: set) -> str:
    """Point each emptied link object at its site page ({"url":"<id>.html",...}, a sibling in pages/) when its title is in
    `mapping` and that page is built; any other becomes null (the page's own script must draw nothing for a null link)."""
    def sub(m):
        try:
            tid = mapping.get(json.loads(m.group(1)))
        except ValueError:
            tid = None
        if tid in built:
            return '{"url":%s,"title":%s}' % (json.dumps(tid + '.html'), m.group(1))
        return 'null'
    return _LINK_OBJ.sub(sub, page)


def thumbnail(src, dst, width=640, rotate=0):
    from PIL import Image
    im = Image.open(src).convert('RGB')
    if rotate:
        im = im.rotate(rotate, expand=True)                          # degrees counter-clockwise, as for the figure itself
    h = round(im.height * width / im.width)
    os.makedirs(os.path.dirname(dst), exist_ok=True); im.resize((width, h)).save(dst, 'JPEG', quality=82)


def rotated_copy(src, dst, degrees):
    """A figure turned `degrees` counter-clockwise (a photo taken sideways). Re-saving also drops its metadata."""
    from PIL import Image
    im = Image.open(src).rotate(degrees, expand=True)
    if dst.lower().endswith(('.jpg', '.jpeg')):
        im.convert('RGB').save(dst, 'JPEG', quality=90)
    else:
        im.save(dst)


def video_page(item, src, poster=None):
    """A small page for a clip: the title, the player, the caption. `src` and `poster` are relative to pages/."""
    t = html.escape(item['title']); pos = f' poster="{html.escape(poster, quote=True)}"' if poster else ''
    return (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{t}</title>\n<style>\n'
            ':root{--bg:#f4f6f4;--ink:#1c2124;--mute:#59646a}\n'
            '@media (prefers-color-scheme:dark){:root{--bg:#141819;--ink:#e5eae8;--mute:#9aa6aa;color-scheme:dark}}\n'
            'body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,"Segoe UI",sans-serif}\n'
            'main{max-width:960px;margin:0 auto;padding:28px 16px 72px}h1{font-size:clamp(24px,4vw,32px);margin:0 0 14px}\n'
            'video{display:block;width:100%;height:auto;border-radius:8px;background:#000}p{color:var(--mute);max-width:70ch}\n'
            f'</style></head><body><main><h1>{t}</h1>\n'
            f'<video controls muted loop playsinline preload="metadata"{pos} src="{html.escape(src, quote=True)}"></video>\n'
            f'<p>{html.escape(item["caption"])}</p></main></body></html>\n')


_PLACEHOLDER = re.compile(r'\{\{(TITLE|INTRO|SECTIONS|BUILT)\}\}')


def index_html(manifest, cards):
    with open(os.path.join(HERE, 'index.tmpl.html'), encoding='utf-8') as fh:
        t = fh.read()
    sec = []
    for s in manifest['sections']:
        items = ''.join(cards[i['id']] for i in s['items'] if i['id'] in cards)
        if items:
            intro = f'<p class="sect-intro">{html.escape(s["intro"])}</p>' if s.get('intro') else ''
            sec.append(f'<section><h2>{html.escape(s["name"])}</h2>{intro}<div class="grid">{items}</div></section>')
    val = {'TITLE': html.escape(manifest['title']), 'INTRO': html.escape(manifest['intro']), 'SECTIONS': '\n'.join(sec),
           'BUILT': datetime.date.today().isoformat()}
    return _PLACEHOLDER.sub(lambda m: val[m.group(1)], t)               # one pass: a {{BUILT}} inside a caption stays as written


def credits_line(licence) -> str:
    """The short Credits line of an index card (HTML): the sources the licence names, with their licences, and a link to the list."""
    named = ', '.join(f'{label} ({short})' for label, _, short, _ in credited_sources(licence)) or 'stand-in boxes for parts without a recorded licence'
    return f'Credits: {html.escape(named)}. <a href="{html.escape(THIRD_PARTY_URL, quote=True)}">Full list</a>'


def card(item, href, thumb):
    bg = f' style="background-image:url({html.escape(thumb, quote=True)})"' if thumb else ''
    label = '' if thumb else html.escape(item['title'])                      # no picture: the title fills the picture area (the kind line says what it is)
    hide = '' if thumb else ' aria-hidden="true"'                            # the title is read once, from the line below
    tab = ' target="_blank" rel="noopener"' if item['kind'] == 'link' else ''
    main = (f'<a class="card" href="{html.escape(href, quote=True)}"{tab}><div class="thumb"{bg}{hide}>{label}</div><div class="meta">'
            f'<span class="kind">{KIND[item["kind"]]}</span><b>{html.escape(item["title"])}</b><span>{html.escape(item["caption"])}</span></div></a>')
    if not item.get('licence'):
        return main
    return f'<div class="cardbox">{main}<p class="credits">{credits_line(item["licence"])}</p></div>'      # a link cannot sit inside the card's own link


# ---------------------------------------------------------------- the gates

_ASSET_EXT = ('.json', '.obj', '.stl', '.glb', '.gltf', '.bin', '.png', '.jpg', '.jpeg', '.webp', '.mp4', '.css', '.js')
_CSS_IMPORT = re.compile(r'''@import\s+(?:"([^"]*)"|'([^']*)')''', re.I)                    # @import "x.css" (the url(...) form is _CSS_URL's)
_LINK_TAG = re.compile(r'<link\b' + _ATTRS + r'>', re.I)
_REL = re.compile(r'''\brel\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>"']+))''', re.I)
_LOADING_RELS = {'stylesheet', 'preload', 'modulepreload', 'prefetch', 'icon', 'manifest'}      # a <link> with one of these fetches its href
_IMPORTMAP = re.compile(r'<script\b[^>]*\btype\s*=\s*["\']?importmap\b[^>]*>(.*?)(?:</script\s*>|\Z)', re.I | re.S)
# JS that loads a quoted path: fetch('x'), x.load('x'), import('x'), new Worker('x'), importScripts('x'), el.src = 'x'. `plus` is set when
# the literal is only the start of a longer string ('x' + name).
_JS_SINK = re.compile(r'''(?:\bfetch\s*\(|\.load\s*\(|\bimport\s*\(|\bnew\s+Worker\s*\(|\bimportScripts\s*\(|\.src\s*=(?!=))\s*'''
                      r'''(?P<q>['"`])(?P<v>[^'"`\n]*)(?P=q)(?P<plus>\s*\+)?''')
_JS_IMPORT = re.compile(r'''(?<![\w$.'"])(?:import|export)\b\s*(?:[\w$*{},\s]*?\bfrom\s*)?(?P<q>['"])(?P<v>[^'"\n]*)(?P=q)''')   # import x from 'u'; import 'u'


def _css_refs(css: str) -> list:
    """The raw urls of a stylesheet: url(...) and @import "..."."""
    return [next(g for g in c.groups() if g is not None) for rx in (_CSS_URL, _CSS_IMPORT) for c in rx.finditer(css)]


def _loading_link(page: str, pos: int) -> bool:
    """True when the attribute at `pos` is the href of a <link> whose rel makes the browser fetch it."""
    lt = page.rfind('<', max(0, pos - 4000), pos)
    m = _LINK_TAG.match(page, lt) if lt != -1 else None
    if not m or m.end() < pos:
        return False
    rel = _REL.search(m.group(0))
    return bool(rel) and bool(_LOADING_RELS & set(next(g for g in rel.groups() if g is not None).lower().split()))


def _importmap_urls(block: str) -> list:
    try:
        data = json.loads(block)
    except ValueError:
        return [u for u in re.findall(r'"([^"]*)"', block) if re.match(r'(?:https?:)?//', u, re.I)]
    out, todo = [], [data]
    while todo:
        x = todo.pop()
        if isinstance(x, dict):
            todo += list(x.values())
        elif isinstance(x, list):
            todo += x
        elif isinstance(x, str):
            out.append(x)
    return out


def _html_loads(page: str) -> list:
    """Every raw reference an HTML page loads: src, poster, srcset candidates, url(...) and @import in style blocks and
    attributes, the href of a <link> that fetches (stylesheet, preload, icon ...) and an import map's targets. A plain
    <a href> loads nothing and is left out. Comments are ignored."""
    if '<!--' in page:
        page = _COMMENT.sub('', page)
    out = []
    for m in _ATTR.finditer(page):                                  # the same filters as local_refs
        name, dq, sq, uq = m.group(1).lower(), m.group(2), m.group(3), m.group(4)
        before = page[m.start() - 1] if m.start() else ' '
        if before.isalnum() or before == '_' or (uq is not None and not (before.isspace() and _in_tag(page, m.start()))):
            continue
        value = dq if dq is not None else sq if sq is not None else uq
        if name not in ('style', 'srcset') and _CONCAT.search(value):
            continue
        if name == 'style':
            out += _css_refs(html.unescape(value) if '&' in value else value)
        elif name == 'srcset':
            out += _srcset_urls(html.unescape(value) if '&' in value else value)
        elif name != 'href' or _loading_link(page, m.start()):
            out.append(value)
    for m in _STYLE_BLOCK.finditer(page):
        out += _css_refs(m.group(1))
    for m in _IMPORTMAP.finditer(page):
        out += _importmap_urls(m.group(1))
    return out


def _js_values(text: str) -> list:
    """(quoted path, whole) for each load in JS text; `whole` is False when the literal is only the start of a longer string."""
    out = [(m.group('v'), not m.group('plus') and '${' not in m.group('v')) for m in _JS_SINK.finditer(text)]
    return out + [(m.group('v'), True) for m in _JS_IMPORT.finditer(text)]


def _ext_host(ref: str):
    """The host of an external http(s) or protocol-relative reference (lowercase; '?' when it has none), else None."""
    ref = html.unescape(ref) if '&' in ref else ref
    ref = re.sub(r'[\t\r\n]', '', ref).strip().replace('\\', '/')       # a browser trims these and reads a backslash as a slash
    if ref.startswith('//'):
        ref = 'http:' + ref
    if not re.match(r'https?:', ref, re.I):
        return None
    try:
        return urllib.parse.urlsplit(ref).hostname or '?'
    except ValueError:
        return '?'


def _asset_path(ref: str):
    """The local path of a JS load, only when it names an asset file (.json, .png, .js ...)."""
    p = _as_path(ref)
    return p if p and os.path.splitext(p)[1].lower() in _ASSET_EXT else None


def _names(cache: dict, folder: str) -> set:
    if folder not in cache:
        try:
            cache[folder] = set(os.listdir(folder))
        except OSError:
            cache[folder] = set()
    return cache[folder]


def _resolve(root: str, base: str, ref: str, cache: dict):
    """The site path ('pages/a.html') that `ref`, written in a file in folder `base`, points at, or None when nothing is there:
    missing, outside the site, or only there in another case (GitHub Pages is case-sensitive; Windows and macOS are not, so
    every name is compared with the folder's listing). A folder stands for its index.html."""
    tgt = os.path.abspath(os.path.join(base, ref))
    if tgt != root and not tgt.startswith(root + os.sep):
        return None
    parts = [] if tgt == root else os.path.relpath(tgt, root).split(os.sep)
    cur = root
    for part in parts:
        if part not in _names(cache, cur):
            return None
        cur = os.path.join(cur, part)
    if os.path.isdir(cur):
        if 'index.html' not in _names(cache, cur):
            return None
        parts.append('index.html')
    return '/'.join(parts)


def _kind(name: str):
    n = name.lower()
    return 'html' if n.endswith(('.html', '.htm', '.svg')) else 'css' if n.endswith('.css') else 'js' if n.endswith(('.js', '.mjs')) else None


def gates(out, limit_mb=LIMIT_MB):
    """Problems with the built site: a file or the whole site over its limit; a reference (HTML, CSS or JS) to a file that is
    not there, in that case, inside the site; a load from a host the site does not allow; a file nothing links to; and anything
    tools/leakscan.py finds (no allowlist: every finding is a problem)."""
    problems, total, root = [], 0, os.path.abspath(out)
    cache, edges, files = {}, {}, []                              # edges: file -> the site files it points at
    for base, _, names in os.walk(out):
        for fn in names:
            p = os.path.join(base, fn); rel = os.path.relpath(p, out).replace(os.sep, '/'); mb = os.path.getsize(p) / 1e6
            total += mb; files.append(rel)
            if mb > limit_mb:
                problems.append(f'{rel} is {mb:.1f} MB (limit {limit_mb} MB)')
                continue
            kind = _kind(fn)
            if kind is None:
                continue
            text = _read(p)
            raw = _html_loads(text) if kind == 'html' else _css_refs(text) if kind == 'css' else []
            js = _js_values(text) if kind != 'css' else []
            for r in dict.fromkeys(raw + [v for v, _ in js]):
                host = _ext_host(r)
                if host is not None and host not in ALLOWED_HOSTS:
                    problems.append(f'{rel} loads {r[:150]}, from a host the site does not allow (allowed: {", ".join(ALLOWED_HOSTS)})')
            refs = (local_refs(text) if kind == 'html' else []) + [_as_path(r) for r in raw] + [_asset_path(v) for v, whole in js if whole]
            edges[rel] = set()
            for r in dict.fromkeys(r for r in refs if r):
                t = _resolve(root, base, r, cache)
                if t is None:
                    problems.append(f'{rel} links to {r}, which is not in the site')
                else:
                    edges[rel].add(t)
    if total > TOTAL_MB:
        problems.append(f'the site is {total:.1f} MB (limit {TOTAL_MB} MB)')
    if 'index.html' not in files:
        problems.append('the site has no index.html')
    reached, todo = {'index.html'}, ['index.html']
    while todo:
        for t in edges.get(todo.pop(), ()):
            if t not in reached:
                reached.add(t); todo.append(t)
    problems += [f'{rel} is in the site but nothing links to it' for rel in sorted(files) if rel not in reached and rel not in (MARKER, '.nojekyll')]
    tools = os.path.dirname(HERE)
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import leakscan
    for f in leakscan.scan_folder(out):
        problems.append(f'leakscan {f.grade} {f.rule} in {f.path}:{f.line}: {leakscan.redact(f.value)}')
    return problems


def _read(path):
    with open(path, encoding='utf-8', errors='replace', newline='') as fh:
        return fh.read()


def _write(path, text):
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)


# ---------------------------------------------------------------- third-party parts: meshes, stand-in boxes, the gate

# A page's 3D data is read as meshes: standin_page() swaps the uncleared ones for boxes and geometry_problems() checks the result.
# Formats read (each a JSON value assigned to a name in a script, or in a .js or .json file): the chassis pages' `const D={...}`
# (meshes {v: int16 x 0.02 mm, f: uint16 or uint32, i32}, labelled in place; lineup.html keeps one list of shapes and labels them
# from its parts), nose.html (the same, keyed and unlabelled), the fit view's `window.FIT` and plus-sleeve's `window.PARTS` (float32
# and uint32; the sleeve's labels sit in a LOOK table in its script). Any other data that carries 3D data is unreadable: it passes
# only while it shows no uncleared name.
_Q = 0.02                                                                       # the chassis pages store vertices in steps of 0.02 mm
_B64 = re.compile(r'[A-Za-z0-9+/]{120,}={0,2}')                                  # a payload: a long base64 run ...
_NUMS = re.compile(r'(?:-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?\s*,\s*){60,}')           # ... or a long list of numbers
_IMAGE_B64 = ('iVBORw0KGgo', '/9j/', 'R0lGOD', 'UklGR')                            # a PNG, JPEG, GIF or WebP: a picture, not a mesh
_MESHY = re.compile(r'positions?|vertices|verts|triangles|tris|indices|faces', re.I)    # keys that hold a mesh as a list of numbers
_SCRIPT = re.compile(r'<script\b([^>]*)>(.*?)</script\s*>', re.I | re.S)
_ASSIGN = re.compile(r'\s*(?:(?:const|let|var)\s+)?[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*\s*=\s*(?=[\[{])')
_SEMI = re.compile(r'\s*;?')
_LOOK = re.compile(r"""(?P<key>[A-Za-z_$][\w$]*)\s*:\s*\[\s*(?P<q>['"])(?P<label>(?:(?!(?P=q))[^\\\n]|\\.)*)(?P=q)\s*,""")
_SCRIPT_EXT = ('.js', '.mjs', '.json')
_MESH_EXT = ('.obj', '.mtl', '.gltf', '.stl', '.ply', '.glb', '.3mf', '.step', '.stp', '.bin')    # files that are 3D data as a whole
_GATE_EXT = ('.html', '.htm') + _SCRIPT_EXT + _MESH_EXT
SUFFIX = ' (stand-in box)'
_BOX_F = ((0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (3, 7, 6), (3, 6, 2), (0, 4, 7), (0, 7, 3), (1, 2, 6), (1, 6, 5))


def is_uncleared(name: str) -> bool:
    return any(rx.search(name) for rx in UNCLEARED)


def credited_kinds(name: str) -> list:
    return [kind for kind, rxs in CREDITED.items() if any(rx.search(name) for rx in rxs)]


def _has_payload(text: str) -> bool:
    return any(not m.group(0).startswith(_IMAGE_B64) for m in _B64.finditer(text)) or bool(_NUMS.search(text))


def _carries_mesh(x: dict) -> bool:
    """True when a dict holds 3D data in some encoding this does not read: a long base64 string (not a picture), or a long list
    under a key named like a mesh."""
    return any((isinstance(v, str) and len(v) >= 200 and _B64.fullmatch(v) is not None and not v.startswith(_IMAGE_B64))
               or (isinstance(v, list) and len(v) >= 30 and _MESHY.search(str(k)) is not None) for k, v in x.items())


# ---- meshes

def _decode(node):
    """(V, F): vertices (n, 3) in the page's units and triangles (m, 3), read as the page's own loader reads them (int16 x 0.02 and
    uint16 or uint32 when the node has 'i32'; else float32 and uint32). None when the node cannot be read."""
    try:
        v = base64.b64decode(node['v'], validate=True); f = base64.b64decode(node['f'], validate=True)
        if 'i32' in node:
            V = np.frombuffer(v, '<i2').astype(np.float64) * _Q; F = np.frombuffer(f, '<u4' if node['i32'] else '<u2')
        else:
            V = np.frombuffer(v, '<f4').astype(np.float64); F = np.frombuffer(f, '<u4')
        if len(V) % 3 or len(F) % 3:
            return None
        V, F = V.reshape(-1, 3), F.reshape(-1, 3).astype(np.int64)
        return (V, F) if not F.size or F.max() < len(V) else None
    except (ValueError, TypeError, binascii.Error):
        return None


def _store(node, V, F):
    """Put (V, F) in `node` the way its loader reads them. The keys keep their order."""
    b = lambda a: base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()
    if 'i32' in node:
        i32 = len(V) > 65535                                           # as the generators choose it
        node['v'] = b(np.rint(V / _Q).astype('<i2')); node['f'] = b(F.astype('<u4' if i32 else '<u2')); node['i32'] = i32
    else:
        node['v'] = b(V.astype('<f4')); node['f'] = b(F.astype('<u4'))


def _box(lo, hi):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    V = np.array([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], float)
    return V, np.array(_BOX_F, np.int64)


def _box_of(V, F):
    u = V[np.unique(F)]
    return _box(u.min(0), u.max(0))


def _is_box(V, F) -> bool:
    """At most 8 distinct vertices: a box (or less), and nothing more."""
    u = np.unique(F)
    return len(u) <= 8 or len(np.unique(V[u], axis=0)) <= 8


def _components(n, F):
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]]])
    return connected_components(coo_matrix((np.ones(len(e), np.int8), (e[:, 0], e[:, 1])), shape=(n, n)), directed=False)[1]


def _volume(V, F) -> float:
    """The volume a closed mesh encloses, as the sum of the signed tetrahedra to the origin; negative when its faces point inward."""
    return float(np.einsum('ij,ij->i', V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum() / 6)


def _pca_extents(V, F):
    """The sides of the box around a closed piece (vertices V, triangles F) along its principal axes, large to small. The axes are those
    of the solid (its second moments, summed over the signed tetrahedra to the origin, which do not change with how the surface is cut
    into triangles); turning or mirroring the mesh turns the axes with it, so the sides stay the same. Axes are only defined where the
    three moments differ: the servo's and the horn's do (their two largest differ by half or more)."""
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    v = np.einsum('ij,ij->i', a, np.cross(b, c)) / 6
    total = v.sum()
    if abs(total) < 1e-9:
        return np.zeros(3)
    s = a + b + c
    mean = (v @ s) / (4 * total)
    cov = sum(np.einsum('i,ij,ik->jk', v, x, x) for x in (a, b, c, s)) / (20 * total) - np.outer(mean, mean)
    axes = np.linalg.eigh(cov)[1]
    return np.sort(np.ptp(V[np.unique(F)] @ axes, axis=0))[::-1]


def _piece_size(V, F):
    """(sides of the box about its principal axes, large to small; absolute volume) of one piece: the two sizes of it that do not change
    when it is turned or mirrored."""
    return _pca_extents(V, F), abs(_volume(V, F))


def _fused(V, F):
    """[(shape name, mask of its triangles)]: the connected pieces of a mesh that are the size of a known uncleared part (SHAPES), turned
    any way, and are not boxes. This is how an MG90S model fused into a base mesh shows up."""
    if not F.size or len(V) <= 8:
        return []
    diagonal = float(np.linalg.norm(np.ptp(V, axis=0)))                   # a piece fits in the mesh's box, whichever way it is turned
    shapes = [s for s in SHAPES if diagonal >= s[1][0] - s[3]]
    if not shapes:
        return []
    if len(V) > 1.5 * len(F):                                       # every triangle has vertices of its own: weld them first
        V, inv = np.unique(V, axis=0, return_inverse=True); F = inv.reshape(-1)[F]
    lab = _components(len(V), F)
    n = int(lab.max()) + 1; tri = lab[F[:, 0]]; verts = np.bincount(lab, minlength=n)
    P = V - V.mean(0)                                               # volumes about the middle of the mesh, to keep the sums small
    volume = np.abs(np.bincount(tri, np.einsum('ij,ij->i', P[F[:, 0]], np.cross(P[F[:, 1]], P[F[:, 2]])), n)) / 6
    out = []
    for name, ext, vol, e_tol, v_tol in shapes:
        for h in np.flatnonzero((verts > 8) & (np.abs(volume - vol) <= v_tol * vol)):       # the volume first: it is cheap and rules out most pieces
            mask = tri == h
            if np.all(np.abs(_pca_extents(P, F[mask]) - ext) <= e_tol):
                out.append((name, mask))
    return out


class _Mesh:
    """A mesh found in a page's data: the dict that holds its encoded geometry, the names it goes by, where it is, the key of the
    page's LOOK table that named it, and (in a lineup page, where one shape serves many parts) the parts that use it."""
    def __init__(self, node, names, path, look=None, users=None):
        self.node, self.names, self.path, self.look, self.users = node, names, path, look, users


def _mesh_names(node, key, look):
    if isinstance(node.get('label'), str):
        return [node['label']], None
    if look and key in look:
        return [look[key]], key
    return ([KEY_NAMES[key]] if key in KEY_NAMES else []), None


def _lineup(value):
    """{geo index: the parts that use it} for a lineup page (lists geo, txt and designs), else None."""
    if not (isinstance(value, dict) and all(isinstance(value.get(k), list) for k in ('geo', 'txt', 'designs'))):
        return None
    users, todo = {}, [value['designs']]
    while todo:
        x = todo.pop()
        if isinstance(x, dict):
            if isinstance(x.get('g'), int) and isinstance(x.get('l'), int):
                users.setdefault(x['g'], []).append(x)
            else:
                todo += list(x.values())
        elif isinstance(x, list):
            todo += x
    return users


def _is_mesh(x) -> bool:
    return isinstance(x.get('v'), str) and isinstance(x.get('f'), str)


class _Block:
    """One JSON value assigned to a name in a script: where it sits in the text, the meshes in it, and the dicts that carry 3D data
    in some other encoding ((path, their own strings): opaque)."""
    def __init__(self, start, end, value, look):
        self.start, self.end, self.value = start, end, value
        self.meshes, self.opaque, self.users = [], [], _lineup(value)
        if self.users is not None:
            txt = value['txt']
            for i, node in enumerate(value['geo']):
                if isinstance(node, dict) and _is_mesh(node):
                    names = [txt[p['l']] for p in self.users.get(i, []) if 0 <= p['l'] < len(txt) and isinstance(txt[p['l']], str)]
                    self.meshes.append(_Mesh(node, names, '/geo[%d]' % i, users=self.users.get(i, [])))
        todo = [(value, '', None)]
        while todo:
            x, path, key = todo.pop()
            if isinstance(x, dict):
                if _is_mesh(x):
                    if not (self.users is not None and path.startswith('/geo[')):
                        names, lk = _mesh_names(x, key, look); self.meshes.append(_Mesh(x, names, path, lk))
                    continue
                if _carries_mesh(x):
                    self.opaque.append((path, [v for v in x.values() if isinstance(v, str) and len(v) < 200]))
                todo += [(v, '%s/%s' % (path, k), k) for k, v in x.items()]
            elif isinstance(x, list):
                todo += [(v, '%s[%d]' % (path, i), None) for i, v in enumerate(x)]


class _Scan:
    def __init__(self, blocks, loose, mesh_file=False):
        self.blocks, self.loose, self.mesh_file = blocks, loose, mesh_file


def _statements(body):
    """[(start, end, value)] for the leading `name = <JSON>;` statements of a script: the offsets of each JSON value."""
    out, pos, dec = [], 0, json.JSONDecoder()
    while True:
        m = _ASSIGN.match(body, pos)
        if not m:
            return out
        try:
            value, end = dec.raw_decode(body, m.end())
        except ValueError:
            return out
        out.append((m.end(), end, value)); pos = _SEMI.match(body, end).end()


def _scan(text, ext='.html'):
    """The 3D data in a page or a data file: its JSON blocks (parsed) and the rest of its scripts (loose text)."""
    ext = ext.lower()
    if ext in _MESH_EXT:
        return _Scan([], [text], mesh_file=True)
    bodies = []
    if ext in ('.html', '.htm'):
        bodies = [(m.start(2), m.group(2)) for m in _SCRIPT.finditer(text) if not re.search(r'\bsrc\s*=', m.group(1), re.I)]
    elif ext in _SCRIPT_EXT:
        bodies = [(0, text)]
    parsed, loose = [], []
    for off, body in bodies:
        st = _statements(body)
        if not st and ext == '.json':
            try:
                st = [(0, len(body), json.loads(body))]
            except ValueError:
                pass
        pos = 0
        for s, e, value in st:
            loose.append(body[pos:s]); pos = e; parsed.append((off + s, off + e, value))
        loose.append(body[pos:])
    look = {}                                                           # the labels a script keeps for the meshes of another
    for t in loose:
        for m in _LOOK.finditer(t) if len(t) < 200000 else ():
            look.setdefault(m.group('key'), m.group('label'))
    return _Scan([_Block(s, e, v, look) for s, e, v in parsed], loose)


# ---- the gate

def geometry_problems(text: str, ext: str = '.html', licence: bool = False) -> list:
    """What is wrong with the 3D data in one published file: an uncleared part (an UNCLEARED name, or a piece the size of an MG90S
    or its horn) that is not a box; 3D data in a format this cannot read that shows an uncleared name; credited parts (CREDITED)
    when the item has no licence. Words in prose do not count: only meshes, and data that carries meshes."""
    sc = _scan(text, ext); seen, kinds = {}, []
    credit = lambda ks: kinds.extend(k for k in ks if k not in kinds)
    for blk in sc.blocks:
        for m in blk.meshes:
            names = [n for n in m.names if isinstance(n, str)]
            for n in names:
                credit(credited_kinds(n))
            hit = next((n for n in names if is_uncleared(n)), None)
            d = _decode(m.node)
            if hit:
                if d is None:
                    seen.setdefault(('read', hit), [m.path, 0, 0])[1] += 1
                elif not _is_box(*d):
                    seen.setdefault(('box', hit), [m.path, 0, len(np.unique(d[0][np.unique(d[1])], axis=0))])[1] += 1
            elif d is not None:
                for what, _ in _fused(*d):
                    seen.setdefault(('fused', names[0] if names else m.path, what), [m.path, 0, 0])[1] += 1
        for path, strings in blk.opaque:
            for s in strings:
                credit(credited_kinds(s))
                if is_uncleared(s):
                    seen.setdefault(('opaque', s), [path or 'the page', 0, 0])[1] += 1
    for t in sc.loose:
        if sc.mesh_file or _has_payload(t):
            t = _NUMS.sub(' ', _B64.sub(' ', t))
            for rx in UNCLEARED:
                mm = rx.search(t)
                if mm:
                    seen.setdefault(('opaque', mm.group(0)), ['the file' if sc.mesh_file else 'a script', 0, 0])[1] += 1
            credit(k for k, rxs in CREDITED.items() if any(rx.search(t) for rx in rxs))
    probs = []
    for key, (path, n, nv) in seen.items():
        also = f', {n} of them' if n > 1 else ''
        if key[0] == 'box':
            probs.append(f"mesh '{key[1]}' ({path}{also}) is an uncleared part and not a box ({nv} vertices)")
        elif key[0] == 'read':
            probs.append(f"mesh '{key[1]}' ({path}{also}) is an uncleared part and could not be read")
        elif key[0] == 'fused':
            probs.append(f"mesh '{key[1]}' ({path}{also}) holds a part the size of the {key[2]} that is not a box")
        else:
            probs.append(f"3D data ({path}) is in a format this cannot read and shows '{key[1]}'")
    if kinds and not licence:
        probs.append(f"shows parts that need a credit ({', '.join(kinds)}), and its item has no licence field")
    return probs


# ---- stand-ins

def _style(original: str, value) -> dict:
    """The json.dumps options under which `value` writes `original` back unchanged (the generators' own), else the defaults."""
    for kw in ({}, {'separators': (',', ':')}, {'ensure_ascii': False}, {'separators': (',', ':'), 'ensure_ascii': False}):
        if json.dumps(value, **kw) == original:
            return kw
    return {}


def _stand_in_mesh(node, names, pats):
    """Swap the mesh for a box of its bounds when a pattern matches one of its names, else swap only its pieces that are an uncleared
    part's size. A box already is one and stays as it is. Returns the text to add to its label ('' if nothing changed)."""
    d = _decode(node)
    if d is None or not d[1].size:
        return ''
    V, F = d
    if any(p.search(n) for n in names for p in pats):
        if _is_box(V, F):
            return ''
        _store(node, *_box_of(V, F))
        return SUFFIX
    parts = _fused(V, F)
    if not parts:
        return ''
    drop = np.zeros(len(F), bool); boxes = []
    for name, mask in parts:
        drop |= mask; boxes.append(_box_of(V, F[mask]))
    Fk = F[~drop]; used = np.unique(Fk); remap = np.full(len(V), -1, np.int64); remap[used] = np.arange(len(used))
    V2, F2 = V[used], remap[Fk]
    for bv, bf in boxes:
        F2 = np.vstack([F2, bf + len(V2)]); V2 = np.vstack([V2, bv])
    _store(node, V2, F2)
    return ' (%s shown as a stand-in box)' % parts[0][0].split()[-1]       # 'servo' or 'horn': the label must not match an uncleared name


def _stand_in_lineup(blk: _Block, pats) -> bool:
    """A lineup page: parts name the shapes. A shape only matching parts use becomes a box; one that others use too is copied, and
    the matching parts are pointed at the copy."""
    txt, geo, changed = blk.value['txt'], blk.value['geo'], False
    at = lambda s: txt.index(s) if s in txt else (txt.append(s) or len(txt) - 1)
    label = lambda p: txt[p['l']] if 0 <= p['l'] < len(txt) and isinstance(txt[p['l']], str) else ''
    for m in [m for m in blk.meshes if m.path.startswith('/geo[')]:
        hit = [p for p in m.users if any(r.search(label(p)) for r in pats)]
        if hit:
            d = _decode(m.node)
            if d is None or not d[1].size or _is_box(*d):
                continue
            node = m.node if len(hit) == len(m.users) else dict(m.node)
            _store(node, *_box_of(*d))
            if node is not m.node:
                geo.append(node)
                for p in hit:
                    p['g'] = len(geo) - 1
            for p in hit:
                p['l'] = at(label(p) + SUFFIX)
            changed = True
        else:
            add = _stand_in_mesh(m.node, [], pats)
            if add:
                for p in m.users:
                    p['l'] = at(label(p) + add)
                changed = True
    return changed


def standin_page(text: str, patterns, ext: str = '.html') -> str:
    """The page with a box in place of each mesh whose label matches one of `patterns` (regexes, any case), and in place of each piece
    of any mesh that is the size of an uncleared part (the MG90S fused into a base). A box has the bounds of what it replaces, 8
    vertices and 12 triangles, and its label gets ' (stand-in box)'. Everything else in the page stays as it was."""
    pats = [re.compile(p, re.I) for p in patterns]
    sc = _scan(text, ext); edits, relabel = [], set()
    for blk in sc.blocks:
        if not blk.meshes:
            continue
        kw = _style(text[blk.start:blk.end], blk.value)
        changed = _stand_in_lineup(blk, pats) if blk.users is not None else False
        for m in blk.meshes:
            if blk.users is not None and m.path.startswith('/geo['):
                continue
            add = _stand_in_mesh(m.node, m.names, pats)
            if add:
                changed = True
                if isinstance(m.node.get('label'), str):
                    m.node['label'] += add
                if m.look:
                    relabel.add(m.look)
        if changed:
            edits.append((blk.start, blk.end, json.dumps(blk.value, **kw)))
    for s, e, new in sorted(edits, reverse=True):
        text = text[:s] + new + text[e:]
    for key in relabel:                                                  # labels kept in the page's script (plus-sleeve's LOOK table)
        text = re.sub(r"""(\b%s\s*:\s*\[\s*)(['"])((?:(?!\2)[^\\\n]|\\.)*)\2""" % re.escape(key),
                      lambda mm: mm.group(1) + mm.group(2) + mm.group(3) + SUFFIX + mm.group(2), text, count=1)
    return text



def _third_party_problems(item, files, out):
    """The geometry gate (geometry_problems) over every published file that can carry 3D data; a file named like a part counts too."""
    licence, probs = bool(item.get('licence')), []
    for p in files:
        rel = os.path.relpath(p, out).replace(os.sep, '/'); name = os.path.basename(p); ext = os.path.splitext(p)[1].lower()
        if is_uncleared(name):
            probs.append(f"{rel} is named like a part whose model has no recorded licence")
        elif credited_kinds(name) and not licence:
            probs.append(f"{rel} is named like a credited part ({', '.join(credited_kinds(name))}), and item '{item['id']}' has no licence field")
        if ext in _GATE_EXT:
            probs += [f'{rel}: {m}' for m in geometry_problems(_read(p), ext, licence)]
    return probs


def _standin_patterns(item):
    """The item's `standin` as a list of regex strings, or a ValueError saying what is wrong with it."""
    pats = item['standin']
    if not isinstance(pats, list) or not all(isinstance(p, str) and p for p in pats):
        raise ValueError('its standin must be a list of non-empty regular expressions')
    for p in pats:
        try:
            re.compile(p)
        except re.error as e:
            raise ValueError(f'its standin pattern {p!r} is not a regular expression ({e})')
    return pats


def _bad_href(href):
    """Why `href` cannot be a link card's address, else None: it must be a plain https URL with a host, no user name or password,
    and not a private claude.ai artifact link."""
    if not isinstance(href, str) or not href:
        return 'is missing'
    if re.search(r'''[\s"'<>`\\\x00-\x1f]''', href):
        return 'has a space, quote, bracket or control character in it'
    try:
        u = urllib.parse.urlsplit(href); host = u.hostname
    except ValueError:
        return 'is not a valid URL'
    if u.scheme.lower() != 'https':
        return 'is not an https URL'
    if not host:
        return 'has no host'
    if u.username is not None or u.password is not None:
        return 'has a user name or password in it'
    if PRIVATE.search(href):
        return 'is a private claude.ai artifact link'
    return None


# ---------------------------------------------------------------- video, the output folder

def copy_video(src: str, dst: str) -> bool:
    """Copy a clip to `dst`. An MP4 is remuxed with its index first (-movflags +faststart) so it plays before it has all
    downloaded; without ffmpeg, or if it fails, the file is copied as it is. True when it was remuxed."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if src.lower().endswith('.mp4'):
        try:
            r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-c', 'copy', '-movflags', '+faststart', dst],
                               capture_output=True, stdin=subprocess.DEVNULL, timeout=600)
            if r.returncode == 0 and os.path.getsize(dst) > 0:
                return True
        except (OSError, subprocess.SubprocessError):
            pass
    shutil.copyfile(src, dst)
    return False


def _shown(path):
    """A path for messages: relative to the repo when it is inside it, else just its last part (no home folder in the output)."""
    try:
        rel = os.path.relpath(path, ROOT)
    except ValueError:
        return os.path.basename(path)
    return os.path.basename(path) if rel.startswith('..') else rel


def _prepare_out(out):
    """Start from an empty `out`. An existing folder is deleted only when it is empty or carries MARKER (build() wrote it):
    pointing the build at a folder of someone's files must not wipe it."""
    if os.path.lexists(out):
        if not os.path.isdir(out) or (os.listdir(out) and MARKER not in os.listdir(out)):
            raise RuntimeError(f'{_shown(out)} is not empty and holds no {MARKER} marker, so the build will not delete it; empty it or choose another folder')
        shutil.rmtree(out)
    os.makedirs(out); _write(os.path.join(out, MARKER), ''); _write(os.path.join(out, '.nojekyll'), '')


def build(manifest, root=ROOT, out=OUT, allow_missing=False, limit_mb=LIMIT_MB):
    _prepare_out(out)
    links = manifest.get('link_pages') or {}
    items = [it for s in manifest['sections'] for it in s['items']]
    built_pages = {it['id'] for it in items if it['kind'] == 'page' and not it.get('hold') and not it.get('dir')       # ids a link may point at: a page in pages/
                   and os.path.exists(os.path.join(root, it['src']))}
    cards, missing, held, problems, n = {}, [], [], [], 0
    for s in manifest['sections']:
        for it in s['items']:
            if it.get('hold'):                                       # a decision for the owner is pending: no files, no card
                held.append((it['id'], it['hold'])); continue
            if it['kind'] == 'link':                                 # an address: nothing to copy
                why = _bad_href(it.get('href'))
                if why:
                    problems.append(f"item '{it['id']}': its href {why}"); continue
                thumb = None
                if it.get('thumb'):
                    if os.path.exists(os.path.join(root, it['thumb'])):
                        thumbnail(os.path.join(root, it['thumb']), os.path.join(out, 'thumbs', it['id'] + '.jpg')); thumb = f'thumbs/{it["id"]}.jpg'
                    else:
                        problems.append(f"item '{it['id']}': its thumb {it['thumb']} is not on disk")
                cards[it['id']] = card(it, it['href'], thumb); n += 1; continue
            src = os.path.join(root, it['src'])
            if not os.path.exists(src):
                missing.append((it['id'], it['make'])); continue
            if it.get('thumb') and not os.path.exists(os.path.join(root, it['thumb'])):
                problems.append(f"item '{it['id']}': its thumb {it['thumb']} is not on disk")
            ext = os.path.splitext(src)[1].lower(); th = it.get('thumb') or (it['src'] if it['kind'] == 'figure' else None)
            if it['kind'] == 'page':
                standin = None
                if 'standin' in it:
                    try:
                        standin = _standin_patterns(it)
                    except ValueError as e:
                        problems.append(f"item '{it['id']}': {e}")
                if it.get('dir'):                                    # a page that loads its sibling files
                    dst_dir = os.path.join(out, 'pages', it['id']); shutil.copytree(os.path.dirname(src), dst_dir)
                    dst = os.path.join(dst_dir, os.path.basename(src)); href = f'pages/{it["id"]}/{os.path.basename(src)}'; back = '../../index.html'
                    published = [os.path.join(b, f) for b, _, fs in os.walk(dst_dir) for f in fs]
                else:
                    dst = os.path.join(out, 'pages', it['id'] + '.html'); href = f'pages/{it["id"]}.html'; back = '../index.html'
                    os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copyfile(src, dst); published = [dst]
                page = rewrite_links(strip_all(_read(dst)), links, built_pages)    # with no map, an emptied link object still becomes null
                if standin is not None:
                    page = standin_page(page, standin)
                _write(dst, wrap_page(page, back, credit=it.get('licence'), note=PAGE_NOTE))
                for p in published if standin is not None else ():           # the files a page loads get their stand-ins too
                    ext = os.path.splitext(p)[1].lower()
                    if p != dst and ext in ('.html', '.htm') + _SCRIPT_EXT:
                        _write(p, standin_page(_read(p), standin, ext))
                problems += _third_party_problems(it, published, out)
            elif it['kind'] == 'video':
                copy_video(src, os.path.join(out, 'media', it['id'] + ext))
                poster = None
                if it.get('thumb') and os.path.exists(os.path.join(root, it['thumb'])):
                    pext = os.path.splitext(it['thumb'])[1].lower(); poster = f'../media/{it["id"]}{pext}'
                    shutil.copyfile(os.path.join(root, it['thumb']), os.path.join(out, 'media', it['id'] + pext))
                os.makedirs(os.path.join(out, 'pages'), exist_ok=True)
                _write(os.path.join(out, 'pages', it['id'] + '.html'),
                       wrap_page(video_page(it, f'../media/{it["id"]}{ext}', poster), '../index.html', credit=it.get('licence')))
                href = f'pages/{it["id"]}.html'
            else:
                dst = os.path.join(out, 'media', it['id'] + ext); os.makedirs(os.path.dirname(dst), exist_ok=True)
                if it.get('rotate'):
                    rotated_copy(src, dst, it['rotate'])
                else:
                    shutil.copyfile(src, dst)
                href = f'media/{it["id"]}{ext}'
            thumb = None
            if th and os.path.exists(os.path.join(root, th)):
                turn = it.get('rotate', 0) if th == it['src'] else 0          # a separate thumb is drawn the right way up
                thumbnail(os.path.join(root, th), os.path.join(out, 'thumbs', it['id'] + '.jpg'), rotate=turn); thumb = f'thumbs/{it["id"]}.jpg'
            cards[it['id']] = card(it, href, thumb); n += 1
    _write(os.path.join(out, 'index.html'), index_html(manifest, cards))
    return dict(items=n, missing=missing, held=held, problems=problems + gates(out, limit_mb))


def main(argv=None):
    ap = argparse.ArgumentParser(description='Build the gallery into site/out.')
    ap.add_argument('--allow-missing', action='store_true', help='build without the entries whose source is not on disk')
    a = ap.parse_args(argv)
    with open(MANIFEST, encoding='utf-8') as fh:
        manifest = json.load(fh)
    try:
        r = build(manifest, ROOT, OUT, allow_missing=a.allow_missing)
    except RuntimeError as e:
        print(f'refusing: {e}')
        return 1
    for i, mk in r['missing']:
        print(f'missing {i}: rebuild with  {mk}')
    for i, why in r['held']:
        print(f'held {i}: {why}')
    for p in r['problems']:
        print('PROBLEM', p)
    print(f"{r['items']} items in {_shown(OUT)}; {len(r['missing'])} missing; {len(r['held'])} held; {len(r['problems'])} problems")
    return 1 if r['problems'] or (r['missing'] and not a.allow_missing) else 0


if __name__ == '__main__':
    sys.exit(main())
