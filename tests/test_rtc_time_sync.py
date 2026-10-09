import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

source = Path(__file__).resolve().parents[1] / 'scripts/rtc_time_sync.py'
spec = importlib.util.spec_from_file_location('rtc_time_sync', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RTCSyncTests(unittest.TestCase):
    def execute(self, action, present=True, synced=False, epoch='1791560000', kernel='0'):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            if present:
                device = base / 'rtc0'
                device.mkdir()
                (device / 'hctosys').write_text(kernel)
                (device / 'since_epoch').write_text(epoch)
            with patch.object(module, 'Path', return_value=base), patch.object(module.shutil, 'which', return_value='/sbin/hwclock'), patch.object(module, 'ntp_synchronized', return_value=synced), patch.object(module, 'run') as run:
                run.side_effect = lambda *args: subprocess.CompletedProcess(args, 0, 'yes' if synced else 'no', '')
                result = module.synchronize(action)
                return result, [call.args for call in run.call_args_list]

    def test_missing_rtc_never_reads_or_writes(self):
        for action in ('restore', 'save'):
            self.assertEqual(self.execute(action, present=False), (0, []))

    def test_early_boot_does_not_wait_for_dbus(self):
        with patch.object(module, 'run') as run:
            module.ntp_synchronized('restore')
            run.assert_not_called()

    def test_unsynchronized_system_never_writes_rtc(self):
        _, calls = self.execute('save')
        self.assertFalse(any('hwclock' in c[0] for c in calls))

    def test_ntp_time_is_not_overwritten_by_rtc(self):
        _, calls = self.execute('restore', synced=True)
        self.assertFalse(any('hwclock' in c[0] for c in calls))

    def test_invalid_rtc_waits_for_ntp(self):
        _, calls = self.execute('restore', epoch='0')
        self.assertFalse(any('hwclock' in c[0] for c in calls))

    def test_restore_and_save_use_utc(self):
        for action, expected in (('restore', '--hctosys'), ('save', '--systohc')):
            _, calls = self.execute(action, synced=action == 'save')
            self.assertIn(expected, calls[-1])
            self.assertIn('--utc', calls[-1])


if __name__ == '__main__':
    unittest.main()
