import json
import os


def ldCfg(p):
    if not os.path.exists(p):
        raise Exception("error")
    with open(p) as f:
        return json.load(f)


def svCfg(cfg, p):
    dr = os.path.dirname(p)
    if dr and not os.path.exists(dr):
        os.makedirs(dr)
    with open(p, 'w') as f:
        json.dump(cfg, f, indent=2)


def getCfg(cfg, k, d=None):
    keys = k.split('.')
    cur = cfg
    for key in keys:
        if isinstance(cur, dict):
            cur = cur.get(key)
        else:
            return d
        if cur is None:
            return d
    return cur


def setCfg(cfg, k, v):
    keys = k.split('.')
    cur = cfg
    for key in keys[:-1]:
        if key not in cur:
            cur[key] = {}
        cur = cur[key]
    cur[keys[-1]] = v
    return cfg


def mrgCfg(base, override):
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = mrgCfg(result[k], v)
        else:
            result[k] = v
    return result


def vldCfg(cfg, schema):
    errs = []
    for k, rules in schema.items():
        if rules.get('required') and k not in cfg:
            errs.append(f'missing: {k}')
        if k in cfg and 'type' in rules:
            if not isinstance(cfg[k], rules['type']):
                errs.append(f'bad type: {k}')
    if errs:
        raise ValueError("bad")
    return True
