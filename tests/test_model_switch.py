import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import model_switch as switch


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.config = self.base / 'birdnet.conf'
        self.state = self.base / 'profiles.json'
        self.old = ('MODEL=BirdNET_GLOBAL_6K_V2.4_Model_FP16\n'
                    'CONFIDENCE=0.6\nSENSITIVITY=1.25\nSF_THRESH=0.03\n'
                    'DATA_MODEL_VERSION=2\nPRIVACY_THRESHOLD=1\n')
        self.config.write_text(self.old)
        (self.base / 'model').mkdir()
        for model in switch.MODELS:
            (self.base / 'model' / (model + '.tflite')).write_bytes(b'0' * 1000001)
        def atomic(path, content):
            path.write_text(content)
        for name, value in [('BASE', self.base), ('CONFIG', self.config), ('STATE', self.state),
                            ('atomic', atomic), ('service', lambda *a: None), ('labels', lambda: None),
                            ('enforce_services', lambda: None), ('PAUSE_MARKER', self.base/'pause.json'),
                            ('active',lambda unit:unit!='birdnet-archive-analysis')]:
            patcher = patch.object(switch, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_roundtrip_restores_old_profile(self):
        with patch.object(switch, 'await_ready'):
            switch.apply(switch.replace(self.old, 'MODEL', switch.V3))
            new = switch.values(self.config.read_text())
            self.assertEqual(new['SENSITIVITY'], '1.0')
            self.assertEqual(new['PRIVACY_THRESHOLD'], '0')
            switch.apply(switch.replace(self.config.read_text(), 'MODEL', switch.MODELS[0]))
        self.assertEqual(self.config.read_text(), self.old)

    def test_failed_start_restores_exact_config(self):
        with patch.object(switch, 'await_ready', side_effect=[RuntimeError('bad model'), None]):
            with self.assertRaisesRegex(RuntimeError, 'Previous model and settings restored'):
                switch.apply(switch.replace(self.old, 'MODEL', switch.V3))
        self.assertEqual(self.config.read_text(), self.old)

    def test_first_legacy_selection_from_v3_uses_legacy_defaults(self):
        with patch.object(switch, 'await_ready'):
            switch.apply(switch.replace(self.old, 'MODEL', switch.V3))
            switch.apply(switch.replace(self.config.read_text(), 'MODEL', switch.MODELS[1]))
        restored = switch.values(self.config.read_text())
        self.assertEqual(restored['SENSITIVITY'], '1.25')
        self.assertEqual(restored['PRIVACY_THRESHOLD'], '1')

    def test_missing_model_does_not_change_config(self):
        (self.base / 'model' / (switch.V3 + '.tflite')).unlink()
        with self.assertRaisesRegex(ValueError, 'missing or incomplete'):
            switch.apply(switch.replace(self.old, 'MODEL', switch.V3))
        self.assertEqual(self.config.read_text(), self.old)

    def test_unsupported_model_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unknown model'):
            switch.apply(switch.replace(self.old, 'MODEL', '../../unknown'))

    def test_optional_permission_change_keeps_core_running(self):
        with patch.object(switch,'enforce_services') as enforce, patch.object(switch,'service') as analysis, patch.object(switch,'recording_service') as recording:
            switch.apply(switch.replace(self.old,'SERVICE_ALLOW_TERMINAL','0'))
            enforce.assert_called_once()
            analysis.assert_not_called();recording.assert_not_called()
            self.assertEqual(switch.values(self.config.read_text())['SERVICE_ALLOW_TERMINAL'],'0')

    def test_failed_permissions_apply_restores_previous_configuration(self):
        with patch.object(switch,'enforce_services',side_effect=[RuntimeError('policy failure'),None]) as enforce:
            with self.assertRaisesRegex(RuntimeError,'Previous model and settings restored'):
                switch.apply(switch.replace(self.old,'SERVICE_ALLOW_TERMINAL','0'))
            self.assertEqual(self.config.read_text(),self.old)
            self.assertEqual(enforce.call_count,2)


if __name__ == '__main__':
    unittest.main()
