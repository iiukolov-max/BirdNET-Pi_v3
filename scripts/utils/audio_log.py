"""Best-effort persistent audio diagnostics, usable with system Python 3.11/3.13.

Callers retain their existing stdout/stderr contract. No exception from this
module may prevent audio capture. State and locks live on tmpfs, not the SD.
"""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

LOG = Path('/var/log/birdnet/audio.jsonl')
STATE = Path('/run/birdnet-audio')
INTERVAL = 600
MAX_BYTES = 256 * 1024


def read(path):
    try:
        return Path(path).read_text().strip()
    except (OSError, UnicodeError):
        return ''


def safe(value):
    if isinstance(value, dict):
        return {k: safe(v) for k, v in value.items() if 'serial' not in k.lower()}
    if isinstance(value, list):
        return [safe(v) for v in value]
    if isinstance(value, str):
        value = '\n'.join(line for line in value.splitlines() if not re.search(r'serial(?:number| number|=|:)', line, re.I))
        return re.sub(r'(alsa_input|alsa_output)\.usb-[^\s\"\']+', r'\1.usb-[redacted]', value)
    return value


def envelope(event, source, fields):
    return dict(safe(fields), schema_version=1, event=event,
                time=dt.datetime.now().astimezone().isoformat(),
                boot_id=read('/proc/sys/kernel/random/boot_id'),
                uptime_seconds=float(read('/proc/uptime').split()[0]),
                source=source, pid=os.getpid())


def append(record, path):
    # Existing file only: provisioning/rotation owns permissions. No symlinks.
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
    try:
        if os.fstat(fd).st_size >= MAX_BYTES:
            return False  # Bound disk use even if the rotation timer is broken.
        data = (json.dumps(safe(record), ensure_ascii=False, allow_nan=False) + '\n').encode()
        if len(data) > 32768:
            return False
        return os.write(fd, data) == len(data)
    finally:
        os.close(fd)


def emit(event, source, *, repeat=False, snapshot=None, signature='',
         log_path=None, state_dir=None, interval=INTERVAL, lane='', console=False, **fields):
    """Append once; coalesce retry failures across short-lived processes.

    snapshot is lazy, evaluated only when an event is actually persisted.
    Each source has a lifecycle slot; unrelated diagnostics cannot clear it.
    Return False on any failure; do not write anything to caller stdout.
    """
    try:
        path = Path(log_path) if log_path is not None else LOG
        state_root = Path(state_dir) if state_dir is not None else STATE
        record = envelope(event, source, fields)
        if console:
            print(json.dumps(record, ensure_ascii=False), file=sys.stderr, flush=True)
        if not repeat:
            if snapshot:
                record['snapshot'] = snapshot()
            return append(record, path)
        reason = re.sub(r'\d+', '#', str(fields.get('reason', fields.get('error', ''))))
        key = hashlib.sha256((event + reason + signature).encode()).hexdigest()
        slot = re.sub(r'[^a-zA-Z0-9_-]', '_', source)
        if lane:
            slot += '-' + hashlib.sha256(lane.encode()).hexdigest()[:16]
        with (state_root / (slot + '.lock')).open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            state_path = state_root / (slot + '.json')
            try:
                previous = json.loads(state_path.read_text())
            except (OSError, ValueError):
                previous = {}
            now = time.monotonic()
            if previous.get('boot_id') != record['boot_id']:
                previous = {}
            same = previous.get('key') == key
            if same:
                previous['count'] += 1
                previous['last_time'] = record['time']
            if previous.get('count') and (not same or now - previous['reported'] >= interval):
                summary = envelope('repeated', source, {
                    'of': previous['event'], 'count': previous['count'],
                    'first_time': previous['first_time'], 'last_time': previous['last_time']})
                if append(summary, path):
                    previous['count'] = 0
                    previous['reported'] = now
            if not same:
                if snapshot:
                    record['snapshot'] = snapshot()
                if not append(record, path):
                    return False
                previous = dict(key=key, event=event, count=0, first_time=record['time'],
                                last_time=record['time'], reported=now, boot_id=record['boot_id'])
            temporary = state_path.with_suffix('.tmp')
            temporary.write_text(json.dumps(previous))
            os.replace(temporary, state_path)
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('event')
    parser.add_argument('--source', default='birdnet_recording')
    parser.add_argument('--fields', default='{}', help='JSON object; never pass credentials or stream URLs')
    args = parser.parse_args()
    try:
        fields = json.loads(args.fields)
        record = envelope(args.event, args.source, fields)
        print(json.dumps(record), file=sys.stderr, flush=True)
        emit(args.event, args.source, repeat=True,
             lane='' if args.event in {'arecord_started','ffmpeg_started','recording_microphone_unavailable'} else args.event, **fields)
    except Exception:
        pass


if __name__ == '__main__':
    main()
