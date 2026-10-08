#!/usr/bin/env python3
"""Enable WAL only after a verified SQLite backup; keep FULL commit durability."""
import argparse,json,sqlite3,os,stat
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('database');parser.add_argument('backup');args=parser.parse_args()
path=Path(args.database).resolve(strict=True);backup=Path(args.backup)
if backup.exists():raise SystemExit('Backup already exists; nothing overwritten')
info=path.stat()
# PHP and analysis use different accounts. WAL/SHM must inherit the shared DB group.
os.chown(path.parent,-1,info.st_gid)
os.chmod(path.parent,(path.parent.stat().st_mode&0o7777)|stat.S_ISGID|stat.S_IWGRP|stat.S_IXGRP)
os.chmod(path,(info.st_mode&0o777)|stat.S_IWGRP)
for shared in (path.with_name(path.name+'-wal'),path.with_name(path.name+'-shm')):
    if shared.exists():
        os.chown(shared,-1,info.st_gid);os.chmod(shared,(shared.stat().st_mode&0o777)|stat.S_IWGRP)
source=sqlite3.connect(str(path),timeout=30);saved=sqlite3.connect(str(backup))
try:
    source.backup(saved)
    assert saved.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
finally:saved.close()
try:
    old=source.execute('PRAGMA journal_mode').fetchone()[0];mode=source.execute('PRAGMA journal_mode=WAL').fetchone()[0]
    assert mode=='wal'
    source.execute('PRAGMA synchronous=FULL')
    assert source.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    print(json.dumps({'before':old,'after':mode,'synchronous':source.execute('PRAGMA synchronous').fetchone()[0],'backup':str(backup)}))
finally:source.close()
