"""Remove unchanged archive sources only with a durable zero-detection result."""
from contextlib import closing
from pathlib import Path
import sqlite3
import stat
import time


def ensure_history(db):
    """Keep history separate from the older, four-column completion ledger."""
    db.execute('CREATE TABLE IF NOT EXISTS archive_analysis_results '
               '(name TEXT,size INTEGER,mtime INTEGER,detections INTEGER NOT NULL,'
               'PRIMARY KEY(name,size,mtime))')
    columns={row[1] for row in db.execute('PRAGMA table_info(archive_analysis_results)')}
    for name,definition in [('analyzed_at','REAL'),('backend',"TEXT DEFAULT 'unknown'"),
                            ('seconds','REAL'),('outcome',"TEXT DEFAULT 'ok'"),
                            ('error','TEXT'),('evidence',"TEXT DEFAULT 'live'")]:
        if name not in columns:db.execute('ALTER TABLE archive_analysis_results ADD COLUMN '+name+' '+definition)


def record_result(db, identity, detections, backend='remote', seconds=None,
                  outcome='ok', error=None, evidence='live', analyzed_at=None):
    """Called inside the same transaction that commits archive_processed."""
    ensure_history(db)
    db.execute('INSERT INTO archive_analysis_results '
               '(name,size,mtime,detections,analyzed_at,backend,seconds,outcome,error,evidence) '
               'VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(name,size,mtime) DO UPDATE SET '
               'detections=excluded.detections,analyzed_at=excluded.analyzed_at,backend=excluded.backend,'
               'seconds=excluded.seconds,outcome=excluded.outcome,error=excluded.error,evidence=excluded.evidence',
               (*identity,detections,time.time() if analyzed_at is None else analyzed_at,
                backend,seconds,outcome,error,evidence))


def record_failure(path, database, error, backend, seconds=None):
    """Failures remain visible even though no completion is committed."""
    import json
    from utils.database import connect
    try:
        info=Path(path).lstat()
        identity=(Path(path).name,info.st_size,info.st_mtime_ns)
        with closing(connect(database,timeout=30)) as db, db:
            record_result(db,identity,-1,backend,seconds,'error',str(error)[:1000])
    except (OSError,sqlite3.Error) as history_error:
        print(json.dumps({'event':'archive_history_write_failed','file':Path(path).name,'error':str(history_error)}),flush=True)


def remove_empty_source(path, identity, database):
    path = Path(path)
    with closing(sqlite3.connect('file:' + str(database) + '?mode=ro', uri=True, timeout=30)) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='archive_analysis_results'").fetchone():
            return 'retained_unknown'
        row = db.execute('SELECT r.detections FROM archive_analysis_results r '
                         'JOIN archive_processed p USING(name,size,mtime) '
                         "WHERE r.name=? AND r.size=? AND r.mtime=? AND r.outcome='ok'", identity).fetchone()
    if row is None:
        return 'retained_unknown'
    if row[0] != 0:
        return 'retained_detections'
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or (path.name, info.st_size, info.st_mtime_ns) != identity:
            return 'retained_changed'
        if info.st_nlink != 1:
            return 'retained_shared'
        path.unlink()
        return 'removed'
    except FileNotFoundError:
        return 'missing'
