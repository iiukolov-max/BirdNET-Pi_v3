#!/usr/bin/env python3
"""Configure an optional DS3231 on Raspberry Pi; hardware is checked at boot."""
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def configure(text):
    overlays = re.findall(r'^\s*dtoverlay\s*=\s*i2c-rtc,([^\n#]+)', text, re.M)
    if overlays and any(not value.strip().startswith('ds3231') for value in overlays):
        return text, 'Existing RTC configuration retained'
    # Place settings in [all], so a preceding board-specific section cannot hide them.
    marker = '# BirdNET-Pi optional DS3231 RTC'
    if marker in text:
        return text, 'Already configured'
    return text.rstrip() + '\n\n' + marker + '\n[all]\ndtparam=i2c_arm=on\ndtoverlay=i2c-rtc,ds3231\n', 'Configured; reboot required'


def main():
    device = Path('/proc/device-tree/model')
    if not device.exists() or 'Raspberry Pi' not in device.read_text():
        print(json.dumps({'event': 'rtc_setup_skipped', 'reason': 'Not a Raspberry Pi'}))
        return
    assert os.geteuid() == 0, 'Run as root'
    target = next((p for p in (Path('/boot/firmware/config.txt'), Path('/boot/config.txt')) if p.is_file()), None)
    if target is None:
        raise RuntimeError('Boot config.txt not found')
    before = target.read_text()
    after, reason = configure(before)
    if after != before:
        backup = target.with_name(target.name + '.birdnet-rtc-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
        backup.write_bytes(target.read_bytes())
        descriptor, temporary = tempfile.mkstemp(prefix='.birdnet-rtc-', dir=target.parent)
        try:
            with os.fdopen(descriptor, 'w') as stream:
                stream.write(after)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, target.stat().st_mode & 0o777)
            os.replace(temporary, target)
        finally:
            Path(temporary).unlink(missing_ok=True)
    root = Path(__file__).resolve().parents[1]
    helper = Path('/usr/local/libexec/rtc_time_sync.py')
    helper.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / 'scripts/rtc_time_sync.py', helper)
    helper.chmod(0o755)
    for unit in ('birdnet-rtc-restore.service', 'birdnet-rtc-save.service', 'birdnet-rtc-save.timer'):
        shutil.copyfile(root / 'templates' / unit, Path('/etc/systemd/system') / unit)
    # An RTC added before the next boot is read automatically. Missing RTC is a fast skip.
    rules = Path('/etc/udev/rules.d/80-birdnet-rtc.rules')
    rules.parent.mkdir(parents=True, exist_ok=True)
    rules.write_text('ACTION=="add", SUBSYSTEM=="rtc", KERNEL=="rtc[0-9]*", TAG+="systemd", ENV{SYSTEMD_WANTS}+="birdnet-rtc-restore.service"\n')
    dropin = Path('/etc/systemd/system/fake-hwclock.service.d')
    dropin.mkdir(parents=True, exist_ok=True)
    (dropin / '80-real-rtc.conf').write_text('[Service]\nExecCondition=/usr/bin/python3 /usr/local/libexec/rtc_time_sync.py --fake-condition\n')
    adjtime = Path('/etc/adjtime')
    lines = adjtime.read_text().splitlines() if adjtime.exists() else ['0.0 0 0.0', '0']
    adjtime.write_text('\n'.join((lines + ['0.0 0 0.0', '0'])[:2]) + '\nUTC\n')
    subprocess.run(['systemctl', 'daemon-reload'], check=True, timeout=60)
    subprocess.run(['udevadm', 'control', '--reload-rules'], check=True, timeout=30)
    subprocess.run(['systemctl', 'enable', 'birdnet-rtc-restore.service'], check=True, timeout=30)
    subprocess.run(['systemctl', 'enable', '--now', 'birdnet-rtc-save.timer'], check=True, timeout=30)
    # Preserve the selected NTP implementation; timedated selects an installed provider.
    ntp = subprocess.run(['timedatectl', 'set-ntp', 'true'], capture_output=True, text=True, timeout=30)
    print(json.dumps({'event': 'rtc_setup', 'reason': reason, 'hardware_present': bool(list(Path('/sys/class/rtc').glob('rtc*'))),
                      'ntp_enabled': ntp.returncode == 0, 'ntp_error': ntp.stderr.strip()}))


if __name__ == '__main__':
    main()
