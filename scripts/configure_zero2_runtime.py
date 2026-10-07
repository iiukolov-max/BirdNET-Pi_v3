#!/usr/bin/env python3
"""Provision disk-backed fallback swap for the explicitly selected Zero 2 W profile."""
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

SWAP = Path('/var/lib/birdnet/swapfile')
UNIT = 'var-lib-birdnet-swapfile.swap'
SIZE = 1024 * 1024 * 1024


def run(*args):
    subprocess.run(args, check=True)


def write_managed(path, content):
    if path.exists() and path.read_text() != content:
        raise RuntimeError('Existing custom configuration must be reviewed: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    path.chmod(0o644)


def main():
    if os.geteuid() != 0:
        raise RuntimeError('Run as root')
    if 'Raspberry Pi Zero 2' not in Path('/proc/device-tree/model').read_text():
        raise RuntimeError('This runtime profile is restricted to Raspberry Pi Zero 2 W')
    created = False
    SWAP.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if SWAP.exists() or SWAP.is_symlink():
        info = SWAP.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_size != SIZE:
            raise RuntimeError('Refusing to overwrite existing swap path: ' + str(SWAP))
        kind = subprocess.check_output(['blkid', '-p', '-s', 'TYPE', '-o', 'value', str(SWAP)], text=True).strip()
        if kind != 'swap':
            raise RuntimeError('Existing path is not a swap file')
    else:
        if shutil.disk_usage(SWAP.parent).free < SIZE + 512 * 1024 * 1024:
            raise RuntimeError('At least 1.5 GiB free disk space is required for fallback swap')
        descriptor = os.open(SWAP, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)
        try:
            run('dd', 'if=/dev/zero', 'of=' + str(SWAP), 'bs=1M', 'count=1024', 'conv=fsync', 'status=none')
            run('mkswap', str(SWAP))
        except BaseException:
            SWAP.unlink()  # Only the new, not-yet-activated file belongs to this attempt.
            raise
        created = True
    SWAP.chmod(0o600)
    write_managed(Path('/etc/systemd/system') / UNIT,
                  '[Unit]\nDescription=BirdNET Zero 2 W disk fallback swap\n'
                  '[Swap]\nWhat=' + str(SWAP) + '\nPriority=10\n'
                  '[Install]\nWantedBy=swap.target\n')
    write_managed(Path('/etc/systemd/system/birdnet_analysis.service.d/45-zero2-swap.conf'),
                  '[Unit]\nRequires=' + UNIT + '\nAfter=' + UNIT + '\n')
    run('systemctl', 'daemon-reload')
    run('systemctl', 'enable', '--now', UNIT)
    print(json.dumps({'disk_swap_bytes': SIZE, 'created': created, 'priority': 10,
                      'message': 'Existing swap is retained; zram with higher priority is used first'}))


if __name__ == '__main__':
    main()
