#!/usr/bin/env python3
"""Optional RTC restore and NTP-to-RTC write; absent hardware never delays boot."""
import json
from pathlib import Path
import shutil
import subprocess
import sys


def run(*args):
    return subprocess.run(args, capture_output=True, text=True, timeout=15)


def ntp_synchronized(action):
    if action == 'restore':
        # Early boot precedes D-Bus. Never invoke timedatectl before sysinit.target.
        return Path('/run/systemd/timesync/synchronized').exists()
    return run('timedatectl', 'show', '-p', 'NTPSynchronized', '--value').stdout.strip() == 'yes'


def synchronize(action):
    devices = sorted(Path('/sys/class/rtc').glob('rtc*'))
    if action == '--fake-condition':
        return 1 if devices else 0
    if not devices:
        print(json.dumps({'event': 'rtc_sync_skipped', 'reason': 'RTC not present'}))
        return 0
    hwclock = shutil.which('hwclock')
    if not hwclock:
        raise RuntimeError('hwclock is not installed')
    device = next((d for d in devices if (d / 'hctosys').read_text().strip() == '1'), devices[0])
    synchronized = ntp_synchronized(action)
    if action == 'save':
        if not synchronized:
            print(json.dumps({'event': 'rtc_sync_skipped', 'reason': 'Awaiting network time synchronization'}))
            return 0
        command = [hwclock, '--systohc', '--utc', '--noadjfile', '--rtc', '/dev/' + device.name]
    elif action == 'restore':
        if synchronized or (device / 'hctosys').read_text().strip() == '1':
            print(json.dumps({'event': 'rtc_restore_skipped', 'reason': 'Clock already set by NTP or kernel'}))
            return 0
        # Reject an uninitialized RTC; NTP can initialize it later.
        try:
            epoch = int((device / 'since_epoch').read_text())
        except (OSError, ValueError):
            epoch = 0
        if not 1577836800 <= epoch < 4102444800:
            print(json.dumps({'event': 'rtc_sync_skipped', 'reason': 'RTC time is uninitialized or invalid'}))
            return 0
        command = [hwclock, '--hctosys', '--utc', '--noadjfile', '--rtc', '/dev/' + device.name]
    else:
        raise ValueError('Expected restore, save or --fake-condition')
    result = run(*command)
    print(json.dumps({'event': 'rtc_' + action, 'device': device.name, 'utc': True,
                      'success': result.returncode == 0, 'error': result.stderr.strip()}))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(synchronize(sys.argv[1]))
