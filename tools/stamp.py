"""A results file a long run appends to and resumes from must hold rows from one version of the code. knobs.py resumed by
(tag, knobs, seed) alone, so a sweep stopped before G3 changed (2026-10-28) and resumed after would have mixed both G3s
in one file, unseen (code review, 2026-10-30).

    import stamp
    stamp.check(path)               # before resuming: refuses rows made by other code
    stamp.check(path, fresh=True)   # a run that starts the file over: just stamp it

The stamp is a sidecar, <path>.stamp.json: a hash of every repo module this process has loaded. Call check() once the
job list is built, so the modules the jobs use are loaded; one a worker imports later isn't seen. An empty or missing
results file takes the current stamp. A resume needs the stamps to match, or it stops and names the files that differ.
--resume-anyway on the command line resumes regardless, and the sidecar logs the mix."""
import hashlib, json, os, sys, time
import config


def sources():
    """repo path -> hash of its text, for every module loaded from the repo"""
    repo = os.path.normcase(config.REPO) + os.sep
    out = {}
    for m in list(sys.modules.values()):
        f = getattr(m, '__file__', None)
        if not f or not f.endswith('.py'):
            continue
        f = os.path.abspath(f)
        if not os.path.normcase(f).startswith(repo):
            continue
        with open(f, 'rb') as fh:
            out[os.path.relpath(f, config.REPO).replace(os.sep, '/')] = hashlib.sha1(fh.read().replace(b'\r\n', b'\n')).hexdigest()[:12]
    return dict(sorted(out.items()))


def _write(side, rec):
    with open(side, 'w') as fh:
        json.dump(rec, fh, indent=1)


def check(path, fresh=False):
    side = path + '.stamp.json'
    now = sources(); when = time.strftime('%Y-%m-%d %H:%M')
    if fresh or not os.path.isfile(path) or os.path.getsize(path) == 0:
        _write(side, dict(made=when, files=now, mixed=[]))
        return
    old = json.load(open(side)) if os.path.isfile(side) else None
    if old is not None and old['files'] == now:
        return
    if old is None:
        changed = ['no stamp: the file was made before stamps (2026-10-30), by code that can no longer be told']
    else:
        was = old['files']
        changed = sorted(f for f in set(was) | set(now) if was.get(f) != now.get(f))
    if '--resume-anyway' not in sys.argv:
        raise SystemExit('%s holds rows made by other code:\n  %s\nStart it over (move the file aside) or, to mix the '
                         'two on purpose, add --resume-anyway.' % (path, '\n  '.join(changed)))
    rec = old or dict(made=None, files={}, mixed=[])
    rec['mixed'].append(dict(at=when, changed=changed)); rec['files'] = now
    _write(side, rec)
    print('%s: resuming over other code, logged in %s' % (path, side), flush=True)
