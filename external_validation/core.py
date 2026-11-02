import csv, hashlib, json, math
from pathlib import Path


def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def read_csv(path,fields):
    with open(path,newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        if not fields.issubset(set(reader.fieldnames or [])):
            raise ValueError(f'{path}: missing {sorted(fields-set(reader.fieldnames or []))}; found {reader.fieldnames}')
        return list(reader)


def integer(x,label):
    s=str(x).strip()
    if not s or not s.lstrip('-').isdigit():raise ValueError(f'{label}: expected integer, got {x!r}')
    return int(s)


def wilson(failures,trials,z=1.95996398454):
    if trials<=0 or not 0<=failures<=trials:raise ValueError('invalid binomial counts')
    p=failures/trials; d=1+z*z/trials
    c=(p+z*z/(2*trials))/d
    r=z*math.sqrt(p*(1-p)/trials+z*z/(4*trials*trials))/d
    return {'rate':p,'ci95':[max(0,c-r),min(1,c+r)],'failures':failures,'trials':trials}


def write_json(path,payload):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(payload,indent=2,sort_keys=True,allow_nan=False)+'\n')


def source_manifest(paths):
    return [{'path':str(p),'sha256':digest(p),'bytes':Path(p).stat().st_size} for p in paths]
