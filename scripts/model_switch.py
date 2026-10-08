#!/usr/bin/env python3
"""Apply Settings as a transaction and restore the prior model on startup failure."""
import json
import os
import pwd
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

BASE = Path(__file__).resolve().parent.parent
CONFIG = BASE / 'birdnet.conf'
STATE = BASE / '.model-profiles.json'
READY = BASE / '.model-ready.json'
V3 = 'BirdNET+_V3.0-preview3.1_Global_11K_FP16_pruned'
MODELS = ('BirdNET_GLOBAL_6K_V2.4_Model_FP16', 'BirdNET_6K_GLOBAL_MODEL', V3)
KEYS = ('CONFIDENCE', 'SENSITIVITY', 'SF_THRESH', 'DATA_MODEL_VERSION', 'PRIVACY_THRESHOLD')


def values(text):
    return dict(re.findall(r'^([A-Za-z_][A-Za-z_0-9]*)=(.*)$', text, re.M))


def replace(text, key, value):
    line = key + '=' + str(value)
    if re.search(r'^' + re.escape(key) + r'=', text, re.M):
        return re.sub(r'^' + re.escape(key) + r'=.*$', lambda _: line, text, flags=re.M)
    return text.rstrip() + '\n' + line + '\n'


def atomic(path, content):
    target = path.resolve()
    stat = target.stat() if target.exists() else CONFIG.stat()
    fd, temp = tempfile.mkstemp(prefix='.' + target.name, dir=target.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, stat.st_mode & 0o777)
        os.chown(temp, stat.st_uid, stat.st_gid)
        os.replace(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def service(*args):
    subprocess.run(['systemctl', *args, 'birdnet_analysis.service'], check=True,
                   stdout=subprocess.DEVNULL, timeout=120)


def await_ready(model, timeout=180):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        info = subprocess.check_output(['systemctl', 'show', 'birdnet_analysis.service',
                                        '-p', 'MainPID', '-p', 'NRestarts'], text=True)
        unit = values(info)
        try:
            ready = json.loads(READY.read_text())
        except (FileNotFoundError, ValueError):
            ready = {}
        if int(unit.get('NRestarts', '0')) >= 1:
            raise RuntimeError('Analyzer restarted unexpectedly during startup')
        if ready.get('model') == model and str(ready.get('pid')) == unit.get('MainPID'):
            return
        time.sleep(1)
    raise RuntimeError('Analyzer did not become ready within 180 seconds')


def labels():
    owner = pwd.getpwuid(BASE.stat().st_uid).pw_name
    subprocess.run(['sudo', '-u', owner, str(BASE / 'birdnet/bin/python3'), '-c',
                    'from utils.helpers import set_label_file; set_label_file()'],
                   cwd=BASE / 'scripts', check=True, timeout=30,
                   stdout=subprocess.DEVNULL)


def apply(candidate):
    previous = CONFIG.read_text()
    before, after = values(previous), values(candidate)
    target = after.get('MODEL')
    if target not in MODELS:
        raise ValueError('Unknown model')
    artifact = BASE / 'model' / (target + '.tflite')
    if not artifact.is_file() or artifact.stat().st_size < 1000000:
        raise ValueError('Model file is missing or incomplete; current settings retained')
    try:
        profiles = json.loads(STATE.read_text())
    except FileNotFoundError:
        profiles = {}
    profiles[before['MODEL']] = {k: before[k] for k in KEYS if k in before}
    if target != before['MODEL']:
        defaults = {k: before[k] for k in KEYS if k in before}
        if target == V3:
            defaults.update(SENSITIVITY='1.0', PRIVACY_THRESHOLD='0', CONFIDENCE='0.6')
        elif before['MODEL'] == V3:
            # A legacy model selected for the first time must inherit a legacy
            # profile, not V3's forced sensitivity/privacy values.
            legacy_defaults = dict(defaults, CONFIDENCE='0.7', SENSITIVITY='1.25',
                                   PRIVACY_THRESHOLD='0', SF_THRESH='0.03', DATA_MODEL_VERSION='1')
            defaults = next((profiles[name] for name in MODELS[:2] if name in profiles), legacy_defaults)
        for key, val in profiles.get(target, defaults).items():
            candidate = replace(candidate, key, val)
    # The preview exports probabilities and has no Human class.
    if target == V3:
        candidate = replace(candidate, 'SENSITIVITY', '1.0')
        candidate = replace(candidate, 'PRIVACY_THRESHOLD', '0')
    service('stop')
    try:
        atomic(CONFIG, candidate)
        labels()
        service('start')
        await_ready(target)
        profiles[target] = {k: v for k, v in values(candidate).items() if k in KEYS}
        atomic(STATE, json.dumps(profiles, indent=2) + '\n')
    except BaseException as exc:
        service('stop')
        atomic(CONFIG, previous)
        labels()
        service('start')
        try:
            await_ready(before['MODEL'])
        except Exception as rollback:
            raise RuntimeError('Settings restored but analyzer recovery failed: ' + str(rollback)) from exc
        raise RuntimeError('Previous model and settings restored: ' + str(exc)) from exc
    return target


def main():
    import fcntl
    if os.geteuid() != 0:
        raise RuntimeError('Run using sudo')
    candidate = sys.stdin.read(131073)
    if not candidate or len(candidate) > 131072:
        raise ValueError('Invalid settings size')
    with open('/run/lock/birdnet-model-switch.lock', 'w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another model switch is still running')
        print('Model ready: ' + apply(candidate))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
