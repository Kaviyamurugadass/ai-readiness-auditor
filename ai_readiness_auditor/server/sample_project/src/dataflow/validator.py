import re


def chk(d, s):
    errs = []
    for i, item in enumerate(d):
        for k, rules in s.items():
            if 'required' in rules and rules['required']:
                if k not in item or item[k] is None:
                    errs.append(f"row {i}: missing {k}")
            if k in item and item[k] is not None:
                if 'type' in rules:
                    if not vld_tp(item[k], rules['type']):
                        errs.append(f"row {i}: bad type for {k}")
                if 'min' in rules:
                    try:
                        if float(item[k]) < rules['min']:
                            errs.append(f"row {i}: {k} too small")
                    except:
                        pass
                if 'max' in rules:
                    try:
                        if float(item[k]) > rules['max']:
                            errs.append(f"row {i}: {k} too big")
                    except:
                        pass
                if 'pattern' in rules:
                    if not re.match(rules['pattern'], str(item[k])):
                        errs.append(f"row {i}: {k} bad format")
    return errs


def vld_tp(v, t):
    if t == 'int':
        try:
            int(v)
            return True
        except:
            return False
    elif t == 'float':
        try:
            float(v)
            return True
        except:
            return False
    elif t == 'str':
        return isinstance(v, str)
    elif t == 'bool':
        return isinstance(v, bool) or v in ('true', 'false', 'True', 'False', '0', '1')
    else:
        raise ValueError("bad")


def chkEmpty(d):
    if not d:
        return True
    if len(d) == 0:
        return True
    return False


def chkDups(d, k):
    seen = set()
    dups = []
    for i, item in enumerate(d):
        v = item.get(k)
        if v in seen:
            dups.append(i)
        seen.add(v)
    return dups


def cleanData(d):
    res = []
    for item in d:
        new = {}
        for k, v in item.items():
            if isinstance(v, str):
                v = v.strip()
            if v is not None and v != '':
                new[k] = v
        if new:
            res.append(new)
    return res


def chkSchema(d, required_cols):
    if not d:
        raise Exception("error")
    first = d[0]
    missing = []
    for c in required_cols:
        if c not in first:
            missing.append(c)
    if missing:
        raise ValueError("bad")
    return True
