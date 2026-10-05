#!/usr/bin/env python3
"""Web launcher for the unchanged export_birddb_verified.py."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parent.parent
    output = root / 'BirdDB_verified.txt'
    previous = None
    if output.exists():
        fd, name = tempfile.mkstemp(prefix='.verified-backup-', dir=root)
        os.close(fd)
        previous = Path(name)
        shutil.copy2(output, previous)
    try:
        result = subprocess.run(
            [sys.executable, str(root / 'export_birddb_verified.py')],
            cwd=root, capture_output=True, text=True, check=True,
        )
        if not output.is_file():
            raise RuntimeError('Exporter did not create BirdDB_verified.txt')
        with output.open(encoding='utf-8') as stream:
            rows = max(0, sum(1 for _ in stream) - 1)
        print(json.dumps({'ok': True, 'rows': rows, 'bytes': output.stat().st_size,
                          'message': result.stdout.strip()}))
    except Exception as error:
        if previous is not None:
            os.replace(previous, output)
            previous = None
        elif output.exists():
            output.unlink()
        message = str(error)
        if isinstance(error, subprocess.CalledProcessError):
            message = error.stderr.strip() or message
        print(json.dumps({'ok': False, 'message': message}))
        return 1
    finally:
        if previous is not None:
            previous.unlink(missing_ok=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
