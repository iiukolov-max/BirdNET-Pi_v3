#!/usr/bin/env python3
"""Explicit Zero 2 W headless profile, with boot backup and reboot validation."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import tempfile


def prepare(config, cmdline):
    tokens = cmdline.strip().split()
    if len(cmdline.strip().splitlines()) != 1 or not tokens:
        raise ValueError('Kernel cmdline must contain one non-empty line')
    tokens = [token for token in tokens if not token.startswith('cma=')]
    tokens.append('cma=0')
    lines = []
    for line in config.splitlines():
        if re.match(r'^\s*dtoverlay=vc4-(?:f?kms)-v3d(?:,|\s*$)', line):
            lines.append('# Headless BirdNET: ' + line)
        elif re.match(r'^\s*(gpu_mem|camera_auto_detect|display_auto_detect)\s*=', line):
            continue
        else:
            lines.append(line)
    block = '# BirdNET-Pi Zero 2 W headless profile'
    # Always put settings into an unconditional section, including reapplication
    # after someone adds another board-specific section at the end of the file.
    if block not in lines:
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ['', block]
    if not lines or lines[-1].strip() != '[all]':
        lines.append('[all]')
    lines += ['gpu_mem=16', 'camera_auto_detect=0', 'display_auto_detect=0']
    return '\n'.join(lines).rstrip() + '\n', ' '.join(tokens) + '\n'


def atomic(path, content):
    info = path.stat()
    fd, name = tempfile.mkstemp(prefix='.birdnet-boot-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, info.st_mode & 0o777)
        if hasattr(os, 'chown') and os.geteuid() == 0:
            os.chown(name, info.st_uid, info.st_gid)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def apply(boot, backups):
    model_path = Path('/proc/device-tree/model')
    if not model_path.exists() or 'Raspberry Pi Zero 2' not in model_path.read_text().rstrip('\0'):
        raise RuntimeError('This profile is restricted to Raspberry Pi Zero 2 W')
    config, cmdline = boot / 'config.txt', boot / 'cmdline.txt'
    before = config.read_text(), cmdline.read_text()
    after = prepare(*before)
    if before == after:
        return {'changed': False, 'message': 'Headless boot profile already written; verify after reboot'}
    backup = backups / ('zero2-headless-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True)
    for path in (config, cmdline):
        shutil.copy2(path, backup / path.name)
    try:
        atomic(config, after[0]); atomic(cmdline, after[1])
    except BaseException:
        atomic(config, before[0]); atomic(cmdline, before[1])
        raise
    return {'changed': True, 'backup': str(backup), 'message': 'Reboot required; graphics and camera disabled'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--boot-directory', type=Path,
                        default=Path('/boot/firmware') if Path('/boot/firmware/config.txt').exists() else Path('/boot'))
    parser.add_argument('--backup-directory', type=Path, default=Path('/home/pi/birdnet-backups'))
    args = parser.parse_args()
    if args.apply:
        print(json.dumps(apply(args.boot_directory, args.backup_directory)))
    else:
        values = dict(re.findall(r'^(CmaTotal|MemAvailable|MemTotal):\s+(\d+) kB', Path('/proc/meminfo').read_text(), re.M))
        print(json.dumps({'memory_kib': values, 'cma_disabled': values.get('CmaTotal') == '0'}))
