# tools/gallery/publish.py
"""Publish site/out to a separate PUBLIC repo and turn GitHub Pages on for it. Outward-facing: it pushes only with --yes,
which Zach gives in chat each time. This repo (private) is never pushed and its history never leaves.

    python tools/gallery/publish.py                       # rebuild, then say what would go where (no network); exit 2
    python tools/gallery/publish.py --yes                 # rebuild, create the repo if needed, push, turn Pages on

The public commit carries Zach's GitHub noreply identity, given per command with -c (nothing is written to any git config),
and nothing is pushed if a commit in the work clone holds any other address.
"""
import os, re, sys, json, shutil, argparse, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from gallery import build as B

DEFAULT_REPO = 'ZacharyShaver/scorpion-gallery'
NAME, EMAIL = 'Zachary Shaver', '36010164+ZacharyShaver@users.noreply.github.com'     # GitHub's noreply address, not the private one
NOREPLY = '@users.noreply.github.com'


def sh(*a, cwd=None):
    return subprocess.run(a, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def _safe(text):
    """Error text without anything that looks like a token, a credential in a URL or an email address."""
    text = re.sub(r'(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{10,}', '<token>', text or '')
    return re.sub(r'[^\s/@:]+@[^\s/]+', '<redacted>', text)


def _stopped(e):
    """One clean line for a failed command: its first two words and exit code, then the last lines of its output (redacted).
    The full command is not shown: the commit command carries the identity."""
    if isinstance(e, subprocess.CalledProcessError):
        words, skip = [], False
        for w in map(str, e.cmd if isinstance(e.cmd, (list, tuple)) else str(e.cmd).split()):
            if skip:
                skip = False
            elif w in ('-c', '-C'):                                    # git's option and its value (the identity, a path)
                skip = True
            elif not w.startswith('-'):
                words.append(w)
        words = words[:2]
        tail = ' / '.join(_safe(e.stderr if isinstance(e.stderr, str) else '').strip().splitlines()[-3:])
        return f"stopped: `{' '.join(map(str, words))}` failed (exit {e.returncode})" + (f': {tail}' if tail else '')
    return f'stopped: could not run a command ({type(e).__name__}); is gh/git installed?'


def held_items():
    """(id, reason) for each manifest item held back on purpose; they are not built, so they do not go out."""
    with open(B.MANIFEST, encoding='utf-8') as fh:
        manifest = json.load(fh)
    return [(it['id'], it['hold']) for s in manifest['sections'] for it in s['items'] if it.get('hold')]


def _say_held():
    held = held_items()
    if not held:
        return
    by_reason = {}
    for i, why in held:
        by_reason.setdefault(why, []).append(i)
    print(f'{len(held)} held back, not in this push:')
    for why, ids in by_reason.items():
        print(f"  {', '.join(ids)}: {why}")


def _publish(a):
    out = a.dry_run_dir or B.OUT
    if not a.dry_run_dir and B.main([]) != 0:
        print('the build failed its gates: nothing published'); return 1
    files = [f for _, _, fs in os.walk(out) for f in fs if f != B.MARKER]
    owner, name = a.repo.split('/')
    print(f'would push {len(files)} files from {B._shown(out)} to https://github.com/{a.repo} and serve https://{owner.lower()}.github.io/{name}/')
    _say_held()
    if not a.yes:
        print('not published: rerun with --yes once Zach has said yes'); return 2
    if not os.path.exists(os.path.join(out, 'index.html')):
        print('refusing: the build folder has no index.html'); return 1
    if subprocess.run(['gh', 'repo', 'view', a.repo], capture_output=True).returncode != 0:
        sh('gh', 'repo', 'create', a.repo, '--public', '--description', 'Scorpion robot: design pages and simulation results')
    with tempfile.TemporaryDirectory(prefix='gallery-publish-', ignore_cleanup_errors=True) as work:
        sh('gh', 'repo', 'clone', a.repo, work)
        for e in os.listdir(work):
            if e != '.git':
                p = os.path.join(work, e); shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
        top = os.path.abspath(out)
        shutil.copytree(out, work, dirs_exist_ok=True,                                  # the marker stays out of the public repo
                        ignore=lambda d, names: [B.MARKER] if os.path.abspath(d) == top and B.MARKER in names else [])
        src = sh('git', '-C', B.ROOT, 'rev-parse', '--short', 'HEAD')
        sh('git', 'add', '-A', cwd=work)
        if sh('git', 'status', '--porcelain', cwd=work):
            sh('git', '-c', f'user.name={NAME}', '-c', f'user.email={EMAIL}', 'commit', '-m',
               f'Gallery build from the design repository at {src}', cwd=work)
            emails = [x.strip() for x in sh('git', 'log', '--all', '--format=%ae%n%ce', cwd=work).splitlines() if x.strip()]
            bad = [x for x in emails if not x.lower().endswith(NOREPLY)]
            if bad:
                print('refusing to push: a commit carries a non-noreply email')
                print(f'({len(bad)} of {len(emails)} author and committer addresses; none shown)'); return 1
            sh('git', 'push', 'origin', 'HEAD:main', cwd=work)
        else:
            print('nothing changed since the last push')
    if subprocess.run(['gh', 'api', f'repos/{a.repo}/pages'], capture_output=True).returncode != 0:
        sh('gh', 'api', '-X', 'POST', f'repos/{a.repo}/pages', '-f', 'source[branch]=main', '-f', 'source[path]=/')
    print(f'published: https://{owner.lower()}.github.io/{name}/ (Pages can take a minute)'); return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description='Publish the gallery to a separate public repo (dry run unless --yes).')
    ap.add_argument('--repo', default=DEFAULT_REPO, help='OWNER/NAME of the public repo')
    ap.add_argument('--yes', action='store_true', help="push; only after Zach's yes in chat")
    ap.add_argument('--dry-run-dir', help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', a.repo):
        print('refusing: --repo must look like OWNER/NAME'); return 1
    if a.dry_run_dir and a.yes:
        print('refusing: --dry-run-dir skips the build and its gates, so it cannot be combined with --yes'); return 1
    try:
        return _publish(a)
    except (subprocess.CalledProcessError, OSError) as e:
        print(_stopped(e)); return 1


if __name__ == '__main__':
    sys.exit(main())
