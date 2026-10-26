# tools/leakscan.py
"""Find what shouldn't leave this repo: credentials, tokens, personal emails, home-network addresses, local user
paths, private claude.ai links, and metadata in binaries, in a folder, in HEAD's tracked files, or in every commit.

    python tools/leakscan.py                  # tracked files at HEAD; exit 1 on any 'must' not allowed
    python tools/leakscan.py --history        # every blob reachable from every ref, plus commit authors and messages
    python tools/leakscan.py --path site/out  # any folder (the Pages site before it is published)
    python tools/leakscan.py --staged         # what the index adds or changes against HEAD (the pre-commit hook)
    python tools/leakscan.py --strict         # 'decide' findings fail too (the Pages gate)
    python tools/leakscan.py --report docs/audit/leak-report.md
    python tools/leakscan.py --allow FILE     # accepted findings from FILE instead of tools/leakscan_allow.txt

Values are always redacted. Accepted findings: tools/leakscan_allow.txt, one 'rule glob' per line.
"""
import os, re, sys, codecs, fnmatch, argparse, subprocess, base64, binascii, struct, zlib
from dataclasses import dataclass, field, replace

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ALLOW = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'leakscan_allow.txt')
PLACEHOLDERS = {'your-ssid', 'your-password', 'your_ssid', 'your_password', 'password', 'changeme', 'xxxx', '****', 'ssid', 'secret',
                'none', 'null', ''}
PLACEHOLDER_SHAPES = re.compile(r'<[^<>]*>|\$\{[^}]*\}|\$\w+|\*+|x{3,}')     # <your password>, ${VAR}, $VAR, ****, xxxxxxxx
# only a whole address is safe: 'digit@github.com' ends in 'git@github.com' but is not it
SAFE_EMAIL = re.compile(r'(noreply@anthropic\.com|@users\.noreply\.github\.com|@example\.(com|org))$|^git@github\.com$', re.I)
LONG_LINE = 2000                                   # base64 meshes: a longer line is read with its base64-like runs blanked out
# a run of 200 or more base64 characters (also hex): blanked in a long line. The lookbehind makes it start only where a run starts, so
# a run of 199 is passed over once, not again from each of its characters (else a line of 199-runs costs 200 steps a character).
_B64 = re.compile(r'(?<![A-Za-z0-9+/=])[A-Za-z0-9+/=]{200,}')


@dataclass
class Finding:
    rule: str
    grade: str
    path: str
    line: int
    value: str = field(repr=False)                 # never in a repr: a traceback or a log line must not leak it
    note: str
    commit: str = ''


# credential words; the name may carry a prefix or suffix (WIFI_PASSWORD, wifiPassword, db_passwd_old), so the match starts at the word.
# Suffixes and prefixes are capped at 64: an open-ended [\w-]* backtracks quadratically on a long line of 'passwordpassword...'.
_WORD = r'(?:ssid|password|passwd|pwd|psk|passphrase)'
# after the name: an optional [] (char ssid[]), a closing quote (a JSON key; \" when the JSON sits in a JS string), an optional
# ': type', then =, := or :
_AFTER_NAME = r'''(?:\[\d*\])?(?:\\*["'])?(?:\s*:\s*[\w.\[\],|]{1,64})?\s*(?::=|=|:)\s*'''
# quoted value ('..' or ".."; \".. \" inside a JS string); also pwd, and a bare PASS / WIFI_PASS (the archive's code.py has PASS next to SSID).
# scan_text drops a match whose name sits inside a string literal (a label: print("Password: ", end="")), see is_label().
QUOTED_KEY = re.compile(r'(?i)(?:' + _WORD + r'[\w-]{0,64}|(?<![\w-])(?:[\w-]{0,64}[_-])?pass(?![\w-]))' + _AFTER_NAME
                        + r'''(?P<esc>\\*)(?P<q>["'])(?P<v>(?:(?!(?P=q)).)*?)(?P=esc)(?P=q)''')
