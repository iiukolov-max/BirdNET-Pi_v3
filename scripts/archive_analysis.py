"""Manual analysis of a snapshot of completed archive recordings."""
import datetime as dt
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import shutil
from archive_recording import PATTERN
from utils.helpers import get_settings, BASE_PATH, DB_PATH

BASE=Path(BASE_PATH)
STATE=BASE/'.archive-analysis.json'


def files():
    root=Path(get_settings()['RECS_DIR'])/'Archive'
    if root.is_symlink() or not (root/'.birdnet-archive').is_file():return []
    return sorted(p for p in root.iterdir() if PATTERN.fullmatch(p.name) and p.is_file() and not p.is_symlink())


def key(path):
    s=path.stat()
    return (path.name,s.st_size,s.st_mtime_ns)


def completed():
    with sqlite3.connect('file:'+DB_PATH+'?mode=ro',uri=True,timeout=10) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='archive_processed'").fetchone():return set()
        return set(db.execute('SELECT name,size,mtime FROM archive_processed'))


def pending():
    done=completed();result=[]
    for p in files():
        try:
            if key(p) not in done:result.append(p)
        except FileNotFoundError:pass
    return result


def publish(state):
    tmp=STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(state));os.replace(tmp,STATE)


def status():
    try:state=json.loads(STATE.read_text())
    except (FileNotFoundError,ValueError):state={}
    active=False
    pid=state.get('pid',0)
    if pid>1:
        try:active=b'archive_analysis.py' in Path('/proc/'+str(pid)+'/cmdline').read_bytes()
        except FileNotFoundError:pass
    if state.get('status') in ('loading','running') and not active:state['status']='interrupted'
    state['active']=active
    try:
        pause=json.loads(Path('/run/birdnet-archive-recording-pause.json').read_text())
        state['recording_paused']=bool(pause.get('resume'))
        if pause and not active:
            # The hook can precede the new worker; persisted counters belong
            # to the previous invocation and must not produce a new ETA.
            state={key:value for key,value in state.items() if key=='recording_paused'}
            state['active']=active=True
            state['status']='loading'
    except (FileNotFoundError,ValueError):
        state['recording_paused']=False
    waiting=pending()
    state['pending']=len(waiting)
    snapshot=set(state.pop('snapshot',[]))
    state['new_pending']=sum(p.name not in snapshot for p in waiting) if active and snapshot else 0
    count=state.get('processed',0);total=state.get('total',0)
    seconds=state.get('processing_seconds',0)
    elapsed=max(0,time.time()-state.get('started',time.time()))
    state['elapsed_seconds']=elapsed
    state['files_per_minute']=60*count/seconds if count and seconds else None
    remaining=max(0,total-count-state.get('failed',0)-state.get('missing',0))
    state['job_remaining']=remaining
    eta=max(0,seconds/count*remaining-(time.time()-state.get('current_started',time.time()))) if active and state.get('status')=='running' and count else None
    state['eta_seconds']=eta
    state['expected_finish']=dt.datetime.fromtimestamp(time.time()+eta).astimezone().isoformat() if eta is not None else None
    conf=get_settings();disk=shutil.disk_usage(conf['RECS_DIR'])
    threshold=int(conf.get('ARCHIVE_MAX_USED_PERCENT','85'))
    available=max(0,disk.free-max(disk.total*(100-threshold)/100,1024**3))
    storage={'free_bytes':disk.free,'total_bytes':disk.total,'max_used_percent':threshold,'available_before_cleanup_bytes':int(available),'estimated_files':None,'estimated_days':None}
    try:
        rate=json.loads((BASE/'.archive-rate.json').read_text())
        if rate['format']==conf.get('AUDIOFMT') and rate['segment_seconds']==int(conf.get('RECORDING_LENGTH','15')):
            storage['estimated_files']=int(available/(rate['bytes_per_second']*rate['segment_seconds']))
            storage['estimated_days']=available/rate['bytes_per_second']/86400
    except (FileNotFoundError,ValueError,KeyError,ZeroDivisionError):pass
    state['storage']=storage
    return state


