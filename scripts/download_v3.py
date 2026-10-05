#!/usr/bin/env python3
"""Download exactly the model artifacts pinned by this software release."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import urllib.request


def matches(path, artifact):
    if not path.is_file() or path.stat().st_size != artifact['bytes']:
        return False
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest() == artifact['sha256']


def download(manifest, directory):
    directory.mkdir(parents=True, exist_ok=True)
    for artifact in manifest['artifacts']:
        name = artifact['name']
        if Path(name).name != name or name in ('.', '..'):
            raise ValueError('Invalid artifact name')
        target = directory / name
        if matches(target, artifact):
            print('Verified existing artifact: ' + name)
            continue
        if shutil.disk_usage(directory).free < artifact['bytes'] + 16 * 1024**2:
            raise RuntimeError('Insufficient disk space for ' + name)
        for attempt in range(3):
            temporary = None
            try:
                fd, filename = tempfile.mkstemp(prefix='.v3-download-', dir=directory)
                temporary = Path(filename)
                with os.fdopen(fd, 'wb') as output:
                    request = urllib.request.Request(artifact['url'], headers={'User-Agent': 'BirdNET-Pi-v3-model-installer/1'})
                    with urllib.request.urlopen(request, timeout=90) as response:
                        written = 0
                        while True:
                            block = response.read(1024 * 1024)
                            if not block:
                                break
                            written += len(block)
                            if written > artifact['bytes']:
                                raise ValueError('Downloaded artifact exceeds expected size')
                            output.write(block)
                    output.flush()
                    os.fsync(output.fileno())
                if not matches(temporary, artifact):
                    raise ValueError('Model checksum/size mismatch: ' + name)
                os.chmod(temporary, 0o644)
                os.replace(temporary, target)
                temporary = None
                print('Downloaded and verified: ' + name)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)


def main():
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=root / 'model/v3-manifest.json')
    parser.add_argument('--directory', type=Path, default=root / 'model')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if manifest.get('schema_version') != 1:
        raise ValueError('Unsupported model manifest')
    download(manifest, args.directory)


if __name__ == '__main__':
    main()