# One slash in any form tools/gallery/build.py's PRIVATE strips (its _SL): plain, JS-escaped (\/ or \\/), URL-encoded (%2F, also
# encoded again as %252F), the JSON unicode escape, or an HTML entity. A copy, not an import: tests/test_leakscan.py cross-checks it.
_SLASH = r'(?:/|\\+/|%(?:25)*2f|\\+u002f|&#0*47;|&#x0*2f;|&sol;)'
# where a host may start: not glued to a word before it (notclaude.ai, x.claude.ai); right after the JSON unicode escape of a slash; or
# right after a %2F (consumed, since it may be %252F or %25252F and a lookbehind cannot be that long)
_HOST_AT = r'(?:(?<![\w.-])|(?<=u002f)|%(?:25)*2f)'
# (rule, grade, regex, value group, note); value group 0 = the whole match
RULES = [
    ('credential', 'must', QUOTED_KEY, 'v',
     'a credential in source; replace with a placeholder and rotate it'),
    # unquoted, whole line only, so Python like `pwd = os.getcwd()` or `password = get_password()` stays quiet:
    # env style (WIFI_PASSWORD=...) ...
    ('credential', 'must', re.compile(r'''^\s*(?:export\s+)?[A-Z0-9_]{0,64}(?:PASSWORD|PASSWD|PSK|SSID|PASSPHRASE)[A-Z0-9_]{0,64}\s*=\s*((?:[^\s"'#]|(?<=\S)#)+)(?:\s+#.*)?\s*$'''),
     1, 'a credential in an env file; replace with a placeholder and rotate it'),
    # ... and YAML style (wifi_password: ...)
    ('credential', 'must', re.compile(r'''(?i)^\s*(?:-\s+)?[\w-]{0,64}(?:password|passwd|psk|passphrase)[\w-]{0,64}\s*:\s*((?:[^\s"'#{\[]|(?<=\S)#)+)(?:\s+#.*)?\s*$'''),
     1, 'a credential in a config file; replace with a placeholder and rotate it'),
    # Arduino macro: #define WIFI_PASSWORD "..." (no '=')
    ('credential', 'must', re.compile(r'(?i)^\s*#\s*define\s+(?:\w{0,64}?' + _WORD + r'|(?:\w{0,64}_)?pass)\w{0,64}\s+"([^"\n]*)"'), 1,
     'a credential in a macro; replace with a placeholder and rotate it'),
    # Arduino / CircuitPython positional: WiFi.begin("net", "pass"): the password argument, and the network name.
    # The first argument is a string, or an expression that starts with a non-space (so \s* before it can't overlap it: that was
    # quadratic) and may hold one level of parentheses: ssid.c_str()
    ('credential', 'must', re.compile(r'(?i)\bwifi\.(?:begin|softAP|radio\.connect)\(\s*(?:"[^"\n]*"|[^\s,()"\n](?:[^,()"\n]|\([^()\n]*\))*),\s*"([^"\n]*)"'), 1,
     'a Wi-Fi password in a call; replace with a placeholder and rotate it'),
    ('credential', 'must', re.compile(r'(?i)\bwifi\.(?:begin|softAP|radio\.connect)\(\s*"([^"\n]*)"'), 1,
     'a Wi-Fi name in a call; replace with a placeholder'),
    ('token', 'must', re.compile(r'\bgh[pousr]_[A-Za-z0-9]{36,}|\bgithub_pat_[A-Za-z0-9_]{22,}\b|\bsk-[A-Za-z0-9]{32,}\b|\b(?:AKIA|ASIA)[0-9A-Z]{16}\b'
                                 r'|\bsk-ant-[A-Za-z0-9_-]{40,}|\bsk-proj-[A-Za-z0-9_-]{32,}'      # Anthropic, OpenAI project keys
                                 r'|(?<![\w-])AIza[0-9A-Za-z_-]{35}(?![\w-])'                      # Google API key: exact length, since base64 rarely fits
                                 r'|\bxox[baprs]-[A-Za-z0-9-]{10,}\b|-----BEGIN [A-Z ]*PRIVATE KEY-----'), 0, 'a token or key'),
    # file names like icon@2x.png are not addresses. The match starts where a run of address characters starts (a lookbehind, not
    # \b): a long run with no '@' is read once, not again from every \b inside it.
    ('email', 'decide', re.compile(r'(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.(?!(?i:png|jpe?g|gif|svg|webp)\b)[A-Za-z]{2,}\b'), 0,
     'a personal email address'),
    ('private_ip', 'decide', re.compile(r'\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b'), 0,
     'an address on the home network'),
    # C:\Users\x, C:\\Users\\x (JSON, Python literals), C:/Users/x, /c/Users/x, /Users/x, /home/x (not inside a URL), OneDrive
    ('user_path', 'decide', re.compile(r'''(?i)[A-Z]:[\\/]+Users[\\/]+[^\\/\s"'<>]+|/c/Users/[^/\s"'<>]+|(?<![\w.])/Users/[^/\s"'<>]+'''
                                       r'''|(?<![\w.])/home/[^/\s"'<>]+|OneDrive'''), 0,
     'an absolute path with the user name'),
    # claude.ai/artifact/<id>, /code/artifact/<uuid>, /public/artifacts/<id> (and /artifacts/<id>) in any case, with or without a scheme
    # or www., the slashes in any form of _SLASH; the host must start the word (not notclaude.ai, not x.claude.ai). The path is
    # PRIVATE's: (code/)?(public/)?artifacts?/<id>. The value runs from claude.ai (or www.) on.
    ('artifact_link', 'decide', re.compile(r'(?i)' + _HOST_AT + r'(?P<link>(?:www\.)?claude\.ai' + _SLASH
                                           + r'(?:code' + _SLASH + r')?(?:public' + _SLASH + r')?artifacts?' + _SLASH + r'[A-Za-z0-9_-]+)'),
     'link', 'a private claude.ai link'),
]
# a long line is read with its base64-like runs blanked out (see scan_text), by every rule; token and credential also read the
# line whole, as before, since they are the rules that can sit inside such a run
TIGHT = {'token', 'credential'}


def redact(value: str) -> str:
    v = value.strip()
    return f'{v[:2]}…{v[-1:]} ({len(v)} chars)' if len(v) >= 8 else f'… ({len(v)} chars)'      # short values: show nothing


def placeholder(value: str) -> bool:
    v = value.strip().lower()
    return v in PLACEHOLDERS or bool(PLACEHOLDER_SHAPES.fullmatch(v))


_STRING_PREFIX = re.compile(r'(?:^|\W)[rbfu]{1,2}$', re.I)      # r'..', b'..', f'..', rb'..' open a string right after a letter


class Quotes:
    """Which string literal a position in one line is inside, read left to right (the cursor only moves forward, so a whole
    line costs one pass). An apostrophe in prose (it's, users') does not open a string; a quote right after r, b, f or u does."""
    def __init__(self, line: str):
        self.line, self.i, self.open = line, 0, ''

    def _opens(self, i: int) -> bool:
        c, line = self.line[i], self.line
        if c == '"' or i == 0 or not (line[i - 1].isalnum() or line[i - 1] == '_'):
            return True
        return bool(_STRING_PREFIX.search(line[max(0, i - 3):i]))

    def at(self, pos: int) -> str:
        """The quote character of the string that position pos is inside, or '' when it is outside every string."""
        line = self.line
        while self.i < pos:
            c = line[self.i]
            if self.open:
                if c == '\\':
                    self.i += 1
                elif c == self.open:
                    self.open = ''
            elif c in '"\'' and self._opens(self.i):
                self.open = c
            self.i += 1
        return self.open


def is_label(quotes: Quotes, m) -> bool:
    """True when a credential name is only words inside a string: print("Password: ", end=""), where the label's closing quote
    would read as the opening quote of a value. A quoted key ("wifi_password": "x") still counts: a quote follows the name."""
    enclosing = quotes.at(m.start())
    if not enclosing or m.group('q') != enclosing:    # the value uses the other quote: an assignment inside a string, not a label
        return False
    if len(m.group('esc')) % 2:                       # \" is an escaped quote (JSON inside a JS string), which cannot close the string
        return False
    text = m.group(0)
    end = re.match(r'[\w-]*', text).end()
    return text[end:end + 1] not in ('"', "'")


# \n, \r and \t written out as two characters (or \\n, in a string inside a string), as JSON and JS write a line break: the 'n' is a word
# character, so it hides what follows ('cwd\n/home/x'). The lookbehind starts a match only where a run of backslashes starts (linear).
_ESCAPES = re.compile(r'(?<!\\)\\+[nrt]')


def _readings(src: str) -> tuple:
    """The line as it is, and (when it holds such an escape) the same line with each escape blanked to spaces of the same width, so a
    match keeps its place. Both are read: C:\\Users\\nick holds a \\n that is a path separator and a name, and only the first sees it."""
    if '\\' not in src:
        return (src,)
    alt = _ESCAPES.sub(lambda m: ' ' * len(m.group()), src)
    return (src,) if alt == src else (src, alt)


