#!/usr/bin/env python3
"""Switch the update source, preserving code, runtime data and the former remote."""
import argparse
import json
from pathlib import Path
import subprocess
from backup_before_update import backup

FORK = 'https://github.com/iiukolov-max/BirdNET-Pi_v3.git'


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def migrate(root, configuration, destination):
    old = git(root, 'config', '--get', 'remote.origin.url')
    if old.rstrip('/') in (FORK, FORK[:-4], 'git@github.com:iiukolov-max/BirdNET-Pi_v3.git'):
        return {'changed': False, 'message': 'Origin already points to this fork'}
    directory = backup(root, configuration, destination)
    remotes = git(root, 'remote').splitlines()
    preserved = 'upstream'
    suffix = 1
    while preserved in remotes:
        preserved = 'upstream-original-' + str(suffix)
        suffix += 1
    git(root, 'remote', 'rename', 'origin', preserved)
    try:
        git(root, 'remote', 'add', 'origin', FORK)
        git(root, 'config', 'remote.origin.fetch', '+refs/heads/main:refs/remotes/origin/main')
    except BaseException:
        if 'origin' in git(root, 'remote').splitlines():
            git(root, 'remote', 'remove', 'origin')
        git(root, 'remote', 'rename', preserved, 'origin')
        raise
    return {'changed': True, 'backup': str(directory), 'preserved_remote': preserved,
            'message': 'Only Git remotes changed. Local edits must be integrated before Update; no code or service was changed.'}


if __name__ == '__main__':
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--root', type=Path, default=root)
    parser.add_argument('--configuration', type=Path, default=Path('/etc/birdnet/birdnet.conf'))
    parser.add_argument('--destination', type=Path, default=root.parent / 'birdnet-backups')
    args = parser.parse_args()
    if args.apply:
        print(json.dumps(migrate(args.root, args.configuration, args.destination)))
    else:
        print('Preview: back up database/configuration/tracked edits, preserve old origin, set origin to ' + FORK)
        print('Use --apply to change remotes. This does not update application code or restart services.')
