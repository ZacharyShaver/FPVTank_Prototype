# Repo Leak Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Find everything in FPVTank_Prototype, in the working tree and in every commit, that shouldn't become public, fix what can be fixed in place, and settle how anything gets published.

**Architecture:** One scanner, `tools/leakscan.py`, with a rule table (regexes plus metadata readers for images, PDFs, STEP and zip-based CAD files). It scans a folder, the tracked files at HEAD, or every blob reachable from every ref plus commit metadata. Findings are deduplicated, redacted (a value is never printed whole) and graded `must` (blocks publishing) or `decide` (Zach's call). Every rule is tested against a planted case that must be found and a near-miss that must not (the repo's negative-control rule, CLAUDE.md). The same scanner gates the Pages site (plan `2026-10-25-pages-showcase.md`) and runs as a pre-commit hook.

**Tech Stack:** Python 3.10 standard library (`re`, `subprocess`, `zipfile`, `unittest`), Pillow 12 (EXIF), git 2.x, gh 2.95.

## Global Constraints

- Run with `python` (Zach's Microsoft Store Python 3.10). No new pip installs except `git-filter-repo`, and only in Task 6 option B, after Zach says yes.
- Never print, log, commit or paste a found secret's value. Reports show `ab…z (9 chars)` at most.
- The repo is PRIVATE (`gh repo view`: `visibility PRIVATE`). Nothing here makes it public; that is Task 6's decision, Zach's.
- Commit only when Zach asks (CLAUDE.md); never push without asking; never rewrite history without his explicit yes.
- Every check ships with a negative control: a planted case it must flag and a near-miss it must not.
- Write documents in the third person; keep them short (CLAUDE.md).

## What a first look already found (2026-10-25, before any of this was built)

| Finding | Where | Grade |
|---|---|---|
| A real Wi-Fi network name and password | `archive/v1-2024/robot/DCMotorTest/DCMotorTest.ino:45-46`, `archive/v1-2024/robot/DCMotorTest/WiFiClient/WiFiClient.ino:20-21`, in every commit since the archive was added | must |
| Zach's personal email as author of 91 commits | git metadata (the other 5 use the GitHub noreply address) | decide |
| Home-network addresses | `tools/config.py:39` (the K2 printer, whose Moonraker API has no login), `archive/v1-2024/controller/SocketServer.py:3`, `archive/v1-2024/robot/code.py:79`, `WiFiClient.ino:23` | decide |
| The Windows user name in absolute paths | 10 tracked files (`research`, `head-v2/generator/generators`, `docs/reorg-2026-09`, `docs/lessons`, `head-v2`) | decide |
| Third-party files: the FPV-Rover download (Instructables PDF, STLs), Raspberry Pi 5 and PCA9685 models | `reference/`, `chassis-v1/parts/` | decide (licences) |
| The fellowship application drafts | `research/paper/` | decide |
| Clean: no EXIF or GPS in `research/data/drops/run1_sheet.jpg`; STEP headers say only "Author"; no API tokens or private keys; nothing sensitive ever deleted from history | | ok |

The tool below makes this repeatable and complete (every blob in history, every binary's metadata), rather than a one-off grep.

---

### Task 1: The scanner's rules, on text, with planted cases

**Files:**
- Create: `tools/leakscan.py`
- Create: `tools/tests/__init__.py` (empty)
- Create: `tools/tests/test_leakscan.py`

**Interfaces:**
- Produces: `Finding` (dataclass: `rule: str`, `grade: str` (`'must'` or `'decide'`), `path: str`, `line: int`, `value: str`, `note: str`, `commit: str = ''`); `scan_text(path: str, text: str) -> list[Finding]`; `redact(value: str) -> str`.

- [ ] **Step 1: Write the failing tests**

```python
# tools/tests/test_leakscan.py
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import leakscan as L


def rules(text, path='x.ino'):
    return sorted({f.rule for f in L.scan_text(path, text)})


class TextRules(unittest.TestCase):
    def test_wifi_credentials_found(self):
        t = 'const char *ssid = "homenet";\nconst char *password = "Hunter2!x";\n'
        self.assertEqual(rules(t), ['credential'])
        self.assertEqual(len(L.scan_text('x.ino', t)), 2)

    def test_placeholder_credentials_not_found(self):        # the near-miss: the README's example
        t = 'const char* ssid = "your-ssid";\nconst char* password = "your-password";\n'
        self.assertEqual(rules(t), [])

    def test_tokens_and_keys(self):
        self.assertEqual(rules('t = "ghp_' + 'a' * 36 + '"'), ['token'])
        self.assertEqual(rules('-----BEGIN RSA PRIVATE KEY-----'), ['token'])
        self.assertEqual(rules('AKIA' + 'B' * 16), ['token'])

    def test_base64_blob_is_not_a_token(self):               # the near-miss: mesh data in a viewer .js
        self.assertEqual(rules('window.M={"v":"s8L3wRfbsr/lCUc/c7v3wbq4u798KF9AFtT3wUr9k7+S8pRAi7P3"}', 'v.js'), [])

    def test_personal_email_but_not_noreply(self):
        self.assertEqual(rules('mail me: someone@hotmail.com'), ['email'])
        self.assertEqual(rules('Co-Authored-By: Claude <noreply@anthropic.com>'), [])
        self.assertEqual(rules('36010164+Z@users.noreply.github.com'), [])

    def test_private_ip_but_not_public(self):
        self.assertEqual(rules("PRINTER = 'http://10.0.0.99:7125'", 'config.py'), ['private_ip'])
        self.assertEqual(rules('dns 8.8.8.8 and version 10.2', 'notes.md'), [])

    def test_user_paths(self):
        self.assertEqual(rules(r'C:\Users\someone\Downloads\x.stl', 'a.md'), ['user_path'])
        self.assertEqual(rules('/c/Users/someone/Documents', 'a.md'), ['user_path'])
        self.assertEqual(rules('the users of the tool', 'a.md'), [])

    def test_private_artifact_links(self):
        self.assertEqual(rules('https://claude.ai/artifact/FakeArtifactId0123abcd', 'README.md'), ['artifact_link'])

    def test_redaction_never_shows_the_value(self):
        r = L.redact('Hunter2!x')
        self.assertNotIn('nter2', r)
        self.assertIn('9 chars', r)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run them to see them fail**

Run: `python -m unittest tools/tests/test_leakscan.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'leakscan'`

- [ ] **Step 3: Write the scanner's text rules**

```python
# tools/leakscan.py
"""Find what shouldn't leave this repo: credentials, tokens, personal emails, home-network addresses, local user
paths, private claude.ai links, and metadata in binaries, in a folder, in HEAD's tracked files, or in every commit.

    python tools/leakscan.py                  # tracked files at HEAD; exit 1 on any 'must' not allowed
    python tools/leakscan.py --history        # every blob reachable from every ref, plus commit authors
    python tools/leakscan.py --path site/out  # any folder (the Pages site before it is published)
    python tools/leakscan.py --staged         # the index (the pre-commit hook)
    python tools/leakscan.py --strict         # 'decide' findings fail too (the Pages gate)
    python tools/leakscan.py --report docs/audit/leak-report.md

Values are always redacted. Accepted findings: tools/leakscan_allow.txt, one 'rule glob' per line.
"""
import os, re, sys, fnmatch, argparse, subprocess
from dataclasses import dataclass

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ALLOW = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'leakscan_allow.txt')
PLACEHOLDERS = {'your-ssid', 'your-password', 'password', 'changeme', 'xxxx', '****', 'ssid', 'secret', ''}
SAFE_EMAIL = re.compile(r'(noreply@anthropic\.com|@users\.noreply\.github\.com|@example\.(com|org)|git@github\.com)$', re.I)
LONG_LINE = 2000                                   # base64 meshes: only the tight token rules look at longer lines


@dataclass
class Finding:
    rule: str
    grade: str
    path: str
    line: int
    value: str
    note: str
    commit: str = ''


# (rule, grade, regex, value group, note); value group 0 = the whole match
RULES = [
    ('credential', 'must', re.compile(r'(?i)\b(?:ssid|password|passwd|pwd|psk|passphrase)\b\s*=\s*["\']([^"\'\n]*)["\']'), 1,
     'a credential in source; replace with a placeholder and rotate it'),
    ('token', 'must', re.compile(r'\bghp_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{22,}\b|\bsk-[A-Za-z0-9]{32,}\b|\bAKIA[0-9A-Z]{16}\b'
                                 r'|\bxox[baprs]-[A-Za-z0-9-]{10,}\b|-----BEGIN [A-Z ]*PRIVATE KEY-----'), 0, 'a token or key'),
    ('email', 'decide', re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'), 0, 'a personal email address'),
    ('private_ip', 'decide', re.compile(r'\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b'), 0,
     'an address on the home network'),
    ('user_path', 'decide', re.compile(r'(?i)[A-Z]:\\Users\\[^\\\s"\'<>]+|/c/Users/[^/\s"\'<>]+|(?<![\w.])/Users/[^/\s"\'<>]+|/home/[^/\s"\'<>]+|OneDrive'), 0,
     'an absolute path with the user name'),
    ('artifact_link', 'decide', re.compile(r'https?://claude\.ai/(?:code/)?artifact/[A-Za-z0-9-]+'), 0, 'a private claude.ai link'),
]
TIGHT = {'token'}


def redact(value: str) -> str:
    v = value.strip()
    return f'{v[:2]}…{v[-1:]} ({len(v)} chars)' if len(v) > 3 else f'… ({len(v)} chars)'


def scan_text(path: str, text: str) -> list:
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        long_ = len(line) > LONG_LINE
        for rule, grade, rx, g, note in RULES:
            if long_ and rule not in TIGHT:
                continue
            for m in rx.finditer(line):
                v = m.group(g)
                if rule == 'credential' and v.strip().lower() in PLACEHOLDERS:
                    continue
                if rule == 'email' and SAFE_EMAIL.search(v):
                    continue
                out.append(Finding(rule, grade, path, n, v, note))
    return out
```

- [ ] **Step 4: Run the tests**

Run: `python -m unittest tools/tests/test_leakscan.py -v`
Expected: 9 tests, `OK`

- [ ] **Step 5: Commit (when Zach asks)**

```bash
git add tools/leakscan.py tools/tests/__init__.py tools/tests/test_leakscan.py
git commit -m "tools: leakscan.py text rules (credentials, tokens, emails, home IPs, user paths, private links), each with a planted case and a near-miss"
```

---

### Task 2: Metadata in binaries

**Files:**
- Modify: `tools/leakscan.py` (add `scan_binary`)
- Modify: `tools/tests/test_leakscan.py` (add `class Binaries`)

**Interfaces:**
- Consumes: `Finding`, `scan_text` (Task 1).
- Produces: `scan_binary(path: str, data: bytes) -> list[Finding]`, for `.jpg .jpeg .png .heic .tif .tiff .pdf .step .stp .f3d .3mf .fcstd .docx`; other extensions return `[]`.

- [ ] **Step 1: Write the failing tests**

```python
# append to tools/tests/test_leakscan.py
import io, zipfile
from PIL import Image


def jpeg(gps):
    im = Image.new('RGB', (8, 8)); ex = Image.Exif(); ex[0x010F] = 'Apple'
    if gps:
        ex[0x8825] = {1: 'N', 2: (42.0, 16.0, 30.0), 3: 'W', 4: (83.0, 44.0, 10.0)}
    b = io.BytesIO(); im.save(b, 'JPEG', exif=ex); return b.getvalue()


class Binaries(unittest.TestCase):
    def test_gps_in_a_photo(self):
        self.assertIn('gps', {f.rule for f in L.scan_binary('a.jpg', jpeg(True))})

    def test_photo_without_gps(self):                          # the near-miss: a camera make alone isn't a location
        self.assertNotIn('gps', {f.rule for f in L.scan_binary('a.jpg', jpeg(False))})

    def test_pdf_author(self):
        self.assertEqual({f.rule for f in L.scan_binary('a.pdf', b'%PDF-1.4\n<< /Author (Jane Q Public) /Creator (Word) >>')}, {'doc_author'})
        self.assertEqual(L.scan_binary('b.pdf', b'%PDF-1.4\n<< /Creator (matplotlib) >>'), [])

    def test_step_author(self):
        hdr = b"FILE_NAME('part','2026-01-01',('Jane Q Public'),('Acme Inc'),'x','y','z');"
        self.assertEqual({f.rule for f in L.scan_binary('a.step', hdr)}, {'doc_author'})
        self.assertEqual(L.scan_binary('b.step', b"FILE_NAME('part','2026',('Author'),(''),'x','y','z');"), [])

    def test_text_rules_inside_a_cad_zip(self):
        b = io.BytesIO()
        with zipfile.ZipFile(b, 'w') as z:
            z.writestr('Document.xml', '<Doc CreatedBy="x" path="C:\\Users\\jane\\Desktop\\a.FCStd"/>')
        self.assertIn('user_path', {f.rule for f in L.scan_binary('a.FCStd', b.getvalue())})
```

- [ ] **Step 2: Run them to see them fail**

Run: `python -m unittest tools/tests/test_leakscan.py -v`
Expected: FAIL, `AttributeError: module 'leakscan' has no attribute 'scan_binary'`

- [ ] **Step 3: Write `scan_binary`**

```python
# append to tools/leakscan.py
import io, zipfile

IMAGES = ('.jpg', '.jpeg', '.png', '.heic', '.tif', '.tiff')
ZIPS = ('.f3d', '.3mf', '.fcstd', '.docx')
NOBODY = {'', 'author', 'unknown', 'none', 'open cascade', 'user'}


def scan_binary(path: str, data: bytes) -> list:
    ext = os.path.splitext(path)[1].lower(); out = []
    if ext in IMAGES:
        try:
            from PIL import Image
            ex = Image.open(io.BytesIO(data)).getexif()
            if ex.get_ifd(0x8825):
                out.append(Finding('gps', 'must', path, 0, 'GPS block', 'a photo with its location; strip EXIF'))
            for tag, name in ((0x013B, 'Artist'), (0x8298, 'Copyright')):
                if ex.get(tag):
                    out.append(Finding('doc_author', 'decide', path, 0, str(ex[tag]), f'EXIF {name}'))
        except Exception:
            pass
    elif ext == '.pdf':
        for m in re.finditer(rb'/Author\s*\(([^)]*)\)', data):
            v = m.group(1).decode('latin-1').strip()
            if v.lower() not in NOBODY:
                out.append(Finding('doc_author', 'decide', path, 0, v, 'PDF author'))
    elif ext in ('.step', '.stp'):
        m = re.search(rb"FILE_NAME\s*\('[^']*','[^']*',\(([^)]*)\),\(([^)]*)\)", data[:20000])
        if m:
            for v in (m.group(1), m.group(2)):
                v = v.decode('latin-1').strip("' ")
                if v.lower() not in NOBODY:
                    out.append(Finding('doc_author', 'decide', path, 0, v, 'STEP header author or organisation'))
    elif ext in ZIPS:
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for info in z.infolist():
                    if info.file_size <= 2_000_000 and info.filename.lower().endswith(('.xml', '.json', '.txt', '.dat', '.model', '.rels')):
                        out += [Finding(f.rule, f.grade, f'{path}!{info.filename}', f.line, f.value, f.note)
                                for f in scan_text(info.filename, z.read(info).decode('utf-8', 'replace'))]
        except zipfile.BadZipFile:
            pass
    return out
```

- [ ] **Step 4: Run the tests**

Run: `python -m unittest tools/tests/test_leakscan.py -v`
Expected: 14 tests, `OK`

- [ ] **Step 5: Commit (when Zach asks)**

```bash
git add tools/leakscan.py tools/tests/test_leakscan.py
git commit -m "tools: leakscan reads metadata (photo GPS, PDF and STEP authors, text inside CAD zips), each with a near-miss"
```

---

### Task 3: Where to look (folder, HEAD, staged, every commit), the allowlist and the report

**Files:**
- Modify: `tools/leakscan.py` (add sources, `allowed`, `report`, `main`)
- Create: `tools/leakscan_allow.txt`
- Modify: `tools/tests/test_leakscan.py` (add `class History`)

**Interfaces:**
- Consumes: `scan_text`, `scan_binary` (Tasks 1-2).
- Produces: `scan_repo(repo: str, mode: str) -> list[Finding]` with mode in `{'head', 'staged', 'history'}`; `scan_folder(folder: str) -> list[Finding]`; `allowed(f: Finding, lines: list[str]) -> bool`; `report(findings: list[Finding]) -> str` (markdown, values redacted); CLI exit code 1 when a `must` (or, with `--strict`, any) finding isn't allowed.

- [ ] **Step 1: Write the failing tests**

```python
# append to tools/tests/test_leakscan.py
import subprocess, tempfile


def git(repo, *a):
    return subprocess.run(['git', '-C', repo, *a], check=True, capture_output=True, text=True).stdout


class History(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); git(self.d, 'init', '-q')
        git(self.d, 'config', 'user.email', 'someone@hotmail.com'); git(self.d, 'config', 'user.name', 'T')
        open(os.path.join(self.d, 'wifi.ino'), 'w').write('const char *password = "Hunter2!x";\n')
        git(self.d, 'add', '.'); git(self.d, 'commit', '-q', '-m', 'add')
        os.remove(os.path.join(self.d, 'wifi.ino')); open(os.path.join(self.d, 'ok.md'), 'w').write('nothing\n')
        git(self.d, 'add', '-A'); git(self.d, 'commit', '-q', '-m', 'remove')

    def test_head_is_clean_but_history_is_not(self):            # the control: deleting a file doesn't remove it
        self.assertEqual([f for f in L.scan_repo(self.d, 'head') if f.rule == 'credential'], [])
        hist = [f for f in L.scan_repo(self.d, 'history') if f.rule == 'credential']
        self.assertEqual(len(hist), 1); self.assertEqual(hist[0].path, 'wifi.ino'); self.assertTrue(hist[0].commit)

    def test_commit_author_emails(self):
        self.assertIn('author_email', {f.rule for f in L.scan_repo(self.d, 'history')})

    def test_allowlist_and_report_redact(self):
        f = L.Finding('credential', 'must', 'wifi.ino', 1, 'Hunter2!x', 'n')
        self.assertTrue(L.allowed(f, ['credential wifi.*'])); self.assertFalse(L.allowed(f, ['email wifi.*']))
        self.assertTrue(L.allowed(f, ['* wifi.*  # every rule, this file']))
        self.assertNotIn('Hunter2', L.report([f]))
```

- [ ] **Step 2: Run them to see them fail**

Run: `python -m unittest tools/tests/test_leakscan.py -v`
Expected: FAIL, `AttributeError: module 'leakscan' has no attribute 'scan_repo'`

- [ ] **Step 3: Write the sources, allowlist, report and CLI**

```python
# append to tools/leakscan.py
BIN_EXT = IMAGES + ZIPS + ('.pdf', '.step', '.stp')
MAX_BLOB = 8_000_000


def _scan_bytes(path, data):
    if path.lower().endswith(BIN_EXT):
        return scan_binary(path, data)
    if b'\x00' in data[:4096]:
        return []                                           # other binaries (STL, npz, f3d bodies): no text rules
    return scan_text(path, data.decode('utf-8', 'replace'))


def scan_folder(folder):
    out = []
    for base, _, files in os.walk(folder):
        if '.git' in base.split(os.sep):
            continue
        for fn in files:
            p = os.path.join(base, fn); rel = os.path.relpath(p, folder).replace(os.sep, '/')
            if os.path.getsize(p) <= MAX_BLOB:
                out += _scan_bytes(rel, open(p, 'rb').read())
    return out


def _git(repo, *a, data=None):
    return subprocess.run(['git', '-C', repo, *a], check=True, capture_output=True, input=data).stdout


def scan_repo(repo, mode='head'):
    out = []
    if mode in ('head', 'staged'):
        rows = _git(repo, 'ls-tree', '-r', 'HEAD') if mode == 'head' else _git(repo, 'ls-files', '-s')
        for line in rows.decode().splitlines():              # ls-tree: "mode blob sha\tpath"; ls-files -s: "mode sha stage\tpath"
            meta, path = line.split('\t', 1); f_ = meta.split()
            sha = f_[2] if mode == 'head' else f_[1]
            if mode == 'head' and f_[1] != 'blob':
                continue
            blob = _git(repo, 'cat-file', 'blob', sha)
            if len(blob) <= MAX_BLOB:
                out += _scan_bytes(path, blob)
        return out
    seen = {}                                                # history: every blob once, with its first path and commit
    for line in _git(repo, 'rev-list', '--objects', '--all').decode().splitlines():
        sha, _, path = line.partition(' ')
        if path and sha not in seen:
            seen[sha] = path
    first = {}
    for c in _git(repo, 'rev-list', '--all', '--reverse').decode().split():
        for row in _git(repo, 'ls-tree', '-r', c).decode().splitlines():
            sha = row.split()[2]
            first.setdefault(sha, c[:10])
    for sha, path in seen.items():
        kind = _git(repo, 'cat-file', '-t', sha).decode().strip()
        if kind != 'blob' or int(_git(repo, 'cat-file', '-s', sha)) > MAX_BLOB:
            continue
        for f in _scan_bytes(path, _git(repo, 'cat-file', 'blob', sha)):
            f.commit = first.get(sha, ''); out.append(f)
    for row in _git(repo, 'log', '--all', '--format=%H%x09%ae%x09%ce').decode().splitlines():
        h, ae, ce = row.split('\t')
        for e in {ae, ce}:
            if not SAFE_EMAIL.search(e):
                out.append(Finding('author_email', 'decide', '(commit metadata)', 0, e, 'an author or committer email', h[:10]))
    return out


def allowed(f, lines):
    for l in lines:
        l = l.split('#')[0].strip()
        if l:
            rule, glob = l.split(None, 1)
            if rule in ('*', f.rule) and fnmatch.fnmatch(f.path, glob):
                return True
    return False


def dedupe(findings):
    """one row per (rule, value), with every path it appears in"""
    rows = {}
    for f in findings:
        r = rows.setdefault((f.rule, f.value), dict(f=f, paths=[], n=0))
        r['n'] += 1
        if f.path not in r['paths']:
            r['paths'].append(f.path)
    return list(rows.values())


def report(findings):
    L_ = ['| grade | rule | value (redacted) | where | first commit | note |', '|---|---|---|---|---|---|']
    for r in sorted(dedupe(findings), key=lambda r: (r['f'].grade != 'must', r['f'].rule)):
        f = r['f']; where = ', '.join(r['paths'][:4]) + (f' (+{len(r["paths"]) - 4} more)' if len(r['paths']) > 4 else '')
        L_.append(f"| {f.grade} | {f.rule} | {redact(f.value)} | {where}{':' + str(f.line) if f.line and len(r['paths']) == 1 else ''} | {f.commit} | {f.note} ({r['n']}x) |")
    return '\n'.join(L_) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--history', action='store_true'); g.add_argument('--staged', action='store_true'); g.add_argument('--path')
    ap.add_argument('--strict', action='store_true'); ap.add_argument('--report')
    a = ap.parse_args(argv)
    fs = scan_folder(a.path) if a.path else scan_repo(ROOT, 'history' if a.history else 'staged' if a.staged else 'head')
    allow = open(ALLOW, encoding='utf-8').read().splitlines() if os.path.exists(ALLOW) else []
    left = [f for f in fs if not allowed(f, allow)]
    text = report(left)
    if a.report:
        os.makedirs(os.path.dirname(os.path.abspath(a.report)), exist_ok=True); open(a.report, 'w', encoding='utf-8').write(text)
    print(text)
    bad = [f for f in left if f.grade == 'must' or a.strict]
    print(f'{len(fs)} findings, {len(fs) - len(left)} allowed, {len(bad)} blocking')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
```

```text
# tools/leakscan_allow.txt: accepted findings, one 'rule path-glob' per line ('*' = every rule). Say why on each.
* tools/tests/test_leakscan.py                     # planted test values (a fake password, key, path), not real
* tools/tests/test_site.py                         # planted test values for the gallery's leak gate
* docs/superpowers/plans/2026-10-25-leak-audit.md  # the same test code, quoted in the plan
* docs/superpowers/plans/2026-10-25-pages-showcase.md  # the gallery's test code and private-link examples
```

- [ ] **Step 4: Run the tests**

Run: `python -m unittest tools/tests/test_leakscan.py -v`
Expected: 17 tests, `OK`

- [ ] **Step 5: Run it on the repo as a smoke test (no fixes yet)**

Run: `python tools/leakscan.py`
Expected: exit code 1; nothing from the four allowlisted files; the `must` rows are the two `.ino` credentials (2 values, 2 files each: the network name and the password); `decide` rows include `private_ip` in `tools/config.py`, `user_path` in 10 files, and `artifact_link` in READMEs.

- [ ] **Step 6: Commit (when Zach asks)**

```bash
git add tools/leakscan.py tools/leakscan_allow.txt tools/tests/test_leakscan.py
git commit -m "tools: leakscan scans a folder, HEAD, the index or every commit (with first-commit and author emails), allowlist, redacted report"
```

---

### Task 4: The full audit, written down

**Files:**
- Create: `docs/audit/2026-10-25-leak-report.md` (generated, then annotated)

**Interfaces:**
- Consumes: the CLI from Task 3.

- [ ] **Step 1: Run the history scan into the report**

Run: `python tools/leakscan.py --history --report docs/audit/2026-10-25-leak-report.md`
Expected: exit code 1; the table lists the credentials with the commit that first added them, `author_email` rows for the personal address (91 commits) and none for the noreply one.

- [ ] **Step 2: Check the scanner against the first look (the control on the whole run)**

Every row of "What a first look already found" above must appear in the report: the credentials, the author email, the four home-network files, the user paths. Run: `python tools/leakscan.py --history | findstr /C:"credential" /C:"author_email" /C:"private_ip" /C:"user_path"`
Expected: all four rules present. If one is missing, the scanner is blind there: fix the rule and add its case to the tests before going on.

- [ ] **Step 3: Annotate the report for Zach**

Add a header to `docs/audit/2026-10-25-leak-report.md`, above the generated table:

```markdown
# Leak audit, 2026-10-25

Scanned: every blob reachable from main, reorg and research-sprint (local and origin), commit metadata, and the
metadata of every photo, PDF, STEP and CAD zip. Values are redacted. Generated by `python tools/leakscan.py --history`.

Needs Zach (one line each, his call recorded here when made):
- Wi-Fi credentials in two 2024 sketches: rotate the network's password if it's still in use? (Fixing the files doesn't remove them from history.)
- Personal email on 91 commits: fine in a private repo; public only after a mailmap rewrite (Task 6, option B).
- Home addresses (printer, old robot): move the printer's to a local untracked setting (Task 5)? The archive's are from 2024.
- User name in 10 absolute paths: rewrite as repo-relative (Task 5), or allow as history notes?
- Third-party files in reference/ and chassis-v1/parts/: keep out of anything public unless their licences allow it.
- The fellowship application drafts (research/paper/): private until submitted and decided?
- Private claude.ai links in READMEs: harmless privately; strip from anything public.
```

- [ ] **Step 4: Commit (when Zach asks)**

```bash
git add docs/audit/2026-10-25-leak-report.md
git commit -m "docs: leak audit of HEAD and full history (values redacted), with the calls Zach needs to make"
```

---

### Task 5: Fix what can be fixed in place, and guard against a repeat

**Files:**
- Modify: `archive/v1-2024/robot/DCMotorTest/DCMotorTest.ino:45-46`
- Modify: `archive/v1-2024/robot/DCMotorTest/WiFiClient/WiFiClient.ino:20-21`
- Modify: `tools/config.py:39`
- Create: `tools/config_local.example.py`
- Modify: `.gitignore` (add `tools/config_local.py`)
- Modify: the files `python tools/leakscan.py` lists under `user_path` (paths made repo-relative, or allowlisted with a reason)
- Modify: `tools/leakscan_allow.txt`
- Create: `.githooks/pre-commit`

**Interfaces:**
- Consumes: the CLI from Task 3 (`--staged`).
- Produces: `config.PRINTER` read from `tools/config_local.py` when present, else the environment variable `FPVTANK_PRINTER`, else `None` (so `tools/k2.py` fails with a clear message instead of using a committed address).

- [ ] **Step 1: Replace the credentials with placeholders** in both sketches (the network name and password lines):

```cpp
const char *ssid = "your-ssid";          // set locally; never commit a real one
const char *password = "your-password";  // set locally; never commit a real one
```

- [ ] **Step 2: Move the printer's address out of the repo**

```python
# tools/config.py, replacing line 39 (the committed printer address)
try:
    from config_local import PRINTER                         # untracked: tools/config_local.py
except ImportError:
    PRINTER = os.environ.get('FPVTANK_PRINTER')              # e.g. http://<printer-ip>:7125
```

```python
# tools/config_local.example.py: copy to tools/config_local.py (gitignored) and fill in
PRINTER = 'http://<printer-ip>:7125'
```

Append to `.gitignore`: `tools/config_local.py`. Zach copies the example and writes his printer's address into the untracked copy.

Check that `tools/k2.py status` still works: run `python tools/k2.py status`. Expected: the printer's state line (as before). Control: rename `tools/config_local.py` and unset `FPVTANK_PRINTER`, run it again. Expected: it fails, saying `PRINTER` is not set. (If `k2.py` crashes with a traceback instead, add `if not config.PRINTER: sys.exit('set PRINTER in tools/config_local.py or FPVTANK_PRINTER')` at its top.)

- [ ] **Step 3: User paths**: for each file under `user_path`, replace an absolute path that points into the repo with the repo-relative one. Leave history notes that name a past location (for example `docs/reorg-2026-09/*`) and allowlist them with a reason:

```text
user_path docs/reorg-2026-09/*   # the reorganisation's record of where things lived; private repo only
```

- [ ] **Step 4: The pre-commit hook** (a real failure happened, so the check is earned):

```sh
#!/bin/sh
# .githooks/pre-commit: refuse a commit that adds a credential, token or located photo
exec python tools/leakscan.py --staged
```

Enable it (Zach, once, in his clone): `git config core.hooksPath .githooks`

Control: stage a file containing `password = "Hunter2!x"` and run `git commit -m test`. Expected: refused, with one `must` row. Unstage and delete the file afterwards.

- [ ] **Step 5: Rescan HEAD**

Run: `python tools/leakscan.py`
Expected: exit code 0, `0 blocking`; the `decide` rows left are only those Zach chose to keep (allowlisted with reasons).

- [ ] **Step 6: Commit (when Zach asks)**

```bash
git add archive/v1-2024/robot/DCMotorTest tools/config.py tools/config_local.example.py .gitignore tools/leakscan_allow.txt .githooks/pre-commit
git commit -m "Remove the Wi-Fi credentials and the printer's address from tracked files; repo-relative paths; pre-commit leak check"
```

---

### Task 6: How anything gets published (Zach decides; nothing here runs without his yes)

HEAD can be clean while every past commit still holds the credentials and the personal email. Two routes:

**Option A (recommended): keep this repo private; publish only a curated site from a separate public repo.** No history rewrite. The site is built from this repo and checked by `leakscan --path site/out --strict` before every push (plan `2026-10-25-pages-showcase.md`). This repo's history never leaves.

**Option B: make this repo public.** Rewrites every commit hash, breaks every clone, and needs a force-push of all three branches. Only after Zach's explicit yes:

- [ ] **Step 1:** Zach rotates the Wi-Fi password if the network is still in use. The old one stays in GitHub's copy of the history until the rewrite is pushed.
- [ ] **Step 2:** Back up: `git clone --mirror https://github.com/ZacharyShaver/FPVTank_Prototype.git ..\FPVTank_Prototype-backup.git`
- [ ] **Step 3:** Install the tool (a download; ask first): `python -m pip install git-filter-repo`
- [ ] **Step 4:** Write `..\replacements.txt` outside the repo (it holds the old values, so it is never committed): one line per value, `OLDVALUE==>REDACTED`, for the network name, the password, and the printer and robot addresses.
- [ ] **Step 5:** Write `..\mailmap` (outside the repo): one line, `Zachary Shaver <36010164+ZacharyShaver@users.noreply.github.com> <OLD>`, where OLD is the address that `git log --all --format=%ae | sort | uniq -c` lists 91 times. The plan doesn't repeat it.
- [ ] **Step 6:** In a fresh mirror clone: `git filter-repo --replace-text ..\replacements.txt --mailmap ..\mailmap`
- [ ] **Step 7:** Verify: `python tools/leakscan.py --history` exits 0 with no `credential` or `author_email` rows.
- [ ] **Step 8:** Push (asks Zach first): `git push --force --mirror origin`; delete and re-clone every local copy; then make the repo public in GitHub's settings. Old commit hashes can stay reachable through GitHub's caches until GitHub support purges them.

Record Zach's choice at the top of `docs/audit/2026-10-25-leak-report.md`, and in `docs/decisions.md` (a decision, kept even if it's later reversed).