def scan_text(path: str, text: str) -> list:
    out = []
    for n, line in enumerate(text.split('\n'), 1):         # not splitlines(): git counts '\n' only
        line = line.rstrip('\r')
        flat = _B64.sub(' ', line) if len(line) > LONG_LINE else line      # a long line's base64 would fire the address rules
        whole = _readings(line)
        blanked = _readings(flat) if flat is not line else whole
        for rule, grade, rx, g, note in RULES:
            kept = []                                        # where this rule found something in the line as it is
            for k, src in enumerate(whole if rule in TIGHT else blanked):
                quotes = Quotes(src) if rx is QUOTED_KEY else None
                pos = 0
                while True:                                  # finditer, except that a dropped label is retried one character on:
                    m = rx.search(src, pos)                  # its false match must not swallow a real credential after it
                    if not m:
                        break
                    pos = max(m.end(), m.start() + 1)
                    if quotes and is_label(quotes, m):
                        pos = m.start() + 1
                        continue
                    v = m.group(g)
                    if rule == 'credential' and placeholder(v):
                        continue
                    if rule == 'email' and SAFE_EMAIL.search(v):
                        continue
                    if k and any(a < m.end() and m.start() < b for a, b in kept):    # the blanked reading finds what the first did again
                        continue
                    if not k:
                        kept.append((m.start(), m.end()))
                    out.append(Finding(rule, grade, path, n, v, note))
    return out


import io, html, zipfile

IMAGES = ('.jpg', '.jpeg', '.png', '.heic', '.tif', '.tiff')
ZIPS = ('.f3d', '.3mf', '.fcstd', '.docx')
NOBODY = {'', 'author', 'unknown', 'none', 'open cascade', 'user'}


def nobody(v: str) -> bool:
    """A placeholder where a name should be, in any case and spacing: '', 'Author', 'Unknown', 'Open  CASCADE', and the same after a line break."""
    return ' '.join(v.split()).lower() in NOBODY


def _skip(h: str, i: int) -> int:
    """Past the spaces, line breaks and /* comments */ that STEP allows between any two tokens."""
    while i < len(h):
        if h[i].isspace():
            i += 1
        elif h.startswith('/*', i):
            k = h.find('*/', i + 2)
            i = len(h) if k < 0 else k + 2
        else:
            break
    return i


def step_names(h: str) -> list:
    """The quoted strings in FILE_NAME's author and organisation lists (the 3rd and 4th arguments), in any layout: a hand-written
    walk, so that a stray quote or a long run of them stays linear. '' inside a string is an escaped quote."""
    m = re.search('(?i)FILE_NAME', h)
    if not m:
        return []
    i = _skip(h, m.end())
    if h[i:i + 1] != '(':
        return []
    i, depth, args = i + 1, 0, [[]]
    while i < len(h):
        c = h[i]
        if c == "'":
            j, parts = i + 1, []
            while True:
                k = h.find("'", j)
                if k < 0:
                    k = len(h)
                    break
                if h.startswith("''", k):
                    parts.append(h[j:k + 1]); j = k + 2
                    continue
                break
            args[-1].append(''.join(parts) + h[j:k]); i = k + 1
        elif c == '/' and h.startswith('/*', i):
            i = _skip(h, i)
        elif c == '(':
            depth += 1; i += 1
        elif c == ')':
            if depth == 0:
                break
            depth -= 1; i += 1
        else:
            if c == ',' and depth == 0:
                args.append([])
            i += 1
    return [v for arg in args[2:4] for v in arg]


def scan_step(path: str, data: bytes) -> list:
    """A STEP file's header (up to the first ENDSEC;): the text rules over all of it, since the name field is often a local
    path; and FILE_NAME's author and organisation names. The DATA section is not read."""
    end = data.find(b'ENDSEC;')
    h = data[:end + 7 if end >= 0 else 20000].decode('latin-1')           # from the file's start, so line numbers match the file
    out = scan_text(path, h)
    for v in step_names(h):
        if not nobody(v):
            out.append(Finding('doc_author', 'decide', path, 0, ' '.join(v.split()), 'STEP header author or organisation'))
    return out


def _meta_text(path: str, text: str) -> list:
    """The text rules over text read out of a binary's metadata (a PNG chunk, an MP4 atom, an STL header). Such text has no lines
    of the file's, so the findings carry line 0."""
    return [replace(f, line=0) for f in scan_text(path, text)]


def _uniq(findings: list) -> list:
    """the findings without exact repeats (the same chunk read twice, by two routes), in order"""
    seen, out = set(), []
    for f in findings:
        k = (f.rule, f.path, f.line, f.value, f.note)
        if k not in seen:
            seen.add(k); out.append(f)
    return out


def _exif_findings(path: str, ex) -> list:
    """GPS, and the Artist and Copyright tags, of a Pillow Exif; raises when the block is damaged"""
    out = []
    if ex.get_ifd(0x8825):
        out.append(Finding('gps', 'must', path, 0, 'GPS block', 'a photo with its location; strip EXIF'))
    for tag, name in ((0x013B, 'Artist'), (0x8298, 'Copyright')):
        v = ex.get(tag)
        if v:
            out.append(Finding('doc_author', 'decide', path, 0, str(v), f'EXIF {name}'))
    return out


def scan_binary(path: str, data: bytes) -> list:
    ext = os.path.splitext(path)[1].lower(); out = []
    if ext in IMAGES:
        pre = scan_png(path, data) if ext == '.png' else []           # the chunks first: they are read even when Pillow cannot open the file
        try:
            from PIL import Image
        except ImportError:
            return pre + [unreadable(path, 'image not readable: Pillow is not installed; check metadata by hand')]
        try:
            found = _exif_findings(path, Image.open(io.BytesIO(data)).getexif())
        except Exception:                                   # HEIC without a plugin, corrupt or truncated bytes
            return pre + [unreadable(path, 'image not readable by Pillow; check metadata by hand')]
        out = _uniq(pre + found)
    elif ext in MP4S:
        out += scan_mp4(path, data)
    elif ext == '.pdf':
        for m in re.finditer(rb'/Author\s*\(([^)]*)\)', data):
            v = m.group(1).decode('latin-1').strip()
            if not nobody(v):
                out.append(Finding('doc_author', 'decide', path, 0, v, 'PDF author'))
    elif ext in ('.step', '.stp'):
        out += scan_step(path, data)
    elif ext in ZIPS:
        out += scan_zip(path, data)
    return out


PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
PNG_TEXT = 1 << 20                                  # bytes of one text chunk read, after unpacking: more is a gap, not a memory bomb
PNG_CHUNKS = 100_000
PNG_AUTHOR_KEYS = {'author', 'artist', 'copyright'}


def _inflate(b: bytes):
    """b unpacked, or None when it is damaged or unpacks to more than PNG_TEXT (a zip bomb)"""
    try:
        out = zlib.decompressobj().decompress(b, PNG_TEXT + 1)
    except zlib.error:
        return None
    return out if len(out) <= PNG_TEXT else None


