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
from birdnet_service_policy import allowed, validate, CATALOG
import analysis_backend
from settings_plan import HOT_KEYS

BASE = Path(__file__).resolve().parent.parent
CONFIG = BASE / 'birdnet.conf'
STATE = BASE / '.model-profiles.json'
READY = BASE / '.model-ready.json'
PAUSE_MARKER = Path('/run/birdnet-archive-recording-pause.json')
V3 = 'BirdNET+_V3.0-preview3.1_Global_11K_FP16_pruned'
MODELS = ('BirdNET_GLOBAL_6K_V2.4_Model_FP16', 'BirdNET_6K_GLOBAL_MODEL', V3)
KEYS = ('CONFIDENCE', 'SENSITIVITY', 'SF_THRESH', 'DATA_MODEL_VERSION', 'PRIVACY_THRESHOLD', 'GEO_MODEL')


def values(text):
    result = dict(re.findall(r'^([A-Za-z_][A-Za-z_0-9]*)=(.*)$', text, re.M))
    for key, value in result.items():
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = re.sub(r'\\([\\"$`])', r'\1', value[1:-1])
        result[key] = value
    return result


def changed_settings(before, after):
    defaults = {'OPERATION_MODE':'normal','ARCHIVE_MAX_USED_PERCENT':'85',
                'ANALYSIS_BACKEND':'local','REMOTE_ANALYSIS_IP':'','REMOTE_ANALYSIS_BATCH':'10',
                'MICROPHONE_GAIN_100':'0'}
    defaults.update({'SERVICE_ALLOW_'+row['key']:str(row['default']) for row in CATALOG})
    return {k for k in before.keys() | after.keys()
            if before.get(k, defaults.get(k)) != after.get(k, defaults.get(k))}


def replace(text, key, value):
    line = key + '=' + str(value)
    if re.search(r'^' + re.escape(key) + r'=', text, re.M):
        return re.sub(r'^' + re.escape(key) + r'=.*$', lambda _: line, text, flags=re.M)
    return text.rstrip() + '\n' + line + '\n'


