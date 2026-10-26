"""Build the Scorpion gallery: copy the manifest's pages, figures and video into site/out, give every page a document
head and a way back, strip private links, make thumbnails, write index.html, then refuse the build if a local link
is broken, a file is too big, or tools/leakscan.py finds anything.

    python tools/gallery/build.py                 # -> site/out/ (exit 1 on any failed gate)
    python tools/gallery/build.py --allow-missing # build without entries whose source isn't on disk (listed)

A manifest item may carry "hold": "<reason>" (not built, listed) or, when its page shows third-party parts, "licence": "<text>".
"""
import os, re, sys, json, html, shutil, argparse, datetime, subprocess, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'site', 'out'); MANIFEST = os.path.join(HERE, 'manifest.json')
CDN = ('https://cdnjs.cloudflare.com/', 'https://cdn.jsdelivr.net/', 'https://unpkg.com/', 'https://fonts.googleapis.com/', 'https://fonts.gstatic.com/')
ALLOWED_HOSTS = tuple(urllib.parse.urlsplit(u).hostname for u in CDN)     # the only hosts a page may load anything from
MARKER = '.gallery-build'                                                  # build() writes it; it only deletes an out folder that has it

# Labels and file names of parts that come from other people's models (FPV-Rover V2.0, an Adafruit-layout PCA9685 board, the
# Raspberry Pi 5, an MG90S servo). A published page that shows one needs its manifest item to carry a "licence" field, or a "hold".
THIRD_PARTY = [re.compile(p, re.I) for p in (r'outer[-_ ]?frame', r'sprocket', r'PCA9685', r'MG90S', r'raspberry[-_ ]?pi')]

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
BOM = chr(0xFEFF)                                              # U+FEFF, the byte-order mark some editors put first
LIMIT_MB, TOTAL_MB = 95.0, 900.0


_DOCTYPE = re.compile(r'<!doctype', re.I)
_OLD_BACK = re.compile(r'\n?<a data-gallery-back\b[^>]*>.*?</a>\n?', re.S)


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


def wrap_page(page: str, back: str) -> str:
    """Give the page a document head if it lacks a doctype, and exactly one fixed link back to `back` (a link from an
    earlier wrap is replaced, so wrapping twice gives the same page)."""
    out = page
    if not _has_doctype(out):
        out = HEAD + out.lstrip(BOM)
    if 'data-gallery-back' in out:
        out = _OLD_BACK.sub('', out)
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

KIND = {'page': '3D, drag to turn', 'figure': 'figure', 'video': 'video'}


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


def thumbnail(src, dst, width=640):
    from PIL import Image
    im = Image.open(src).convert('RGB'); h = round(im.height * width / im.width)
    os.makedirs(os.path.dirname(dst), exist_ok=True); im.resize((width, h)).save(dst, 'JPEG', quality=82)


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
            sec.append(f'<section><h2>{html.escape(s["name"])}</h2><div class="grid">{items}</div></section>')
    val = {'TITLE': html.escape(manifest['title']), 'INTRO': html.escape(manifest['intro']), 'SECTIONS': '\n'.join(sec),
           'BUILT': datetime.date.today().isoformat()}
    return _PLACEHOLDER.sub(lambda m: val[m.group(1)], t)               # one pass: a {{BUILT}} inside a caption stays as written


def card(item, href, thumb):
    bg = f' style="background-image:url({html.escape(thumb, quote=True)})"' if thumb else ''
    label = '' if thumb else html.escape(KIND[item['kind']])
    return (f'<a class="card" href="{html.escape(href, quote=True)}"><div class="thumb"{bg}>{label}</div><div class="meta">'
            f'<span class="kind">{KIND[item["kind"]]}</span><b>{html.escape(item["title"])}</b><span>{html.escape(item["caption"])}</span></div></a>')


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


# ---------------------------------------------------------------- third-party parts, video, the output folder

_TEXT_EXT = ('.html', '.htm', '.js', '.mjs', '.css', '.json', '.svg', '.txt', '.mtl', '.obj', '.gltf', '.xml', '.md')


def third_party(text: str) -> list:
    """The third-party part labels (THIRD_PARTY) found in `text`, lowercase, each once, in order of first appearance."""
    hits = {}
    for rx in THIRD_PARTY:
        m = rx.search(text)
        if m:
            hits.setdefault(m.group(0).lower(), m.start())
    return sorted(hits, key=hits.get)


def _third_party_problems(item, files, out):
    """One problem per published file of a page item whose name or text shows a third-party part, unless the item has a licence."""
    if item.get('licence'):
        return []
    probs = []
    for p in files:
        hits = third_party(os.path.basename(p))
        if p.lower().endswith(_TEXT_EXT):
            hits += [h for h in third_party(_read(p)) if h not in hits]
        if hits:
            rel = os.path.relpath(p, out).replace(os.sep, '/')
            probs.append(f"{rel} shows third-party parts ({', '.join(hits)}), and item '{item['id']}' has no licence field")
    return probs


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
            src = os.path.join(root, it['src'])
            if not os.path.exists(src):
                missing.append((it['id'], it['make'])); continue
            if it.get('thumb') and not os.path.exists(os.path.join(root, it['thumb'])):
                problems.append(f"item '{it['id']}': its thumb {it['thumb']} is not on disk")
            ext = os.path.splitext(src)[1].lower(); th = it.get('thumb') or (it['src'] if it['kind'] == 'figure' else None)
            if it['kind'] == 'page':
                if it.get('dir'):                                    # a page that loads its sibling files
                    dst_dir = os.path.join(out, 'pages', it['id']); shutil.copytree(os.path.dirname(src), dst_dir)
                    dst = os.path.join(dst_dir, os.path.basename(src)); href = f'pages/{it["id"]}/{os.path.basename(src)}'; back = '../../index.html'
                    published = [os.path.join(b, f) for b, _, fs in os.walk(dst_dir) for f in fs]
                else:
                    dst = os.path.join(out, 'pages', it['id'] + '.html'); href = f'pages/{it["id"]}.html'; back = '../index.html'
                    os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copyfile(src, dst); published = [dst]
                page = rewrite_links(strip_all(_read(dst)), links, built_pages)    # with no map, an emptied link object still becomes null
                _write(dst, wrap_page(page, back))
                problems += _third_party_problems(it, published, out)
            elif it['kind'] == 'video':
                copy_video(src, os.path.join(out, 'media', it['id'] + ext))
                poster = None
                if it.get('thumb') and os.path.exists(os.path.join(root, it['thumb'])):
                    pext = os.path.splitext(it['thumb'])[1].lower(); poster = f'../media/{it["id"]}{pext}'
                    shutil.copyfile(os.path.join(root, it['thumb']), os.path.join(out, 'media', it['id'] + pext))
                os.makedirs(os.path.join(out, 'pages'), exist_ok=True)
                _write(os.path.join(out, 'pages', it['id'] + '.html'),
                       wrap_page(video_page(it, f'../media/{it["id"]}{ext}', poster), '../index.html'))
                href = f'pages/{it["id"]}.html'
            else:
                dst = os.path.join(out, 'media', it['id'] + ext); os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(src, dst); href = f'media/{it["id"]}{ext}'
            thumb = None
            if th and os.path.exists(os.path.join(root, th)):
                thumbnail(os.path.join(root, th), os.path.join(out, 'thumbs', it['id'] + '.jpg')); thumb = f'thumbs/{it["id"]}.jpg'
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