def scan_png(path: str, data: bytes) -> list:
    """What a PNG's chunks say: tEXt, zTXt and iTXt (a name in Author, Artist or Copyright; the text through the text rules, so XMP
    with a path in it is found) and eXIf (GPS, Artist, Copyright). The image data is not read. Pillow's reading of the file is separate."""
    out, gaps, i, n = [], 0, 8, 0
    if not data.startswith(PNG_SIGNATURE):
        return out
    while i + 8 <= len(data) and n < PNG_CHUNKS:
        length, typ = int.from_bytes(data[i:i + 4], 'big'), data[i + 4:i + 8]
        a, n = i + 8, n + 1
        i = a + length + 4                                           # past the chunk and its CRC
        if typ not in (b'tEXt', b'zTXt', b'iTXt', b'eXIf'):
            continue
        if length > PNG_TEXT:
            gaps += 1
            continue
        body = data[a:a + length]
        key, _, rest = body.partition(b'\x00')
        key = key.decode('latin-1')
        if typ == b'eXIf':
            try:
                from PIL import Image
                ex = Image.Exif(); ex.load(body)
                out += _exif_findings(path, ex)
            except ImportError:
                pass                                                 # scan_binary reports a missing Pillow
            except Exception:
                gaps += 1
            continue
        if typ == b'tEXt':
            text = rest.decode('latin-1')
        elif typ == b'zTXt':
            raw = _inflate(rest[1:])                                 # one byte of compression method first
            text = None if raw is None else raw.decode('latin-1')
        else:                                                        # iTXt: flag, method, language, translated key, then the text
            flag, rest = rest[:1], rest[2:]
            rest = rest.partition(b'\x00')[2].partition(b'\x00')[2]
            raw = _inflate(rest) if flag == b'\x01' else rest
            text = None if raw is None else raw.decode('utf-8', 'replace')
        if text is None:
            gaps += 1
            continue
        out += _meta_text(path, f'{key}: {text}')
        if key.lower() in PNG_AUTHOR_KEYS and not nobody(text):
            out.append(Finding('doc_author', 'decide', path, 0, ' '.join(text.split()), f'PNG {key}'))
    if gaps:
        out.append(unreadable(path, f'PNG: {gaps} text chunk{"s" if gaps != 1 else ""} damaged or over {PNG_TEXT >> 20} MB, unscanned; check by hand'))
    if n >= PNG_CHUNKS and i + 8 <= len(data):                       # stopped at the cap with chunks left: the rest was never read
        out.append(unreadable(path, f'PNG: more than {PNG_CHUNKS} chunks, the rest unscanned; check by hand'))
    return out


MP4S = ('.mp4', '.m4v', '.m4a', '.mov', '.3gp', '.3g2')
MP4_BOXES = 100_000                                 # boxes walked in one file
MP4_DEPTH = 8                                       # moov > udta > meta > ilst > item > data is 5
MP4_ATOM = 1 << 20                                  # bytes of one atom read
MP4_READ = 16 << 20                                 # bytes of atoms read in one file
MP4_FIRST = {b'ftyp', b'moov', b'mdat', b'free', b'skip', b'wide', b'junk', b'pnot', b'uuid', b'meta', b'styp', b'sidx'}   # what a file may start with
MP4_INTO = {b'moov', b'trak', b'udta', b'meta', b'ilst'}                 # boxes whose children can hold metadata
MP4_GPS = {b'\xa9xyz', b'loci'}                     # QuickTime location, and 3GPP location information
MP4_AUTHOR = {b'\xa9ART', b'\xa9aut', b'\xa9wrt', b'\xa9cpy', b'auth', b'perf', b'aART', b'cprt'}
MP4_3GPP = {b'auth', b'perf', b'cprt', b'titl', b'dscp', b'albm', b'gnre', b'kywd'}    # version and flags, a language, a string
XMP_UUID = bytes.fromhex('be7acfcb97a942e89c71999491e3afac')            # the uuid box that holds XMP
_CONTROL = re.compile(r'[\x00-\x08\x0b-\x1f�]+')


def _atom_text(b: bytes) -> str:
    s = b.decode('utf-16', 'replace') if b[:2] in (codecs.BOM_UTF16_BE, codecs.BOM_UTF16_LE) else b.decode('utf-8', 'replace')
    return _CONTROL.sub('\n', s)


