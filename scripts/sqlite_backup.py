#!/usr/bin/env python3
"""SQLite backup API also includes committed pages still in WAL."""
import argparse,os,sqlite3
from pathlib import Path
def backup(source,destination,replace=False):
    source=Path(source).resolve(strict=True);destination=Path(destination)
    if source==destination.resolve():raise ValueError('Source and destination must differ')
    if destination.exists() and not replace:raise FileExistsError(destination)
    read=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True,timeout=30)
    write=sqlite3.connect(str(destination),timeout=30)
    try:
        read.backup(write,pages=256,sleep=.01)
        if write.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('Invalid database backup')
    finally:read.close();write.close()
    if not replace:os.chmod(destination,source.stat().st_mode&0o777)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source');parser.add_argument('destination');parser.add_argument('--replace',action='store_true');args=parser.parse_args()
    backup(args.source,args.destination,args.replace)
