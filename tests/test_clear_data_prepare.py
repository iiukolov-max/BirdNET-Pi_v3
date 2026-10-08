"""Run only the pre-deletion shell prefix with fake services and temp files."""
import fcntl
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'scripts/clear_all_data.sh'
class ClearDataPrepareTest(unittest.TestCase):
    def run_prefix(self, failure='', busy=False):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);scripts=root/'BirdNET-Pi/scripts';scripts.mkdir(parents=True)
            log=root/'events';lock=root/'lock'
            (scripts/'archive_recording_pause.py').write_text("import os,sys\nwith open(os.environ['EVENTS'],'a') as f:f.write('hook '+sys.argv[1]+'\\n')\n")
            sudo=root/'sudo';sudo.write_text('#!/bin/sh\nexec "$@"\n');sudo.chmod(0o755)
            service=root/'systemctl'
            service.write_text('''#!/bin/sh
echo "$*" >> "$EVENTS"
case "$1" in
  cat) exit 0;;
  stop) [ "$FAILURE" = "$2" ] && exit 1; exit 0;;
  show) if [ "$FAILURE" = still-active ]; then echo active; else echo inactive; fi;;
esac
''');service.chmod(0o755)
            text=SOURCE.read_text();assert text.count('echo "Removing all data . . . "')==1
            # No deletion command is present in the executed prefix.
            prefix=text.split('echo "Removing all data . . . "')[0]
            prefix=prefix.replace('source /etc/birdnet/birdnet.conf','BIRDNET_USER=fixture')
            prefix=prefix.replace('HOME=/home/${BIRDNET_USER}','HOME='+shlex.quote(str(root)))
            prefix=prefix.replace('/run/lock/birdnet-model-switch.lock',str(lock))
            with lock.open('a') as held:
                if busy:fcntl.flock(held,fcntl.LOCK_EX|fcntl.LOCK_NB)
                r=subprocess.run(['bash','-c',prefix+'\necho CLEANUP_READY\n'],env=dict(os.environ,PATH=str(root)+':'+os.environ['PATH'],EVENTS=str(log),FAILURE=failure),capture_output=True,text=True)
            return r,log.read_text().splitlines() if log.exists() else []
    def test_cancel_then_stop_all_before_deletion(self):
        result,events=self.run_prefix()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('CLEANUP_READY',result.stdout)
        self.assertLess(events.index('hook cancel'),events.index('stop birdnet-archive-analysis.service'))
        self.assertLess(events.index('stop birdnet-archive-analysis.service'),events.index('stop birdnet_recording.service'))
        self.assertIn('stop birdnet_analysis.service',events)
    def test_stop_failure_prevents_deletion(self):
        for unit in ('birdnet-archive-analysis.service','birdnet_recording.service','birdnet_analysis.service'):
            with self.subTest(unit=unit):
                result,_=self.run_prefix(unit)
                self.assertNotEqual(result.returncode,0)
                self.assertNotIn('CLEANUP_READY',result.stdout)
    def test_active_service_prevents_deletion(self):
        result,_=self.run_prefix('still-active')
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('CLEANUP_READY',result.stdout)
    def test_lock_blocks_concurrent_start(self):
        result,events=self.run_prefix(busy=True)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(events,[])
        self.assertNotIn('CLEANUP_READY',result.stdout)

if __name__=='__main__':unittest.main()
