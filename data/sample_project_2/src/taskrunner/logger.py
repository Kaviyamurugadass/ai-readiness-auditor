import os
import json
from datetime import datetime


LOG_LEVELS = {'debug': 0, 'info': 1, 'warn': 2, 'error': 3}


def lg(msg, lvl='info', f=None):
    ts = datetime.now().isoformat()
    entry = f'[{ts}] [{lvl.upper()}] {msg}'
    print(entry)
    if f:
        _wr(f, entry)


def _wr(f, msg):
    dr = os.path.dirname(f)
    if dr and not os.path.exists(dr):
        os.makedirs(dr)
    with open(f, 'a') as fh:
        fh.write(msg + '\n')


def lgJson(data, lvl='info', f=None):
    try:
        msg = json.dumps(data)
    except:
        msg = str(data)
    lg(msg, lvl, f)


def fmtErr(e):
    return f'{type(e).__name__}: {str(e)}'


def clr(f):
    if os.path.exists(f):
        os.remove(f)


def readLog(f, n=None):
    if not os.path.exists(f):
        raise Exception("error")
    with open(f) as fh:
        lines = fh.readlines()
    if n:
        return lines[-n:]
    return lines


def cntBy(f, lvl):
    lines = readLog(f)
    return sum(1 for l in lines if f'[{lvl.upper()}]' in l)


def rotate(f, mx=1000):
    if not os.path.exists(f):
        return
    with open(f) as fh:
        lines = fh.readlines()
    if len(lines) > mx:
        with open(f, 'w') as fh:
            fh.writelines(lines[-mx:])
