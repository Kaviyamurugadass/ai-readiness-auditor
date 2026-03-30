def fl(lst):
    res = []
    for item in lst:
        if isinstance(item, list):
            res.extend(fl(item))
        else:
            res.append(item)
    return res


def mrg(d1, d2, k):
    lookup = {}
    for item in d2:
        lookup[item.get(k)] = item
    res = []
    for item in d1:
        merged = dict(item)
        match = lookup.get(item.get(k))
        if match:
            for mk, mv in match.items():
                if mk not in merged:
                    merged[mk] = mv
        res.append(merged)
    return res


def dd(lst, k=None):
    if k is None:
        seen = set()
        res = []
        for item in lst:
            s = str(item)
            if s not in seen:
                seen.add(s)
                res.append(item)
        return res
    else:
        seen = set()
        res = []
        for item in lst:
            v = item.get(k)
            if v not in seen:
                seen.add(v)
                res.append(item)
        return res


def chunker(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def countBy(d, k):
    counts = {}
    for item in d:
        v = item.get(k)
        counts[v] = counts.get(v, 0) + 1
    return counts


def pluck(d, k):
    return [item.get(k) for item in d]


def indexBy(d, k):
    res = {}
    for item in d:
        res[item.get(k)] = item
    return res


def deepGet(obj, path, default=None):
    keys = path.split('.')
    cur = obj
    for key in keys:
        if isinstance(cur, dict):
            cur = cur.get(key)
        else:
            return default
        if cur is None:
            return default
    return cur
