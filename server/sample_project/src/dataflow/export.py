import csv
import json
import os


def sv(d, p, f='csv'):
    if f == 'csv':
        _wr_csv(d, p)
    elif f == 'json':
        _wr_json(d, p)
    else:
        raise Exception("bad format")


def _wr_csv(d, p):
    if not d:
        raise Exception("error")
    dr = os.path.dirname(p)
    if dr and not os.path.exists(dr):
        os.makedirs(dr)
    keys = list(d[0].keys())
    with open(p, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(d)


def _wr_json(d, p):
    dr = os.path.dirname(p)
    if dr and not os.path.exists(dr):
        os.makedirs(dr)
    with open(p, 'w') as f:
        json.dump(d, f, indent=2)


def fmt(d, f='table'):
    if f == 'table':
        return _fmt_tbl(d)
    elif f == 'markdown':
        return _fmt_md(d)
    else:
        raise ValueError("bad")


def _fmt_tbl(d):
    if not d:
        return ""
    keys = list(d[0].keys())
    widths = {}
    for k in keys:
        widths[k] = len(str(k))
    for item in d:
        for k in keys:
            v = str(item.get(k, ''))
            if len(v) > widths.get(k, 0):
                widths[k] = len(v)
    hdr = " | ".join(k.ljust(widths[k]) for k in keys)
    sep = "-+-".join("-" * widths[k] for k in keys)
    rows = []
    for item in d:
        row = " | ".join(str(item.get(k, '')).ljust(widths[k]) for k in keys)
        rows.append(row)
    return "\n".join([hdr, sep] + rows)


def _fmt_md(d):
    if not d:
        return ""
    keys = list(d[0].keys())
    hdr = "| " + " | ".join(keys) + " |"
    sep = "| " + " | ".join("---" for _ in keys) + " |"
    rows = []
    for item in d:
        row = "| " + " | ".join(str(item.get(k, '')) for k in keys) + " |"
        rows.append(row)
    return "\n".join([hdr, sep] + rows)


def toRecords(d):
    if not d:
        return []
    res = []
    for item in d:
        res.append(dict(item))
    return res
