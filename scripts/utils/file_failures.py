"""Preserve bad recordings and prevent unchanged failures restarting forever."""
import hashlib
import json
import os
from pathlib import Path
import time

class InvalidRecording(ValueError):
    """A completed recording has an invalid name or invalid audio content."""

def fingerprint(path):
    path=Path(path);info=path.stat()
    return hashlib.sha256(f'{path.resolve()}\0{info.st_size}\0{info.st_mtime_ns}'.encode()).hexdigest()

def ledger_path():
    return Path(__file__).resolve().parents[2]/'.analysis-failures.json'

def failures():
    try:return json.loads(ledger_path().read_text())
    except FileNotFoundError:return {}

def blocked(path):
    try:return fingerprint(path) in failures()
    except FileNotFoundError:return False

def preserve_failure(path,error,quarantine=False):
    from .helpers import get_settings
    path=Path(path);key=fingerprint(path);rows=failures()
    row={'source':str(path),'error':str(error),'type':type(error).__name__,'time':time.time(),'quarantined':False}
    if quarantine:
        folder=Path(get_settings()['RECS_DIR'])/'Quarantine'
        if folder.is_symlink():raise ValueError('Quarantine directory cannot be a symlink')
        folder.mkdir(mode=0o700,exist_ok=True)
        target=folder/(key[:16]+'-'+path.name)
        if target.exists():raise FileExistsError('Quarantine collision; original retained')
        os.rename(path,target)
        row.update(quarantined=True,retained=str(target))
        target.with_name(target.name+'.error.json').write_text(json.dumps(row,indent=2))
    rows[key]=row
    destination=ledger_path();temporary=destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(rows,indent=2));os.chmod(temporary,0o600);os.replace(temporary,destination)
    return row
