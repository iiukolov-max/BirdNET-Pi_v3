"""Root-only boot guard for the explicitly requested recording/analysis profile."""
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from birdnet_service_policy import CATALOG, allowed, reconcile

KEEP = {'birdnet_recording.service', 'birdnet_analysis.service', 'caddy.service',
        'birdnet-archive-analysis.service',
        'birdnet-archive-charts.service',
        'birdnet-minimal-services.service', 'birdnet-cpu-policy.service', 'birdnet-startup-log.service',
        'birdnet-startup-log.timer'}
KNOWN = {'birdnet_log.service', 'birdnet_stats.service', 'chart_viewer.service',
         'spectrogram_viewer.service', 'web_terminal.service', 'livestream.service',
         'custom_recording.service', 'icecast2.service', 'caddy.service', 'caddy-api.service'}


def run(*args, check=True):
    result = subprocess.run(args, text=True, capture_output=True, timeout=90)
    if check and result.returncode:
        raise RuntimeError(' '.join(args) + ': ' + result.stderr.strip())
    return result


def restore_services():
    run('systemctl','stop','birdnet-archive-analysis.service',check=False)
    backup=Path('/var/lib/birdnet/minimal-services-backup')
    manifest=backup/'units.json'
    if not manifest.exists():return
    saved=json.loads(manifest.read_text())
    restored=[]
    starts=[]
    for unit,state in saved.items():
        if unit in KEEP or re.fullmatch(r'php[0-9.]+-fpm\.service',unit):continue
        if state['enabled']=='masked':continue
        if unit not in KNOWN and not unit.startswith(('birdnet_','birdnet-')):continue
        local=Path('/etc/systemd/system')/unit
        if not (local.is_symlink() and os.readlink(local)=='/dev/null'):continue
        run('systemctl','unmask','--no-reload',unit)
        if state.get('local_regular'):
            local.write_bytes((backup/unit).read_bytes())
        elif state.get('local_symlink') and not local.exists():
            local.symlink_to(state['local_symlink'])
        if state['enabled']=='enabled':run('systemctl','enable','--no-reload',unit)
        elif state['enabled']=='disabled':run('systemctl','disable','--no-reload',unit)
        if state['active']=='active' and (unit not in {u for row in CATALOG for u in row['units']} or allowed(unit)):
            starts.append(unit)
        restored.append(unit)
    if restored:run('systemctl','daemon-reload')
    if starts:run('systemctl','start','--no-block',*starts)
    print(json.dumps({'event':'normal_unit_files_restored','restored_unit_files':restored,'start_requested':starts}),flush=True)


def main():
    assert os.geteuid() == 0, 'Run as root'
    if '--boot' in sys.argv[1:]:
        from archive_charts import recover
        recover()
    config=Path('/etc/birdnet/birdnet.conf').read_text()
    mode=dict(re.findall(r'^([A-Z_]+)=(.*)$',config,re.M)).get('OPERATION_MODE','normal')
    if mode not in ('normal','archive'):raise ValueError('Invalid OPERATION_MODE')
    if mode=='normal':
        restore_services()
        reconcile()
        return
    if '--boot' in sys.argv[1:]:
        # Boot always returns to capture-only, never resumes a manual run.
        run('systemctl','disable','birdnet-archive-analysis.service')
        run('systemctl','stop','--no-block','birdnet-archive-analysis.service','birdnet_analysis.service')
        if allowed('birdnet_recording.service'):
            run('systemctl','enable','birdnet_recording.service')
            run('systemctl','start','--no-block','birdnet_recording.service')
    inventory = run('systemctl', 'list-unit-files', '--no-legend', '--no-pager').stdout
    # Detached maintenance trials are transient, have no boot autostart, and
    # must be allowed to finish restoring the main analyzer.
    installed = {line.split()[0] for line in inventory.splitlines()
                 if line.strip() and len(line.split()) > 1 and line.split()[1] != 'transient'}
    services = sorted(unit for unit in installed if unit.endswith('.service') and '@.' not in unit)
    metadata = run('systemctl', 'show', *services, '-p', 'Id', '-p', 'ExecStart').stdout
    commands = {}
    for block in metadata.split('\n\n'):
        fields = dict(line.split('=', 1) for line in block.splitlines() if '=' in line)
        if 'Id' in fields:
            commands[fields['Id']] = fields.get('ExecStart', '')
    targets = set()
    for unit in installed:
        if unit in KEEP or re.fullmatch(r'php[0-9.]+-fpm\.service', unit) or not unit.endswith(('.service', '.timer', '.socket', '.path')):
            continue
        if unit in KNOWN or unit.startswith(('birdnet_', 'birdnet-')):
            targets.add(unit)
            continue
        if unit.endswith('.service'):
            command = commands.get(unit, '')
            application_root = str(Path('/etc/birdnet/birdnet.conf').resolve().parent) + '/'
            if application_root in command or re.search(r'/usr/local/bin/(birdnet_|chart_viewer|spectrogram_viewer|web_terminal|livestream)', command):
                targets.add(unit)
    backup = Path('/var/lib/birdnet/minimal-services-backup')
    backup.mkdir(parents=True, exist_ok=True, mode=0o700)
    manifest_file = backup / 'units.json'
    saved = json.loads(manifest_file.read_text()) if manifest_file.exists() else {}
    for unit in sorted(targets):
        if unit not in saved:
            local = Path('/etc/systemd/system') / unit
            saved[unit] = {'enabled': run('systemctl', 'is-enabled', unit, check=False).stdout.strip(),
                           'active': run('systemctl', 'is-active', unit, check=False).stdout.strip(),
                           'local_symlink': os.readlink(local) if local.is_symlink() else None,
                           'local_regular': local.is_file() and not local.is_symlink()}
            if saved[unit]['local_regular']:
                (backup / unit).write_bytes(local.read_bytes())
            manifest_file.write_text(json.dumps(saved, indent=2) + '\n')
    if targets:
        run('systemctl', 'disable', '--now', *sorted(targets))
        for unit in sorted(targets):
            local = Path('/etc/systemd/system') / unit
            if local.exists() and not local.is_symlink():
                # Only an inventoried, backed-up unit in this exact directory.
                assert (backup / unit).is_file()
                local.unlink()
        run('systemctl', 'mask', '--force', *sorted(targets))
        # SysV-generated units can retain active state through disable/reload.
        run('systemctl', 'stop', *sorted(targets))
    run('systemctl', 'daemon-reload')
    reconcile()
    states = {}
    for unit in sorted(targets):
        state = {'active': run('systemctl', 'is-active', unit, check=False).stdout.strip(),
                 'enabled': run('systemctl', 'is-enabled', unit, check=False).stdout.strip()}
        assert state['active'] not in ('active', 'activating', 'reloading'), (unit, state)
        assert state['enabled'] == 'masked', (unit, state)
        states[unit] = state
    report = {'event': 'minimal_services_enforced', 'time': dt.datetime.now().astimezone().isoformat(),
              'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              'disabled': states, 'keep': sorted(KEEP), 'passed': True}
    log = Path('/var/log/birdnet/minimal-services.jsonl')
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('a') as output:
        output.write(json.dumps(report) + '\n')
    os.chmod(log, 0o640)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
