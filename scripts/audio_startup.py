#!/usr/bin/env python3
"""Audio boot snapshot, also safe to invoke manually after installing logging."""
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.audio_log import emit
from utils.audio_snapshot import snapshot


def main():
    try:
        result = subprocess.run(['systemctl', 'show', 'birdnet_recording.service',
                                 '-p', 'ActiveState', '-p', 'NRestarts', '-p', 'ExecMainStatus'],
                                capture_output=True, text=True, timeout=3)
        service = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
        # Tail only: never read the growing persistent log in full here.
        import json
        last = None
        try:
            with open('/var/log/birdnet/audio.jsonl', 'rb') as stream:
                stream.seek(0, 2)
                stream.seek(max(0, stream.tell() - 65536))
                for line in stream.read().splitlines():
                    try:
                        row = json.loads(line)
                        if row.get('source') in ('archive_recording', 'birdnet_recording', 'heartbeat'):
                            last = {k: row.get(k) for k in ('event', 'time', 'boot_id', 'reason')}
                    except ValueError:
                        pass
        except OSError:
            pass
        emit('startup', 'startup', console=True, snapshot=snapshot, service=service, last_recording_event=last,
             phase='late' if '--late' in sys.argv else 'early')
    except Exception:
        pass


if __name__ == '__main__':
    main()
