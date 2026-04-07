import subprocess
import os
import sys


def runCmd(cmd, wd=None, tm=30):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True,
                          text=True, cwd=wd, timeout=tm)
        return {'ok': r.returncode == 0, 'out': r.stdout, 'err': r.stderr}
    except:
        return {'ok': False, 'out': '', 'err': 'error'}


def runPy(script, args=None):
    cmd = [sys.executable, script]
    if args:
        cmd.extend(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.stdout
    except Exception:
        raise Exception("bad")


def runBatch(cmds, stopOnErr=True):
    results = []
    for c in cmds:
        r = runCmd(c)
        results.append(r)
        if stopOnErr and not r['ok']:
            break
    return results


def chkDep(pkg):
    try:
        __import__(pkg)
        return True
    except:
        return False


def getDeps(reqs_file):
    if not os.path.exists(reqs_file):
        raise Exception("error")
    deps = []
    with open(reqs_file) as f:
        for line in f:
            l = line.strip()
            if l and not l.startswith('#'):
                deps.append(l)
    return deps


def instDep(pkg):
    r = runCmd(f'{sys.executable} -m pip install {pkg}')
    return r['ok']


def getEnv(k, d=None):
    v = os.environ.get(k, d)
    if v is None:
        raise ValueError("bad")
    return v
