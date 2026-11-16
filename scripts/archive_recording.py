"""Stream microphone PCM directly into encoded segments; retain complete audio."""
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import re
import queue
import threading
import shutil
import signal
import stat
import subprocess
import time
from utils.audio_log import emit
from utils.audio_snapshot import read as read_audio
from utils.audio_metrics import Levels, Period, StderrTail

FORMATS = {'flac': ('flac', 'flac'), 'mp3': ('libmp3lame', 'mp3'),
           'ogg': ('libvorbis', 'ogg'), 'opus': ('libopus', 'ogg'), 'wav': ('pcm_s16le', 'wav')}
PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}-birdnet-\d{2}:\d{2}:\d{2}\.(flac|mp3|ogg|opus|wav)$')


def cleanup_limit(previous, path=Path('/etc/birdnet/birdnet.conf')):
    """Reload only the live cleanup threshold; keep capture settings stable."""
    try:
        match = re.search(r'^ARCHIVE_MAX_USED_PERCENT="?(\d+)"?\s*$', path.read_text(), re.M)
        value = int(match[1]) if match else previous
        return value if 50 <= value <= 95 else previous
    except (OSError, ValueError):
        return previous


def log(event, **data):
    print(json.dumps(dict(event=event, time=dt.datetime.now().astimezone().isoformat(), **data)), flush=True)
    if event != 'archive_segment_completed' or data.get('first_segment'):
        emit(event, 'archive_recording', repeat=event != 'archive_segment_completed',
             interval=86400 if event in {'archive_recovery_required','archive_microphone_unavailable'} else 600,
             lane='' if event in {'archive_started','archive_stopped','archive_microphone_unavailable'}
             else event + str(data.get('path','')), **data)


def disk_free(root):
    try:return shutil.disk_usage(root).free
    except OSError:return None


def cleanup(root, trigger=85, target=85, batch=100, usage=shutil.disk_usage):
    """Delete only closed recorder-owned archive files, never detection audio."""
    root = Path(root)
    if root.is_symlink() or not (root / '.birdnet-archive').is_file():
        raise ValueError('Unrecognized archive directory')
    disk = usage(root)
    low = max(disk.total * (100-trigger)/100, 512*1024**2)
    goal = max(disk.total * (100-target)/100, 1024**3)
    if disk.free >= low:
        return 0
    candidates=[]
    for p in root.iterdir():
        s=p.lstat()
        if PATTERN.fullmatch(p.name) and stat.S_ISREG(s.st_mode):
            candidates.append((p.name,p,s.st_ino,s.st_dev))
    candidates.sort()  # Recorder timestamps, rather than copy-dependent mtime.
    deleted=0
    for offset in range(0,len(candidates),batch):
        count=0
        for _,p,inode,device in candidates[offset:offset+batch]:
            try:
                s=p.lstat()
                if stat.S_ISREG(s.st_mode) and (s.st_ino,s.st_dev)==(inode,device):
                    p.unlink();count+=1
            except FileNotFoundError:
                pass
        deleted+=count
        disk=usage(root)
        log('archive_cleanup_batch', files=count, free_bytes=disk.free, target_free_bytes=int(goal))
        if disk.free>=goal:
            return deleted
    raise RuntimeError('Archive cleanup cannot restore free-space reserve; recording paused')


