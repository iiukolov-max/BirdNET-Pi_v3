"""Read durable archive results, independently of system journal retention."""
import argparse
import csv
from contextlib import closing
import json
import sqlite3
import sys


def rows(database, limit=100):
    with closing(sqlite3.connect('file:'+str(database)+'?mode=ro',uri=True,timeout=30)) as db:
        db.row_factory=sqlite3.Row
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='archive_analysis_results'").fetchone():return []
        return [dict(row) for row in db.execute(
            'SELECT name,size,mtime,analyzed_at,backend,outcome,detections,seconds,error,evidence '
            'FROM archive_analysis_results ORDER BY analyzed_at DESC LIMIT ?', (limit,))]


def main():
    from utils.helpers import DB_PATH
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit',type=int,default=100,help='Number of results; -1 exports all')
    parser.add_argument('--format',choices=['json','csv'],default='json')
    args=parser.parse_args()
    if args.limit==0 or args.limit < -1:parser.error('limit must be positive or -1')
    data=rows(DB_PATH,args.limit)
    if args.format=='json':print(json.dumps(data,ensure_ascii=False,indent=2))
    else:
        writer=csv.DictWriter(sys.stdout,fieldnames=['name','size','mtime','analyzed_at','backend','outcome','detections','seconds','error','evidence'])
        writer.writeheader();writer.writerows(data)


if __name__=='__main__':main()
