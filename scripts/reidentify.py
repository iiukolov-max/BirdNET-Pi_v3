#!/usr/bin/env python3
"""Rename one detection with bound SQL and preserve its review record."""
import argparse,fcntl,os,sqlite3
from pathlib import Path

def contained(base,path):
    resolved=path.resolve(strict=True)
    if not resolved.is_relative_to(base.resolve()) or resolved==base.resolve():raise ValueError('Path outside detection archive')
    return resolved

def reidentify(database,base,labels,oldname,newname):
    base=Path(base).resolve(strict=True)
    if Path(oldname).name!=oldname or '\\' in oldname:raise ValueError('Expected a recording basename')
    if newname not in Path(labels).read_text(encoding='utf-8').splitlines():raise ValueError('Select an existing species label')
    scientific,common=newname.split('_',1);safe=common.replace("'",'').replace(' ','_')
    if safe in ('','.','..') or '/' in safe or '\\' in safe:raise ValueError('Invalid species directory')
    with (base.parent/'.reidentify.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        db=sqlite3.connect(str(database),timeout=8);moves=[]
        try:
            db.execute('BEGIN IMMEDIATE')
            rows=db.execute('SELECT Date,Com_Name FROM detections WHERE File_Name=?',(oldname,)).fetchall()
            if len(rows)!=1:raise ValueError('Expected exactly one matching detection')
            date,oldcommon=rows[0];oldsafe=oldcommon.replace("'",'').replace(' ','_')
            if common==oldcommon:raise ValueError('Species is unchanged')
            source=contained(base,base/date/oldsafe/oldname)
            filename=oldname.replace(oldsafe,safe,1)
            folder=base/date/safe
            folder.mkdir(parents=True,exist_ok=True);contained(base,folder)
            target=folder/filename
            for old,new in [(source,target),(source.with_name(source.name+'.png'),target.with_name(target.name+'.png'))]:
                if not old.exists():continue
                contained(base,old)
                if new.exists():raise FileExistsError('Destination already exists')
                os.rename(old,new);moves.append((old,new))
            db.execute('UPDATE detections SET Sci_Name=?,Com_Name=?,Confidence=0,File_Name=? WHERE File_Name=?',(scientific,common,filename,oldname))
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='detection_reviews'").fetchone():
                db.execute('UPDATE detection_reviews SET file_path=? WHERE file_path=?',(f'{date}/{safe}/{filename}',f'{date}/{oldsafe}/{oldname}'))
            db.commit()
            return filename
        except BaseException:
            db.rollback()
            for old,new in reversed(moves):os.rename(new,old)
            raise
        finally:db.close()

if __name__=='__main__':
    from utils.helpers import get_settings,DB_PATH,MODEL_PATH
    parser=argparse.ArgumentParser();parser.add_argument('oldname');parser.add_argument('newname');parser.add_argument('logging',nargs='?');args=parser.parse_args()
    print(reidentify(DB_PATH,Path(get_settings()['EXTRACTED'])/'By_Date',Path(MODEL_PATH)/'labels.txt',args.oldname,args.newname))
