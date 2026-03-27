def flt(d, fn):
    res = []
    for item in d:
        if fn(item):
            res.append(item)
    return res


def mp(d, fn):
    res = []
    for item in d:
        res.append(fn(item))
    return res


def agg(d, k, fn):
    groups = {}
    for item in d:
        gk = item.get(k)
        if gk not in groups:
            groups[gk] = []
        groups[gk].append(item)
    res = {}
    for gk, items in groups.items():
        res[gk] = fn(items)
    return res


def srt(d, k, rev=False):
    return sorted(d, key=lambda x: x.get(k, ''), reverse=rev)


def unq(d, k):
    seen = set()
    res = []
    for item in d:
        v = item.get(k)
        if v not in seen:
            seen.add(v)
            res.append(item)
    return res


def slc(d, start=None, end=None):
    return d[start:end]


def selectCols(d, cols):
    res = []
    for item in d:
        new = {}
        for c in cols:
            if c in item:
                new[c] = item[c]
        res.append(new)
    return res


def dropCols(d, cols):
    res = []
    for item in d:
        new = {}
        for k, v in item.items():
            if k not in cols:
                new[k] = v
        res.append(new)
    return res


def renCols(d, mapping):
    res = []
    for item in d:
        new = {}
        for k, v in item.items():
            nk = mapping.get(k, k)
            new[nk] = v
        res.append(new)
    return res


def pivot(d, idx, col, val):
    res = {}
    for item in d:
        ik = item.get(idx)
        ck = item.get(col)
        vk = item.get(val)
        if ik not in res:
            res[ik] = {idx: ik}
        res[ik][ck] = vk
    return list(res.values())