def decode_archive(source, wav):
    """Decode in process to avoid evicting the acoustic model for each file."""
    import soundfile as sf
    try:
        source.seek(0)
        audio, rate = sf.read(source, dtype='int16', always_2d=True)
        if not len(audio):
            raise ValueError('Empty archive recording')
        sf.write(str(wav), audio, rate, subtype='PCM_16')
    except (RuntimeError, ValueError):
        # Preserve support for inputs that the installed libsndfile cannot read.
        source.seek(0)
        subprocess.run(['ffmpeg','-v','error','-nostdin','-i','pipe:0',
                        '-c:a','pcm_s16le','-y',str(wav)],
                       stdin=source,check=True,timeout=120)


def worker():
    if get_settings().get('OPERATION_MODE','normal')!='archive':raise RuntimeError('Archive mode required')
    import fcntl
    import signal
    def interrupted(signum,frame):raise InterruptedError('Archive analysis stopped')
    signal.signal(signal.SIGTERM,interrupted)
    lock=(BASE/'.analysis-instance.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    queue=pending()
    state=dict(status='loading',pid=os.getpid(),started=time.time(),processed=0,failed=0,missing=0,total=len(queue),processing_seconds=0,snapshot=[p.name for p in queue])
    publish(state)
    if not queue:state['status']='done';publish(state);return
    from utils.analysis import load_global_model,run_analysis
    from utils.classes import ParseFileName
    from utils.reporting import extract_detection
    load_global_model()
    state['status']='running';publish(state)
    try:
        for path in queue:
            began=time.time();state.update(current=path.name,current_started=began);publish(state)
            try:
                # Open before cleanup can unlink it; decode from this descriptor into RAM.
                with path.open('rb') as source:
                    info=os.fstat(source.fileno())
                    fingerprint=(path.name,info.st_size,info.st_mtime_ns)
                    with tempfile.TemporaryDirectory(prefix='birdnet-archive-') as folder:
                        wav=Path(folder)/(path.stem+'.wav')
                        decode_archive(source, wav)
                        parsed=ParseFileName(str(wav));detections=run_analysis(parsed)
                        for d in detections:d.file_name_extr=extract_detection(parsed,d)
                        conf=get_settings()
                        with sqlite3.connect(DB_PATH,timeout=30) as db:
                            db.execute('CREATE TABLE IF NOT EXISTS archive_processed (name TEXT,size INTEGER,mtime INTEGER,processed REAL,PRIMARY KEY(name,size,mtime))')
                            if not db.execute('SELECT 1 FROM archive_processed WHERE name=? AND size=? AND mtime=?',fingerprint).fetchone():
                                for d in detections:
                                    db.execute('INSERT INTO detections VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(d.date,d.time,d.scientific_name,d.common_name,d.confidence,conf['LATITUDE'],conf['LONGITUDE'],conf['CONFIDENCE'],str(d.week),conf['SENSITIVITY'],conf['OVERLAP'],os.path.basename(d.file_name_extr)))
                                db.execute('INSERT INTO archive_processed VALUES (?,?,?,?)',(*fingerprint,time.time()))
                try:
                    if key(path)==fingerprint:path.unlink()
                except FileNotFoundError:pass
                state['processed']+=1
                state['processing_seconds']+=time.time()-began
                print(json.dumps({'event':'archive_analyzed','file':path.name,'detections':len(detections),'seconds':time.time()-began}),flush=True)
            except InterruptedError:
                raise
            except FileNotFoundError:
                state['missing']+=1
            except Exception as error:
                state['failed']+=1;state['last_error']=str(error)
                print(json.dumps({'file':path.name,'error':str(error)}),flush=True)
            publish(state)
        state['status']='done' if not state['failed'] else 'done_with_errors'
    except BaseException as error:
        state['status']='interrupted';state['last_error']=str(error);raise
    finally:
        state['finished']=time.time();state['current']=None;publish(state)


if __name__=='__main__':
    if sys.argv[1:]==['status']:print(json.dumps(status()))
    elif sys.argv[1:]==['worker']:worker()
    else:raise SystemExit('Expected status or worker')
