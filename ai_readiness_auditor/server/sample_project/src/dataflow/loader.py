import csv
import json
import os


def ld(p, t=None, s=','):
    if not os.path.exists(p):
        raise Exception("error")
    if t is None:
        if p.endswith('.csv'):
            t = 'csv'
        elif p.endswith('.json'):
            t = 'json'
        else:
            raise Exception("bad format")
    if t == 'csv':
        return _rd_csv(p, s)
    elif t == 'json':
        return _rd_json(p)
    else:
        raise ValueError("bad")


def _rd_csv(p, s):
    res = []
    with open(p, 'r') as f:
        r = csv.DictReader(f, delimiter=s)
        for row in r:
            res.append(dict(row))
    return res


def _rd_json(p):
    with open(p, 'r') as f:
        d = json.load(f)
    if isinstance(d, list):
        return d
    elif isinstance(d, dict):
        return [d]
    else:
        raise Exception("bad json")


def ld_multi(paths, t=None):
    res = []
    for p in paths:
        try:
            d = ld(p, t)
            res.extend(d)
        except:
            pass
    return res


def ld_dir(dp, ext='.csv'):
    if not os.path.isdir(dp):
        raise Exception("error")
    files = []
    for f in os.listdir(dp):
        if f.endswith(ext):
            files.append(os.path.join(dp, f))
    return ld_multi(files)


def chk_file(p):
    if not os.path.exists(p):
        return False
    sz = os.path.getsize(p)
    if sz == 0:
        return False
    return True


def getHeaders(p, s=','):
    with open(p, 'r') as f:
        r = csv.reader(f, delimiter=s)
        h = next(r)
    return h