def record(conf):
    fmt=conf.get('AUDIOFMT','flac')
    codec,muxer=FORMATS[fmt]
    base=Path(conf['RECS_DIR']).resolve()
    root=base/'Archive'
    if root.is_symlink():raise ValueError('Archive directory cannot be a symlink')
    root.mkdir(exist_ok=True)
    (root/'.birdnet-archive').touch()
    partial=root/'.partial'
    if partial.is_symlink():raise ValueError('Partial directory cannot be a symlink')
    partial.mkdir(exist_ok=True)
    lock=(root/'.recording.lock').open('w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    # Interrupted segments are preserved separately, never passed to automatic purge.
    for p in partial.iterdir():
        if p.is_file() and not p.is_symlink():
            log('archive_recovery_required', path=str(p))
    trigger=target=int(conf.get('ARCHIVE_MAX_USED_PERCENT','85'))
    batch=100
    cleanup(root,trigger,target,batch)
    if conf.get('RTSP_STREAM','').strip():raise ValueError('Archive mode currently supports the microphone input')
    try:
        device=subprocess.check_output(['python3','/usr/local/bin/prepare_microphone.py','--pulse','--device',conf.get('REC_CARD','default')],text=True).strip()
    except subprocess.CalledProcessError as error:
        log('archive_microphone_unavailable', returncode=error.returncode)
        return error.returncode or 1
    channels=int(conf.get('CHANNELS','1'))
    started=dt.datetime.now()
    source=subprocess.Popen(['arecord','-q','-f','S16_LE','-c',str(channels),'-r','48000','-t','raw','-D',device],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    source_tail=StderrTail(source.stderr)
    levels=Levels()
    period=Period(interval=float(conf.get('AUDIO_HEARTBEAT_SECONDS','900')),
                  quiet_dbfs=float(conf.get('AUDIO_QUIET_DBFS','-70')))
    encoder_tail=None
    seconds=int(conf.get('RECORDING_LENGTH','15'))
    chunks=queue.Queue(maxsize=256)  # At most 16 MiB; absorbs cold model/SD stalls.
    errors=[]
    def capture():
        try:
            while True:
                data=source.stdout.read(65536)
                if not data:break
                chunks.put(data,timeout=5)
        except BaseException as error:errors.append(str(error) or 'Capture buffer overflow')
        finally:
            try:chunks.put(None,timeout=5)
            except queue.Full:pass
    reader=threading.Thread(target=capture,daemon=True);reader.start()
    encoder=None
    stopping=False
    stop_reason=None
    def stop(*_):
        nonlocal stopping
        stopping=True
        if source.poll() is None:source.terminate()
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    ready=Path.home()/'BirdNET-Pi'/'.archive-ready.json'
    last_cleanup=0;completed=0;written=0;segment_bytes=0;p=None;has_signal=False
    limit=seconds*48000*channels*2
    def finish():
        nonlocal encoder,completed,segment_bytes,has_signal,levels
        encoder.stdin.close()
        code=encoder.wait(timeout=30)
        if code!=0:
            log('archive_encoder_stopped', returncode=code, signal=-code if code<0 else None,
                stderr=encoder_tail.text())
            raise RuntimeError('Archive encoding failed; partial file retained')
        dest=root/p.name
        if dest.exists():raise RuntimeError('Archive timestamp collision; original preserved')
        encoder_tail.text()
        encoder.stderr.close()
        duration=segment_bytes/(48000*channels*2)
        os.replace(p,dest);completed+=1;encoder=None;segment_bytes=0
        info=dest.stat()
        marker={'pid':os.getpid(),'path':str(dest),'format':fmt,'completed':completed,'audio_seconds':duration,'bytes':info.st_size,'has_signal':has_signal}
        rate_path=ready.with_name('.archive-rate.json')
        try:rate=json.loads(rate_path.read_text())
        except (FileNotFoundError,ValueError):rate={}
        if has_signal and duration>=seconds*.99:
            measured=max(info.st_size,info.st_blocks*512)/duration
            if (rate.get('has_signal') is True and rate.get('format')==fmt and
                    rate.get('segment_seconds')==seconds and rate.get('channels')==channels):
                measured=.8*rate['bytes_per_second']+.2*measured
            rate={'format':fmt,'segment_seconds':seconds,'channels':channels,'sample_rate':48000,
                  'bytes_per_second':measured,'has_signal':True,'updated_at':time.time()}
            rate_tmp=rate_path.with_suffix('.tmp');rate_tmp.write_text(json.dumps(rate));os.replace(rate_tmp,rate_path)
        measured_levels=levels.result()
        levels=Levels()
        transition=period.add(measured_levels,duration,dt.datetime.now().astimezone().isoformat())
        if transition:log(transition, **measured_levels)
        summary=period.summary()
        if summary:
            emit('heartbeat','heartbeat', console=True, **summary, free_bytes=disk_free(root),
                 pcm=device, card=read_audio('/proc/asound/cards'))
        has_signal=False
        temp=ready.with_suffix('.tmp');temp.write_text(json.dumps(marker));os.replace(temp,ready)
        log('archive_segment_completed',path=str(dest),bytes=dest.stat().st_size,first_segment=completed==1,**measured_levels)
    log('archive_started',format=fmt,segment_seconds=seconds,channels=channels,directory=str(root),pcm=device)
    try:
        while True:
            if time.monotonic()-last_cleanup>10 and not stopping:
                trigger=target=cleanup_limit(trigger)
                cleanup(root,trigger,target,batch);last_cleanup=time.monotonic()
            if errors:raise RuntimeError(errors[0])
            try:data=chunks.get(timeout=1)
            except queue.Empty:
                if not reader.is_alive():raise RuntimeError('Capture reader stopped')
                continue
            if data is None:
                if encoder is not None:finish()
                if not stopping:raise RuntimeError('Microphone stopped unexpectedly')
                return
            while data:
                if encoder is None:
                    stamp=started+dt.timedelta(seconds=written/(48000*channels*2))
                    p=partial/(stamp.strftime('%F-birdnet-%H:%M:%S.')+fmt)
                    if p.exists() or (root/p.name).exists():raise RuntimeError('Archive timestamp collision')
                    command=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-probesize','32','-analyzeduration','0',
                             '-f','s16le','-ar','48000','-ac',str(channels),'-i','pipe:0','-map','0:a:0','-c:a',codec,'-threads','1','-f',muxer,str(p)]
                    encoder=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
                    encoder_tail=StderrTail(encoder.stderr)
                count=min(len(data),limit-segment_bytes)
                if not has_signal:has_signal=bool(data[:count].strip(b'\x00'))
                levels.update(data[:count])
                encoder.stdin.write(data[:count]);written+=count;segment_bytes+=count;data=data[count:]
                if segment_bytes==limit:finish()
    except Exception as error:
        stop_reason=str(error)
        error.audio_logged=True
        raise
    finally:
        if source.poll() is None:source.terminate()
        try:source.wait(timeout=5)
        except subprocess.TimeoutExpired:source.kill();source.wait()
        if encoder is not None and encoder.poll() is None:
            encoder.terminate()
            try:encoder.wait(timeout=10)
            except subprocess.TimeoutExpired:encoder.kill();encoder.wait()
        log('archive_capture_stopped', returncode=source.returncode,
            signal=-source.returncode if source.returncode and source.returncode<0 else None,
            stderr=source_tail.text(), requested=stopping)
        if encoder is not None:
            log('archive_encoder_stopped', returncode=encoder.returncode,
                stderr=encoder_tail.text() if encoder_tail else '')
        summary=period.summary(force=True)
        if summary:emit('heartbeat','heartbeat', console=True, **summary, final=True,
                        free_bytes=disk_free(root),pcm=device)
        log('archive_stopped',reason=stop_reason or ('signal requested' if stopping else 'capture ended'),
            returncode=source.returncode, signal=-source.returncode if source.returncode and source.returncode<0 else None,
            stderr=source_tail.text())
        source.stdout.close();source.stderr.close();reader.join(timeout=2)
        if ready.exists() and json.loads(ready.read_text()).get('pid')==os.getpid():ready.unlink()


if __name__=='__main__':
    from utils.helpers import get_settings
    import sys
    try:
        sys.exit(record(get_settings()) or 0)
    except Exception as error:
        if not getattr(error,'audio_logged',False):log('archive_stopped',reason=str(error))
        sys.exit(1)
