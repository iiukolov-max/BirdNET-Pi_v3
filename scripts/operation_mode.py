"""Small systemd gate: recording-only mode must never load the acoustic model."""
import sys
import os
import signal
import time
from utils.helpers import get_settings

if __name__ == '__main__':
    if len(sys.argv)>2 and sys.argv[1]=='--stop-recording':
        pid=int(sys.argv[2])
        try:
            cmd=open('/proc/'+str(pid)+'/cmdline','rb').read()
            if pid>1 and b'/archive_recording.py' in cmd:
                os.kill(pid,signal.SIGTERM)
                for _ in range(50):
                    if not os.path.exists('/proc/'+str(pid)):break
                    time.sleep(.5)
        except (ProcessLookupError,FileNotFoundError):pass
        sys.exit(0)
    mode = get_settings().get('OPERATION_MODE', 'normal')
    if mode not in ('normal', 'archive'):
        raise ValueError('Invalid OPERATION_MODE')
    sys.exit(0 if mode == 'normal' else 1)
