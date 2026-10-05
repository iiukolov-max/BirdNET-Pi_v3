#!/usr/bin/env python3
"""Private, consistent backups of database/configuration before code updates."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import uuid


def backup(root, configuration, destination):
    directory = destination / ('update-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    directory.mkdir(parents=True, mode=0o700)
    os.chmod(directory, 0o700)
    database = root / 'scripts/birds.db'
    if not database.is_file() or not configuration.is_file():
        raise RuntimeError('Missing database or configuration; update refused')
    source = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True, timeout=60)
    saved = sqlite3.connect(directory / 'birds.db')
    try:
        source.backup(saved, pages=256, sleep=0.01)
        if saved.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('Database backup is invalid')
    finally:
        saved.close()
        source.close()
    shutil.copy2(configuration, directory / 'birdnet.conf')
    for filename in ('.model-profiles.json', 'model_profiles.json', '.model_profiles.json'):
        for parent in (root, root / 'scripts'):
            path = parent / filename
            if path.is_file():
                shutil.copy2(path, directory / (parent.name + '-' + filename))
    commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    with (directory / 'code.tar').open('wb') as output:
        subprocess.run(['git', '-C', str(root), 'archive', 'HEAD'], stdout=output, check=True)
    # Preserve tracked local changes for remote migration without logging them.
    for filename, arguments in (('working-tree.patch', ['diff', '--binary']),
                                ('index.patch', ['diff', '--cached', '--binary'])):
        with (directory / filename).open('wb') as output:
            subprocess.run(['git', '-C', str(root), *arguments], stdout=output, check=True)
    (directory / 'metadata.json').write_text(json.dumps({'commit': commit, 'audio': 'Audio remains in its original location; not backed up here'}, indent=2) + '\n')
    for path in directory.iterdir():
        os.chmod(path, 0o600)
    return directory


if __name__ == '__main__':
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=root)
    parser.add_argument('--configuration', type=Path, default=Path('/etc/birdnet/birdnet.conf'))
    parser.add_argument('--destination', type=Path, default=root.parent / 'birdnet-backups')
    args = parser.parse_args()
    print(backup(args.root, args.configuration, args.destination))
