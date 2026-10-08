#!/usr/bin/env python3
"""Inspect retained failures or explicitly make an unchanged source eligible again."""
import argparse,json,os
from pathlib import Path
from utils.file_failures import failures,ledger_path
parser=argparse.ArgumentParser()
parser.add_argument('action',choices=['list','retry','restore'])
parser.add_argument('id',nargs='?')
args=parser.parse_args();rows=failures()
if args.action=='list':print(json.dumps(rows,indent=2));raise SystemExit
if args.id not in rows:raise SystemExit('Select an existing failure ID from list')
row=rows[args.id]
if args.action=='restore':
    if not row['quarantined']:raise SystemExit('Source is already retained in its original location; use retry')
    source=Path(row['source']);retained=Path(row['retained'])
    if source.exists():raise SystemExit('Original path already exists; nothing overwritten')
    os.rename(retained,source)
elif row['quarantined']:raise SystemExit('Use restore for a quarantined recording')
del rows[args.id]
temporary=ledger_path().with_suffix('.tmp');temporary.write_text(json.dumps(rows,indent=2));os.chmod(temporary,0o600);os.replace(temporary,ledger_path())
print('Recording is eligible for analysis again; start analysis when ready.')