def merge_changed(previous, candidate):
    """Keep original spelling/quotes for every semantically unchanged setting."""
    raw=dict(re.findall(r'^([A-Za-z_][A-Za-z_0-9]*)=(.*)$',candidate,re.M))
    for key in changed_settings(values(previous),values(candidate)):
        if key in raw:previous=replace(previous,key,raw[key])
        else:previous=re.sub(r'^'+re.escape(key)+r'=.*\n?','',previous,flags=re.M)
    return previous


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
    if not changed_settings(before,after):return after.get('MODEL')
    validate(after)
    if after.get('MICROPHONE_GAIN_100', '0') not in ('0', '1'):
        raise ValueError('Invalid microphone gain setting')
    backend_changed=any(before.get(k,{'ANALYSIS_BACKEND':'local','REMOTE_ANALYSIS_IP':''}[k])!=after.get(k,{'ANALYSIS_BACKEND':'local','REMOTE_ANALYSIS_IP':''}[k]) for k in ('ANALYSIS_BACKEND','REMOTE_ANALYSIS_IP'))
    analysis_backend.validate(after,check=backend_changed and after.get('ANALYSIS_BACKEND','local')=='remote')
    target = after.get('MODEL')
    mode = after.get('OPERATION_MODE', 'normal')
    if mode not in ('normal', 'archive'):
        raise ValueError('Unknown operation mode')
    if mode=='archive' and after.get('AUDIOFMT','flac') not in ('flac','mp3','ogg','opus','wav'):
        raise ValueError('Unsupported archive format')
    if not 50<=int(after.get('ARCHIVE_MAX_USED_PERCENT','85'))<=95:
        raise ValueError('Invalid archive cleanup settings')
    if not 3<=int(after.get('RECORDING_LENGTH','15'))<=60:
        raise ValueError('Invalid archive segment length')
    if mode=='archive' and after.get('RTSP_STREAM','').strip().strip('"'):
        raise ValueError('Archive mode currently supports microphone input only')
    recording_keys=('OPERATION_MODE','CHANNELS','REC_CARD','MICROPHONE_GAIN_100','RECORDING_LENGTH','RTSP_STREAM','LogLevel_BirdnetRecordingService')
    if mode=='archive':recording_keys=tuple(k for k in recording_keys if k!='LogLevel_BirdnetRecordingService')
    defaults={'OPERATION_MODE':'normal','ARCHIVE_MAX_USED_PERCENT':'85','RECORDING_LENGTH':'15','MICROPHONE_GAIN_100':'0'}
    restart_recording=any(before.get(k,defaults.get(k))!=after.get(k,defaults.get(k)) for k in recording_keys) or (mode=='archive' and before.get('AUDIOFMT')!=after.get('AUDIOFMT'))
    if mode == before.get('OPERATION_MODE','normal') == 'archive' and changed_settings(before,after) <= {'LogLevel_BirdnetRecordingService'}:
        restart_recording=False  # Python archive capture has no shell logging level.
    if target not in MODELS:
        raise ValueError('Unknown model')
    artifact = BASE / 'model' / (target + '.tflite')
    if target != before.get('MODEL') and (not artifact.is_file() or artifact.stat().st_size < 1000000):
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
    geo_mode = values(candidate).get('GEO_MODEL', 'legacy')
    if geo_mode not in ('off', 'legacy', 'v3.0.4'):
        raise ValueError('Unknown geographic filter')
    if target == V3 and geo_mode == 'v3.0.4':
        for name in ('BirdNET+_Geomodel_V3.0.4_Global_14K_FP32.tflite',
                     'BirdNET+_Geomodel_V3.0.4_Global_14K_Labels.txt'):
            if not (BASE / 'model' / name).is_file():
                raise ValueError('Geomodel V3 files are missing; current settings retained')
    if target == V3:
        candidate = replace(candidate, 'SENSITIVITY', '1.0')
        candidate = replace(candidate, 'PRIVACY_THRESHOLD', '0')
    effective=values(candidate)
    changed=changed_settings(before,effective)
    if not changed:return target
    mode_changed=before.get('OPERATION_MODE','normal')!=mode
    policy_keys={k for k in changed if k.startswith('SERVICE_ALLOW_') and any(
        k=='SERVICE_ALLOW_'+row['key'] and any(allowed(unit,before)!=allowed(unit,effective) for unit in row['units']) for row in CATALOG)}
    policy_changed=bool(policy_keys)
    analysis_keys={'MODEL','CONFIDENCE','SENSITIVITY','SF_THRESH','DATA_MODEL_VERSION',
                   'PRIVACY_THRESHOLD','GEO_MODEL','LATITUDE','LONGITUDE','DATABASE_LANG',
                   'OVERLAP','RECORDING_LENGTH','EXTRACTION_LENGTH','AUDIOFMT','RAW_SPECTROGRAM'}
    analysis_keys.update({'ANALYSIS_BACKEND'})
    if effective.get('ANALYSIS_BACKEND','local')=='remote':analysis_keys.add('REMOTE_ANALYSIS_IP')
    analysis_change=mode_changed or 'SERVICE_ALLOW_ANALYSIS' in changed or bool(changed&(analysis_keys-HOT_KEYS))
    analysis_active=analysis_change and active('birdnet_analysis')
    try:
        paused_recording=json.loads(PAUSE_MARKER.read_text()).get('resume',False)
    except (FileNotFoundError,ValueError):
        paused_recording=False
    recording_active=(restart_recording or mode_changed) and (active('birdnet_recording') or paused_recording)
    restart_recording=restart_recording and recording_active
    start_analysis=allowed('birdnet_analysis.service', effective) and (analysis_active or (mode_changed and recording_active) or policy_changed)
    touch_analysis=analysis_change and (analysis_active or start_analysis)
    manual_active=(analysis_change or restart_recording) and active('birdnet-archive-analysis')
    if manual_active:
        if restart_recording and paused_recording:
            from archive_recording_pause import cancel
            cancel()
        manual_service('stop')
    if touch_analysis:service('stop')
    try:
        if restart_recording: recording_service('stop')
        atomic(CONFIG, candidate)
        if mode=='normal' and changed&{'MODEL','DATABASE_LANG'}:labels()
        if mode_changed:enforce_services()
        elif policy_changed:enforce_services(policy_keys)
        if restart_recording and allowed('birdnet_recording.service', effective): recording_service('start')
        if mode=='archive' and restart_recording and allowed('birdnet_recording.service', effective):
            await_archive(int(after.get('RECORDING_LENGTH','15'))+120)
        elif start_analysis and touch_analysis:
            service('start')
            # Readiness is published on the first input file. With capture
            # explicitly prohibited the analyzer may legitimately wait idle.
            if allowed('birdnet_recording.service', effective):await_ready(target)
        if changed & (set(KEYS)|{'MODEL'}):
            profiles[target] = {k: v for k, v in values(candidate).items() if k in KEYS}
            atomic(STATE, json.dumps(profiles, indent=2) + '\n')
        if manual_active and mode=='archive' and allowed('birdnet-archive-analysis.service',effective):manual_service('start')
    except BaseException as exc:
        if touch_analysis:service('stop')
        if restart_recording: recording_service('stop')
        atomic(CONFIG, previous)
        if mode_changed:enforce_services()
        elif policy_changed:enforce_services(policy_keys)
        if restart_recording: recording_service('start')
        try:
            if before.get('OPERATION_MODE','normal')=='archive' and restart_recording:
                await_archive(int(before.get('RECORDING_LENGTH','15'))+120)
            elif analysis_active and touch_analysis:
                labels()
                service('start')
                await_ready(before['MODEL'])
            if manual_active:manual_service('start')
        except Exception as rollback:
            raise RuntimeError('Settings restored but analyzer recovery failed: ' + str(rollback)) from exc
        raise RuntimeError('Previous model and settings restored: ' + str(exc)) from exc
    return target


def enforce_services(changed=None):
    if changed is not None:
        policy=Path(__file__).with_name('birdnet_service_policy.py')
        subprocess.run(['/usr/bin/python3',str(policy),'apply',*sorted(k for k in changed if k.startswith('SERVICE_ALLOW_'))],check=True,timeout=120)
        return
    guard=Path('/usr/local/libexec/birdnet_minimal_services.py')
    if guard.is_file():
        subprocess.run(['/usr/bin/python3',str(guard)],check=True,timeout=180)


def active(unit):
    return subprocess.run(['systemctl','is-active','--quiet',unit],stdout=subprocess.DEVNULL).returncode==0


def manual_service(action):
    subprocess.run(['systemctl',action,'birdnet-archive-analysis.service'],check=True,timeout=30)


def recording_service(action):
    subprocess.run(['systemctl',action,'birdnet_recording.service'],check=True,timeout=180)


def await_archive(timeout=180):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        pid=subprocess.check_output(['systemctl','show','birdnet_recording','-p','MainPID','--value'],text=True).strip()
        try:
            ready=json.loads((BASE/'.archive-ready.json').read_text())
            if str(ready['pid'])==pid and Path(ready['path']).is_file():return
        except (FileNotFoundError,ValueError,KeyError):pass
        time.sleep(1)
    raise RuntimeError('Archive recording did not complete a segment')


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
        model=apply(candidate)
        print('Recording-only mode ready' if values(candidate).get('OPERATION_MODE')=='archive' else 'Model ready: '+model)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