class _Mp4:
    """A walk over an MP4 / MOV file's boxes (ISO base media), looking only where metadata lives. Boxes are never trusted: sizes are
    checked against their container, the walk is bounded in boxes, depth and bytes read, and whatever it could not read is an
    'unreadable' finding of its own. mdat, the video, is skipped by size and never read."""
    def __init__(self, path, data):
        self.path, self.data, self.out, self.issues, self.keys = path, data, [], [], []
        self.boxes = self.read = 0
        self.has_gps = False

    def issue(self, why):
        if why not in self.issues:
            self.issues.append(why)

    def boxes_in(self, a, b, depth):
        """(type, uuid usertype, payload start, payload end) of each box in data[a:b]"""
        data, i = self.data, a
        while i < b:
            if b - i < 8:
                if any(data[i:b]):                                   # zero padding after the last box is fine
                    self.issue('a box header cut short')
                return
            size, typ = struct.unpack_from('>I4s', data, i)
            hdr, user = 8, b''
            if size == 1:                                            # a 64-bit size follows the type
                if b - i < 16:
                    self.issue('a box header cut short')
                    return
                size, hdr = struct.unpack_from('>Q', data, i + 8)[0], 16
            elif size == 0:                                          # runs to the end of the container
                size = b - i
            if typ == b'uuid':
                user, hdr = data[i + hdr:i + hdr + 16], hdr + 16
            if size < hdr:
                self.issue('a box smaller than its own header')
                return
            self.boxes += 1
            if self.boxes > MP4_BOXES:
                self.issue(f'more than {MP4_BOXES} boxes')
                return
            end = i + size
            if end > b:                                              # runs past its container or the file: take what is there
                if depth or typ in MP4_INTO or typ in (b'uuid', b'XMP_'):
                    self.issue('a metadata box runs past its container or the end of the file')
                end = b
            yield typ, user, i + hdr, end
            i = end

    def take(self, a, b):
        """payload bytes data[a:b], bounded per atom and per file"""
        n = min(b - a, MP4_ATOM)
        if b - a > MP4_ATOM:
            self.issue(f'an atom over {MP4_ATOM >> 20} MB, partly read')
        if self.read + n > MP4_READ:
            self.issue(f'more than {MP4_READ >> 20} MB of atoms')
            return b''
        self.read += n
        return self.data[a:a + n]

    def gps(self):
        if not self.has_gps:
            self.has_gps = True
            self.out.append(Finding('gps', 'must', self.path, 0, 'GPS location', 'a video with its location; strip the metadata'))

    def text(self, s):
        self.out += _meta_text(self.path, s)

    def author(self, s, note):
        v = ' '.join(s.split())
        if not nobody(v):
            self.out.append(Finding('doc_author', 'decide', self.path, 0, v, note))

    def walk(self, a, b, depth, parent):
        if depth > MP4_DEPTH:
            self.issue('boxes nested too deep')
            return
        for typ, user, pa, pb in self.boxes_in(a, b, depth):
            if typ in MP4_INTO:
                if typ == b'meta' and self.data[pa:pa + 4] == b'\x00\x00\x00\x00':       # ISO meta is a full box; QuickTime's is not
                    pa += 4
                self.walk(pa, pb, depth + 1, typ)
            elif parent == b'meta' and typ == b'keys':
                self.read_keys(pa, pb)
            elif parent == b'meta' and typ == b'xml ':
                self.text(_atom_text(self.take(pa, pb)))
            elif parent == b'ilst':
                self.item(typ, pa, pb, depth)
            elif typ == b'uuid':
                if user == XMP_UUID:
                    self.text(_atom_text(self.take(pa, pb)))
            elif parent == b'udta':
                self.user_data(typ, pa, pb)

    def read_keys(self, a, b):
        """the key names of a QuickTime 'keys' box: version and flags, a count, then size, namespace and name for each"""
        d, i, self.keys = self.data, a + 8, []
        for _ in range(min(int.from_bytes(d[a + 4:a + 8], 'big'), 10_000)):
            size = int.from_bytes(d[i:i + 4], 'big')
            if size < 8 or i + size > b:
                self.issue('a keys box cut short')
                return
            self.keys.append(d[i + 8:i + size].decode('utf-8', 'replace'))
            i += size

    def item(self, typ, a, b, depth):
        """an ilst item: its value is in a 'data' child (version and flags, a locale, then the value). An item named by a number is
        the key of that index in the 'keys' box."""
        idx = int.from_bytes(typ, 'big') if typ[:1] == b'\x00' else 0
        name = self.keys[idx - 1] if 1 <= idx <= len(self.keys) else ''
        for t, _, pa, pb in self.boxes_in(a, b, depth + 1):
            if t != b'data' or pb - pa < 8:
                continue
            kind, value = int.from_bytes(self.data[pa + 1:pa + 4], 'big'), self.take(pa + 8, pb)
            if typ in MP4_GPS or 'location' in name.lower():
                if value:
                    self.gps()
            if kind not in (1, 2):                                   # UTF-8 or UTF-16 text; the rest (cover art, numbers) is not text
                break
            s = _atom_text(value) if kind == 1 else value.decode('utf-16-be', 'replace')
            if typ in MP4_AUTHOR or name.rsplit('.', 1)[-1].lower() in PNG_AUTHOR_KEYS:
                self.author(s, f'MP4 {(name or typ.decode("latin-1")).strip()}')
            self.text(s)
            break

    def user_data(self, typ, a, b):
        if typ in MP4_GPS:
            if b > a:
                self.gps()
            return
        payload = self.take(a, b)
        # QuickTime text atoms start with a length and a language, 3GPP strings with version and flags and a language
        body = payload[4:] if typ[:1] == b'\xa9' else payload[6:] if typ in MP4_3GPP else payload
        s = _atom_text(body)
        if typ in MP4_AUTHOR:
            self.author(s, f'MP4 {typ.decode("latin-1")}')
        self.text(s)

    def result(self):
        if self.data[4:8] not in MP4_FIRST:
            self.issue('not an MP4 or MOV file')
        else:
            self.walk(0, len(self.data), 0, b'')
        if self.issues:
            self.out.append(unreadable(self.path, f'MP4 or MOV: {"; ".join(self.issues)}; metadata not fully read, check by hand'))
        return self.out


def scan_mp4(path: str, data: bytes) -> list:
    return _Mp4(path, data).result()


# the payload may have its slashes written \/ (JSON written by PHP, for one); the two parts cannot match the same text, so it stays linear
_DATA_URI = re.compile(r'data:image\\*/(jpe?g|png);base64,((?:[A-Za-z0-9+/]|\\/)[A-Za-z0-9+/]*(?:\\/[A-Za-z0-9+/]*)*)', re.I)


def scan_data_uris(path: str, text: str) -> list:
    """Each data:image/jpeg or png base64 payload in a text file, decoded and read as the image it is. Findings are reported at
    '<path>!data-uri-<n>', n counting the data URIs in the file from 1."""
    out, seen = [], {}
    for n, m in enumerate(_DATA_URI.finditer(text), 1):
        where = f'{path}!data-uri-{n}'
        payload = m.group(2).replace('\\/', '/')
        ext = '.png' if m.group(1).lower() == 'png' else '.jpg'
        if (ext, payload) not in seen:
            if len(payload) > MAX_BLOB * 4 // 3:
                seen[ext, payload] = [unreadable(where, f'data URI over {MAX_BLOB / 1e6:g} MB, unscanned')]
            else:
                try:
                    raw = base64.b64decode(payload + '=' * (-len(payload) % 4))
                except (binascii.Error, ValueError):
                    seen[ext, payload] = [unreadable(where, 'data URI is not valid base64; check by hand')]
                else:
                    seen[ext, payload] = scan_binary('data-uri' + ext, raw)
        out += [replace(f, path=where) for f in seen[ext, payload]]
    return out


TEXT_MEMBERS = ('.xml', '.json', '.txt', '.dat', '.model', '.rels')      # members whose text the rules read
MEMBER_CAP = 64 * 1024 * 1024                                            # uncompressed bytes: FreeCAD's Document.xml alone is 7 MB
ZIP_METHODS = {93: 'zstd', 95: 'xz', 9: 'deflate64', 98: 'ppmd'}         # zip methods Python 3.10's zipfile cannot decompress


def unreadable(path: str, note: str) -> Finding:
    """Something a scan could not look at is a finding of its own: a gate that skips quietly passes what it never saw."""
    return Finding('unreadable', 'decide', path, 0, '', note)


def _members(n: int, why: str) -> str:
    """'3 members use zstd compression', '1 member is encrypted'"""
    verb, _, rest = why.partition(' ')
    return f'{n} member{"s" if n != 1 else ""} {verb if n != 1 else {"use": "uses", "are": "is"}[verb]} {rest}'


