#!/usr/bin/env python3
"""Normal-mode purge: closed detection audio only, preserve explicit exclusions."""
import argparse,fcntl,json,re
from pathlib import Path
import shutil,stat,subprocess
from utils.helpers import get_settings

EXTENSIONS={'.wav','.flac','.mp3','.ogg','.opus'}
def cleanup(base,protected,threshold=95,behavior='purge',usage=shutil.disk_usage,dry_run=False):
    base=Path(base).resolve(strict=True)
    if base.name!='By_Date' or base==Path('/'):raise ValueError('Expected extracted By_Date directory')
    if not 50<=threshold<=99:raise ValueError('Invalid purge threshold')
    def full():
        disk=usage(base);return 100*(disk.total-disk.free)/disk.total>=threshold
    if not full():return {'deleted':0,'full':False,'dry_run':dry_run}
    if behavior!='purge':return {'deleted':0,'full':True,'dry_run':dry_run}
    candidates=[]
    for day in sorted(base.iterdir()):
        if day.is_symlink() or not day.is_dir() or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day.name):continue
        for species in sorted(day.iterdir()):
            if species.is_symlink() or not species.is_dir():continue
            for path in sorted(species.iterdir()):
                relative=path.relative_to(base).as_posix()
                try:info=path.lstat()
                except FileNotFoundError:continue
                if not stat.S_ISREG(info.st_mode) or path.suffix.lower() not in EXTENSIONS or relative in protected or relative+'.png' in protected:continue
                candidates.append((day.name,path,info.st_ino,info.st_dev))
    candidates.sort(key=lambda item:(item[0],item[1].name))
    deleted=0;planned=[]
    for _,path,inode,device in candidates:
        if deleted%25==0 and not full():break
        try:info=path.lstat()
        except FileNotFoundError:continue
        if not stat.S_ISREG(info.st_mode) or (info.st_ino,info.st_dev)!=(inode,device):continue
        planned.append(str(path.relative_to(base)))
        if not dry_run:
            try:path.unlink()
            except FileNotFoundError:continue
            png=path.with_name(path.name+'.png');relative=png.relative_to(base).as_posix()
            if relative not in protected and png.exists() and not png.is_symlink() and png.is_file():png.unlink()
        deleted+=1
    return {'deleted':0 if dry_run else deleted,'planned':planned,'full':full(),'dry_run':dry_run}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
    conf=get_settings()
    if conf.get('OPERATION_MODE','normal')=='archive':return
    base=Path(conf['EXTRACTED'])/'By_Date'
    if not base.exists():raise ValueError('Extracted directory is missing')
    with (base.parent/'.normal-cleanup.lock').open('a') as stream:
        try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        excludes=Path(__file__).parent/'disk_check_exclude.txt'
        if not excludes.is_file():raise ValueError('Protection list missing; refusing purge')
        lines=excludes.read_text().splitlines()
        if '##start' not in lines:raise ValueError('Protection list invalid; refusing purge')
        result=cleanup(base,set(lines),int(conf.get('PURGE_THRESHOLD','95')),conf.get('FULL_DISK','purge'),dry_run=args.dry_run)
        print(json.dumps(result))
        if result['full'] and not args.dry_run:subprocess.run(['/usr/local/bin/stop_core_services.sh'],check=True)

if __name__=='__main__':main()
