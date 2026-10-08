"""Root systemd hooks: pause recording for a manual run, restore afterwards."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from birdnet_service_policy import allowed

MARKER = Path('/run/birdnet-archive-recording-pause.json')
CONFIG = Path(__file__).resolve().parent.parent / 'birdnet.conf'
UNIT = 'birdnet_recording.service'


def run(*args, **kwargs):
    return subprocess.run(['systemctl', *args], timeout=180, **kwargs)


def mode():
    match = re.search(r'^OPERATION_MODE=(.*)$', CONFIG.read_text(), re.M)
    return match.group(1).strip().strip('"') if match else 'normal'


def state():
    try:
        return json.loads(MARKER.read_text())
    except FileNotFoundError:
        return {}


def write(value):
    temp = MARKER.with_suffix('.tmp')
    temp.write_text(json.dumps(value))
    os.chmod(temp, 0o644)
    temp.replace(MARKER)


def pause():
    if mode() != 'archive':
        raise RuntimeError('Archive mode required')
    if MARKER.exists():
        raise RuntimeError('Previous recording pause has not been restored')
    current = run('show', UNIT, '-p', 'ActiveState', '--value',
                  check=True, text=True, capture_output=True).stdout.strip()
    active = current in ('active', 'activating', 'reloading')
    write({'resume': active, 'invocation': os.environ.get('INVOCATION_ID', ''), 'started': time.time()})
    if active:
        run('stop', UNIT, check=True)
        if run('is-active', '--quiet', UNIT).returncode == 0:
            raise RuntimeError('Microphone recording did not stop')


def restore():
    saved = state()
    if not saved:
        return
    if saved.get('invocation') != os.environ.get('INVOCATION_ID', ''):
        raise RuntimeError('Recording pause belongs to a different run')
    system = run('is-system-running', check=False, text=True, capture_output=True).stdout.strip()
    if saved.get('resume') and mode() == 'archive' and system != 'stopping' and allowed(UNIT):
        # Do not wait for a job that can be ordered after this stop hook.
        run('start', '--no-block', UNIT, check=True)
    MARKER.unlink()
    if saved.get('resume') and mode() == 'archive' and system != 'stopping':
        from archive_charts import read, request, ROOT
        result = read(ROOT/'.archive-analysis.json')
        if result.get('started',0) >= saved.get('started',float('inf')):
            try:request(result)
            except Exception as error:print(json.dumps({'event':'charts_schedule_failed','error':str(error)}),flush=True)


def cancel():
    saved = state()
    if saved:
        saved['resume'] = False
        write(saved)


if __name__ == '__main__':
    if os.geteuid() != 0:
        raise SystemExit('Run with sudo')
    if sys.argv[1:] not in (['pause'], ['restore'], ['cancel']):
        raise SystemExit('Expected pause, restore or cancel')
    {'pause': pause, 'restore': restore, 'cancel': cancel}[sys.argv[1]]()
