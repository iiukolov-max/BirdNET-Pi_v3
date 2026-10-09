import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/install_rtc.py'
spec = importlib.util.spec_from_file_location('rtc_config', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RTCConfigTests(unittest.TestCase):
    def test_board_section_and_repeat(self):
        before = '# User config\n[pi5]\ndtoverlay=nospi10\n'
        after, _ = module.configure(before)
        self.assertTrue(after.startswith(before))
        self.assertIn('[all]\ndtparam=i2c_arm=on\ndtoverlay=i2c-rtc,ds3231', after)
        self.assertEqual(module.configure(after)[0], after)

    def test_preserves_other_rtc(self):
        before = '[all]\ndtoverlay=i2c-rtc,pcf8523\n'
        self.assertEqual(module.configure(before)[0], before)


if __name__ == '__main__':
    unittest.main()