# Who made the file, by archive member: (test on the lower-cased member name, regex, value group, note). A tag's text may be CDATA.
_TEXT = r'\s*((?:<!\[CDATA\[.*?\]\]>|[^<])*)'
AUTHORS = [
    (lambda n: n.endswith('.model'),                                                   # 3MF: <metadata name="Designer">..</metadata>
     re.compile(r"""(?is)<metadata\b[^>]*?\bname\s*=\s*["']Designer["'][^>]*(?<!/)>""" + _TEXT + r'</metadata\s*>'), 1, '3MF Designer'),
    (lambda n: n == 'docprops/core.xml',                                               # docx: dc:creator and cp:lastModifiedBy
     re.compile(r'(?is)<(?:\w+:)?creator\b[^>]*(?<!/)>' + _TEXT + r'</(?:\w+:)?creator\s*>'), 1, 'docx creator'),
    (lambda n: n == 'docprops/core.xml',
     re.compile(r'(?is)<(?:\w+:)?lastModifiedBy\b[^>]*(?<!/)>' + _TEXT + r'</(?:\w+:)?lastModifiedBy\s*>'), 1, 'docx last modified by'),
    (lambda n: n == 'document.xml',                                                    # FreeCAD: <Property name="CreatedBy"..><String value=".."/>
     re.compile(r'<Property\s+name="(CreatedBy|LastModifiedBy|Company)"[^>]*>\s*<String\s+value="([^"]*)"'), 2, 'FCStd {0}'),
]


def xml_text(v: str) -> str:
    v = v.strip()
    if v.startswith('<![CDATA[') and v.endswith(']]>'):                                # CDATA is literal, not escaped
        return v[9:-3].strip()
    return html.unescape(v).strip()


def zip_authors(name: str, text: str) -> list:
    """(value, line, note) for each real name in the member's author fields."""
    out = []
    for test, rx, g, note in AUTHORS:
        if not test(name.lower()):
            continue
        for m in rx.finditer(text):
            v = xml_text(m.group(g))
            if not nobody(v):
                out.append((v, text.count('\n', 0, m.start()) + 1, note.format(*m.groups())))      # 'FCStd {0}' -> 'FCStd CreatedBy'
    return out


def scan_zip(path: str, data: bytes) -> list:
    out, failed, big = [], {}, []                           # failed: why a member could not be read -> how many; big: over the cap
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except Exception:
        return [unreadable(path, 'not a readable zip archive (corrupt or truncated); check by hand')]
    with z:
        for info in z.infolist():
            if not info.filename.lower().endswith(TEXT_MEMBERS):
                continue
            if info.file_size > MEMBER_CAP:
                big.append(info.filename)
                continue
            try:
                text = z.read(info).decode('utf-8', 'replace')
            except NotImplementedError:
                ct = info.compress_type
                why = f'use {ZIP_METHODS[ct]} compression' if ct in ZIP_METHODS else f'use zip compression method {ct}'
                failed[why] = failed.get(why, 0) + 1
                continue
            except RuntimeError:                            # zipfile's way of saying 'encrypted, password required'
                failed['are encrypted'] = failed.get('are encrypted', 0) + 1
                continue
            except Exception:                               # BadZipFile (bad CRC), zlib.error, EOFError ...
                failed['are damaged'] = failed.get('are damaged', 0) + 1
                continue
            out += [Finding(f.rule, f.grade, f'{path}!{info.filename}', f.line, f.value, f.note) for f in scan_text(info.filename, text)]
            out += [Finding('doc_author', 'decide', f'{path}!{info.filename}', line, v, note) for v, line, note in zip_authors(info.filename, text)]
    parts = [_members(n, why) for why, n in failed.items()]
    if big:
        names = ', '.join(big[:3]) + (', ...' if len(big) > 3 else '')
        parts.append(f'{len(big)} over the {MEMBER_CAP >> 20} MB cap ({names})')
    if parts:
        out.append(unreadable(path, f'{"; ".join(parts)}; unscanned, check by hand'))
    return out


BIN_EXT = IMAGES + ZIPS + MP4S + ('.pdf', '.step', '.stp')
READERS = BIN_EXT + ('.stl',)                               # extensions a reader handles; any other binary is a gap in --path mode
MAX_BLOB = 8_000_000
STL_PEEK = 4096                                             # an STL over the cap is read this far: enough to tell binary from ASCII, and for its 80-byte header
MAX_TEXT = 64_000_000                                       # a text file is read to here: the gallery's pages hold 11 MB of embedded meshes
TEXT_EXT = ('.html', '.htm', '.js', '.mjs', '.json', '.css', '.svg', '.txt', '.md', '.csv', '.xml', '.obj', '.mtl', '.log')
MODES = ('head', 'staged', 'history')
EMPTY_TREE = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'     # what a first commit's index is compared with
PER_PATH = {'gps', 'unreadable'}                            # rules whose value says nothing about the file: one report row per path
# a Wavefront .obj vertex, texture, normal or face line made of numbers only: 99% of an exported mesh, and nothing a rule looks for
_MESH_LINE = re.compile(r'(?m)^(?:v|vt|vn|f)[ \t][-+0-9.eE/ \t\r]*$')


def _binary(data):
    """True for a binary: a NUL early on. UTF-16 with a byte order mark is text, not binary."""
    return data[:2] not in (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE) and b'\x00' in data[:4096]


def _text(data):
    """A file's text, or None for a binary."""
    if data[:2] in (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE):
        return data.decode('utf-16', 'replace')
    if _binary(data):
        return None
    return data.decode('utf-8', 'replace')


def _cap(path):
    """the most bytes of this file that is read: a page or other text file may be far larger than a binary, which Pillow or zipfile unpack"""
    return MAX_TEXT if path.lower().endswith(TEXT_EXT) else MAX_BLOB


def _oversize(path):
    return unreadable(path, f'over {_cap(path) / 1e6:g} MB, unscanned')


def _is_stl(path):
    return path.lower().endswith('.stl')


def _scan_big_stl(path, head):
    """An STL over the size cap, from its first STL_PEEK bytes. A binary one is its 80-byte header and the triangles, which no rule reads,
    so the header is all it needs whatever its size; an ASCII one is text that cannot be judged from its start, so it is a gap."""
    return _scan_bytes(path, head) if _binary(head) else [_oversize(path)]


def _scan_bytes(path, data):
    low = path.lower()
    if low.endswith(BIN_EXT):
        return scan_binary(path, data)
    text = _text(data)
    if text is None:
        if low.endswith('.stl'):                            # a binary STL: 80 bytes of header, which is text to the exporter
            return _meta_text(path + '!header', data[:80].decode('utf-8', 'replace').replace('\x00', ' '))
        return []                                           # other binaries (npz, f3d bodies): no text rules
    if low.endswith('.obj'):
        text = _MESH_LINE.sub('', text)                     # the line breaks stay, so line numbers do too
    return scan_text(path, text) + scan_data_uris(path, text)


