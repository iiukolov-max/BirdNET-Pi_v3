#!/usr/bin/env python3
"""Persistent launch permissions, also checked by systemd for every start."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

CONFIG = Path('/etc/birdnet/birdnet.conf')
CATALOG = json.loads(Path(__file__).with_name('service_policy.json').read_text())


def settings():
    return dict(re.findall(r'^([A-Za-z_][A-Za-z_0-9]*)=(.*)$', CONFIG.read_text(), re.M))


def validate(config):
    for row in CATALOG:
        key = 'SERVICE_ALLOW_' + row['key']
        if config.get(key, str(row['default'])) not in ('0', '1'):
            raise ValueError('Invalid service permission: ' + key)


def allowed(unit, config=None):
    config = settings() if config is None else config
    row = next((row for row in CATALOG if unit in row['units']), None)
    if row is None:
        raise ValueError('Unknown managed service: ' + unit)
    return ((row.get('fixed') or config.get('SERVICE_ALLOW_' + row['key'], str(row['default'])) == '1')
            and config.get('OPERATION_MODE', 'normal') in row['modes'])


def run(*args):
    return subprocess.run(['systemctl', *args], capture_output=True, text=True,
                          check=True, timeout=120)


def reconcile():
    """Mode guard restores unit files first; never autostart manual analysis."""
    config = settings()
    validate(config)
    stops, disables, enables, starts = [], [], [], []
    manual_running = config.get('OPERATION_MODE','normal') == 'archive' and subprocess.run(
        ['systemctl','show','birdnet-archive-analysis.service','-p','ActiveState','--value'],
        capture_output=True,text=True,timeout=30).stdout.strip() in ('active','activating','reloading')
    for row in CATALOG:
        for unit in row['units']:
            info = subprocess.run(['systemctl', 'show', unit, '-p', 'LoadState', '--value'],
                                  capture_output=True, text=True, timeout=30).stdout.strip()
            if info in ('', 'not-found'):
                continue
            enabled = subprocess.run(['systemctl', 'is-enabled', unit],
                                     capture_output=True, text=True, timeout=30).stdout.strip()
            permit = allowed(unit, config)
            if not permit:
                stops.append(unit)
                # Economy may already have masked optional services.
                if info != 'masked' and enabled not in ('disabled', 'static', 'masked', 'masked-runtime'):
                    disables.append(unit)
            elif row.get('manual'):
                if enabled not in ('disabled', 'static', 'masked', 'masked-runtime'):
                    disables.append(unit)
            else:
                if enabled not in ('enabled', 'static', 'alias', 'generated'):
                    enables.append(unit)
                if unit == 'birdnet_recording.service' and manual_running:
                    # Saving optional permissions must not break the microphone
                    # pause. Do not stop it either: the completion hook might
                    # already be restoring recording while we reconcile.
                    pass
                else:
                    starts.append(unit)
    if stops:run('stop', *stops)
    if disables:run('disable', '--no-reload', *disables)
    if enables:run('enable', '--no-reload', *enables)
    if disables or enables:
        run('daemon-reload')
    if starts:run('start', '--no-block', *starts)


def install():
    for row in CATALOG:
        for unit in row['units']:
            directory = Path('/etc/systemd/system') / (unit + '.d')
            directory.mkdir(parents=True, exist_ok=True)
            (directory / '20-launch-permission.conf').write_text(
                '[Service]\nExecCondition=/usr/bin/python3 '
                '/usr/local/libexec/birdnet_service_policy.py check ' + unit + '\n')
    run('daemon-reload')


def main():
    if len(sys.argv) == 3 and sys.argv[1] == 'check':
        if allowed(sys.argv[2]):
            return 0
        print('Launch blocked by Settings service permissions or operation mode', flush=True)
        return 1  # ExecCondition: skip startup without marking the unit failed.
    if os.geteuid() != 0:
        raise RuntimeError('Run as root')
    if sys.argv[1:] == ['install']:
        install()
    elif sys.argv[1:] == ['apply']:
        reconcile()
    else:
        raise ValueError('Expected check UNIT, install or apply')
    return 0


if __name__ == '__main__':
    sys.exit(main())
