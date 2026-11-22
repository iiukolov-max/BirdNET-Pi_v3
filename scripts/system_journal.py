"""Apply BirdNET's bounded system journal policy without deleting saved logs."""
import os
from pathlib import Path
import subprocess
import tempfile

KEY = 'PERSISTENT_SYSTEM_JOURNAL'
DROP_IN = Path('/etc/systemd/journald.conf.d/80-birdnet-persistent-journal.conf')
PERSISTENT = (b'[Journal]\nStorage=persistent\nSystemMaxUse=128M\n'
              b'SystemMaxFileSize=8M\nSystemKeepFree=512M\nMaxFileSec=1day\n'
              b'MaxRetentionSec=14day\nSyncIntervalSec=30s\n')
VOLATILE = b'[Journal]\nStorage=volatile\n'


def run(*command):
    return subprocess.run(command, check=True, capture_output=True, text=True, timeout=30).stdout


def read():
    try:
        return DROP_IN.read_bytes()
    except FileNotFoundError:
        return None


def write(content):
    if content is None:
        DROP_IN.unlink(missing_ok=True)
        return
    DROP_IN.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=DROP_IN.parent, delete=False) as stream:
        name = Path(stream.name)
        try:
            stream.write(content)
            stream.flush()
            os.fchmod(stream.fileno(), 0o644)
            os.fsync(stream.fileno())
            os.replace(name, DROP_IN)
        finally:
            name.unlink(missing_ok=True)


def reload(enabled):
    run('systemctl', 'restart', 'systemd-journald.service')
    if enabled:
        run('journalctl', '--flush')
    run('journalctl', '--sync')
    run('systemctl', 'is-active', '--quiet', 'systemd-journald.service')


def effective_storage():
    config = run('systemd-analyze', 'cat-config', 'systemd/journald.conf')
    choices = [line.split('=', 1)[1].strip() for line in config.splitlines()
               if line.strip().startswith('Storage=')]
    return choices[-1] if choices else 'auto'


def restore(previous):
    if read() != previous:
        write(previous)
        reload(effective_storage() == 'persistent')


def apply(value):
    enabled = value == '1'
    previous = read()
    content = PERSISTENT if enabled else VOLATILE
    try:
        if content != previous:
            write(content)
        if effective_storage() != ('persistent' if enabled else 'volatile'):
            raise RuntimeError('Another system configuration overrides journal storage')
        if content != previous:
            reload(enabled)
    except (OSError, subprocess.SubprocessError, RuntimeError) as error:
        try:
            restore(previous)
        except (OSError, subprocess.SubprocessError) as rollback:
            raise RuntimeError('Could not restore the previous system journal configuration') from rollback
        raise RuntimeError('Could not change system journal storage: ' + str(error)) from error
    return previous