def scan_folder(folder):
    out, errs = [], []
    for base, dirs, files in os.walk(folder, onerror=errs.append):         # onerror: a folder that cannot be listed is a finding
        dirs[:] = sorted(d for d in dirs if d != '.git')
        for d in dirs:
            if os.path.islink(os.path.join(base, d)):         # os.walk lists a linked folder but does not enter it
                out.append(unreadable(os.path.relpath(os.path.join(base, d), folder).replace(os.sep, '/'), 'linked folder not followed; check by hand'))
        for fn in sorted(files):
            p = os.path.join(base, fn); rel = os.path.relpath(p, folder).replace(os.sep, '/')
            try:
                if os.path.getsize(p) > _cap(rel):
                    if _is_stl(rel):
                        with open(p, 'rb') as fh:
                            out += _scan_big_stl(rel, fh.read(STL_PEEK))
                    else:
                        out.append(_oversize(rel))
                    continue
                with open(p, 'rb') as fh:
                    data = fh.read()
            except OSError as e:                              # a dangling link, no permission: the class name only, not the system's message (it names the path)
                out.append(unreadable(rel, f'file not readable ({type(e).__name__}); check by hand'))
                continue
            found = _scan_bytes(rel, data)
            if _binary(data) and not rel.lower().endswith(READERS):
                found.append(unreadable(rel, 'binary type not read; check by hand'))
            out += found
    for e in errs:
        where = os.path.relpath(e.filename, folder).replace(os.sep, '/') if e.filename else '.'
        out.append(unreadable(where, f'folder not listable ({type(e).__name__}); check by hand'))
    return out


def _git(repo, *a, data=None):
    return subprocess.run(['git', '-C', repo, *a], check=True, capture_output=True, input=data).stdout


def _path(raw):
    return raw.decode('utf-8', 'replace')                  # every listing below is -z, so git has not quoted or escaped the name


def _has_head(repo):
    return subprocess.run(['git', '-C', repo, 'rev-parse', '--verify', '-q', 'HEAD'], capture_output=True).returncode == 0


class _Objects:
    """Object lookups through two long-running `git cat-file` processes (--batch-check for type and size, --batch for contents),
    one request and one answer at a time. A process per blob cost about 20 ms each on Windows."""
    def __init__(self, repo):
        self.repo, self.procs = repo, {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        for p in self.procs.values():
            p.stdin.close(); p.stdout.close(); p.wait()

    def _ask(self, flag, sha):
        p = self.procs.get(flag)
        if p is None:
            p = self.procs[flag] = subprocess.Popen(['git', '-C', self.repo, 'cat-file', flag], stdin=subprocess.PIPE,
                                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        p.stdin.write(sha.encode() + b'\n'); p.stdin.flush()
        head = p.stdout.readline().split()
        if not head:
            raise RuntimeError(f'git cat-file {flag} ended early')
        return p, head

    def info(self, sha):
        """(type, size), or None when the object is not in the repository"""
        _, head = self._ask('--batch-check', sha)
        return None if head[1] == b'missing' else (head[1].decode(), int(head[2]))

    def read(self, sha, limit=None):
        """the blob's contents, or only its first `limit` bytes (the rest is read off the pipe and dropped, to keep it in step)"""
        p, head = self._ask('--batch', sha)
        size = int(head[2])
        keep = size if limit is None else min(limit, size)
        data = p.stdout.read(keep)
        left = size - keep
        while left > 0:                                                     # the unread rest, a megabyte at a time
            got = p.stdout.read(min(left, 1 << 20))
            if not got:
                break
            left -= len(got)
        p.stdout.read(1)                                                    # then the line feed that ends the contents
        if len(data) != keep or left > 0:
            raise RuntimeError('git cat-file --batch ended early')
        return data


def _scan_blobs(repo, entries):
    """For each (sha, path), the findings in that blob read under that name; one list per entry, in order. A blob is read once."""
    where = {}
    for i, (sha, _) in enumerate(entries):
        where.setdefault(sha, []).append(i)
    found = [[] for _ in entries]
    with _Objects(repo) as objs:
        for sha, idx in where.items():
            info = objs.info(sha)
            if info is None:
                for i in idx:
                    found[i] = [unreadable(entries[i][1], 'object not in this repository, unscanned')]
            elif info[0] != 'blob':
                continue
            else:
                small = [i for i in idx if info[1] <= _cap(entries[i][1])]     # the cap depends on the name: a page may be larger than a binary
                data = objs.read(sha) if small else None
                for i in idx:
                    if i not in small:
                        if _is_stl(entries[i][1]):                                  # over the cap, but only its start is needed
                            data = objs.read(sha, STL_PEEK) if data is None else data
                            found[i] = _scan_big_stl(entries[i][1], data[:STL_PEEK])
                        else:
                            found[i] = [_oversize(entries[i][1])]
                for i in small:
                    found[i] = _scan_bytes(entries[i][1], data)
    return found


def _new_blob(meta):
    """The blob a raw diff record ':old-mode new-mode old-sha new-sha status' leaves at its path; None for a deletion, a
    submodule (mode 160000) or an unmerged path (all-zero sha)."""
    _, mode, _, sha, status = meta.lstrip(b'\n:').split()[:5]
    if status.startswith(b'D') or mode == b'160000' or not sha.strip(b'0'):
        return None
    return sha.decode()


def _head_entries(repo):
    out = []
    for rec in (_git(repo, 'ls-tree', '-r', '-z', '--full-tree', 'HEAD').split(b'\0') if _has_head(repo) else []):
        meta, _, path = rec.partition(b'\t')                  # "mode type sha", a tab, the path
        f = meta.split()
        if len(f) == 3 and f[1] == b'blob':                    # not a submodule
            out.append((f[2].decode(), _path(path)))
    return out


def _staged_entries(repo):
    """What the next commit adds or changes: the index against HEAD (or against the empty tree before the first commit)."""
    raw = _git(repo, 'diff', '--cached', '--raw', '-z', '--no-renames', '--no-abbrev', '--diff-filter=d',
               'HEAD' if _has_head(repo) else EMPTY_TREE)
    toks, out = raw.split(b'\0'), []
    for i in range(0, len(toks) - 1, 2):                      # records alternate: the ':...' line, then the path
        sha = _new_blob(toks[i])
        if sha:
            out.append((sha, _path(toks[i + 1])))
    return out


def _history(repo):
    """One `git log` pass over every ref, oldest commit first and parents before children (--topo-order: commit dates can lie).
    Returns (blobs, commits): blobs = [(sha, path, rank)], one per blob and path, ranked by the first commit that had it there
    (-m lists a merge against each parent; --root lists the first commit's files); commits = [(hash, author email, committer email)]."""
    raw = _git(repo, 'log', '--all', '--reverse', '--topo-order', '--root', '-m', '--raw', '-z', '--no-abbrev', '--no-renames',
               '--format=%x01%H%x02%ae%x02%ce')
    commits, rank, blobs, seen = [], {}, [], set()
    toks, i, cur = raw.split(b'\0'), 0, -1
    while i < len(toks):
        t = toks[i].lstrip(b'\n')
        if t.startswith(b'\x01'):                              # a commit header: \x01 hash \x02 author email \x02 committer email
            h, ae, ce = t[1:].split(b'\x02', 2)
            if h not in rank:
                rank[h] = len(commits); commits.append((h.decode(), _path(ae), _path(ce)))
            cur = rank[h]; i += 1
        elif t.startswith(b':'):
            sha, path = _new_blob(t), _path(toks[i + 1]); i += 2
            if sha and (sha, path) not in seen:
                seen.add((sha, path)); blobs.append((sha, path, cur))
        else:
            i += 1
    return blobs, commits


def _messages(repo):
    """(hash, message) of every commit reachable from any ref; -z ends each commit with a NUL, which a message cannot hold"""
    out = []
    for rec in _git(repo, 'log', '--all', '-z', '--format=%H%x02%B').split(b'\0'):
        h, sep, msg = rec.partition(b'\x02')
        if sep:
            out.append((h.strip().decode(), _path(msg)))
    return out


def scan_repo(repo, mode='head'):
    """mode 'head': the files at HEAD. 'staged': only what the index adds or changes against HEAD. 'history': every blob in
    every commit of every ref, plus the commit authors and messages, oldest first, each finding with the first commit that had it."""
    if mode not in MODES:
        raise ValueError(f'unknown mode {mode!r}; expected one of {", ".join(MODES)}')
    if mode != 'history':
        return [f for fs in _scan_blobs(repo, _head_entries(repo) if mode == 'head' else _staged_entries(repo)) for f in fs]
    blobs, commits = _history(repo)
    out = []
    for (_, _, rank), fs in zip(blobs, _scan_blobs(repo, [(sha, path) for sha, path, _ in blobs])):
        for f in fs:
            f.commit = commits[rank][0][:10]; out.append((rank, f))
    for rank, (h, ae, ce) in enumerate(commits):
        for e in dict.fromkeys((ae, ce)):
            if not SAFE_EMAIL.search(e):
                out.append((rank, Finding('author_email', 'decide', '(commit metadata)', 0, e, 'an author or committer email', h[:10])))
    where = {c[0]: r for r, c in enumerate(commits)}
    for h, msg in _messages(repo):                             # a message is text anyone can put a path or a token in
        for f in scan_text('(commit message)', msg):
            f.commit = h[:10]; out.append((where.get(h, len(commits)), f))
    out.sort(key=lambda t: t[0])                               # stable: dedupe keeps the first finding of a value, the earliest commit's
    return [f for _, f in out]


def load_allow(path=None):
    path = path or ALLOW
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8-sig') as fh:               # a byte order mark is not part of the first rule
        return fh.read().split('\n')


def allowed(f, lines):
    for l in lines:
        l = re.sub(r'(?:^|\s)#.*$', '', l).strip()              # '#' starts a comment at the line's start or after a space, not inside a glob
        parts = l.split(None, 1)
        if len(parts) == 2 and parts[0] in ('*', f.rule) and fnmatch.fnmatchcase(f.path, parts[1].strip()):      # a rule alone matches nothing
            return True
    return False


def dedupe(findings):
    """one row per (rule, value), with every path it appears in; a rule whose value says nothing about the file (a GPS block,
    an unreadable file) gets one row per path, so no file hides behind another"""
    rows = {}
    for f in findings:
        key = (f.rule, f.value, f.path) if f.rule in PER_PATH or not f.value.strip() else (f.rule, f.value)
        r = rows.setdefault(key, dict(f=f, paths=[], n=0))
        r['n'] += 1
        if f.path not in r['paths']:
            r['paths'].append(f.path)
    return list(rows.values())


def _cell(v):
    """one table cell: on one line, with any '|' escaped"""
    return ' '.join(str(v).splitlines()).replace('|', '\\|')


def report(findings):
    L_ = ['| grade | rule | value (redacted) | where | first commit | note |', '|---|---|---|---|---|---|']
    for r in sorted(dedupe(findings), key=lambda r: (r['f'].grade != 'must', r['f'].rule)):
        f, paths = r['f'], r['paths']
        where = ', '.join(paths) + (f':{f.line}' if f.line and len(paths) == 1 else '')
        note = f'{f.note} ({r["n"]}x)'
        L_.append(f'| {f.grade} | {f.rule} | {_cell(redact(f.value))} | {_cell(where)} | {_cell(f.commit)} | {_cell(note)} |')
    return '\n'.join(L_) + '\n'


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):                    # a cp1252 console or pipe cannot print every file name
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError, OSError):
            pass
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--history', action='store_true'); g.add_argument('--staged', action='store_true'); g.add_argument('--path')
    ap.add_argument('--strict', action='store_true'); ap.add_argument('--report')
    ap.add_argument('--allow', help='accepted findings from this file instead of tools/leakscan_allow.txt')
    a = ap.parse_args(argv)
    if a.path is not None and not os.path.isdir(a.path):                     # '' and a missing folder: an error, not a clean or HEAD scan
        print(f'leakscan: --path {a.path!r} is not a folder', file=sys.stderr)
        return 2
    if a.allow is not None and not os.path.isfile(a.allow):                  # a typo must not read as an empty list
        print(f'leakscan: --allow {a.allow!r} is not a file', file=sys.stderr)
        return 2
    fs = scan_folder(a.path) if a.path is not None else scan_repo(ROOT, 'history' if a.history else 'staged' if a.staged else 'head')
    allow = load_allow(a.allow)
    left = [f for f in fs if not allowed(f, allow)]
    text = report(left)
    if a.report:
        os.makedirs(os.path.dirname(os.path.abspath(a.report)), exist_ok=True)
        with open(a.report, 'w', encoding='utf-8') as fh:
            fh.write(text)
    print(text)
    bad = [f for f in left if f.grade == 'must' or a.strict]
    print(f'{len(fs)} findings, {len(fs) - len(left)} allowed, {len(bad)} blocking')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
