import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audio_led_alert import Alert, capture_present


class AudioLED(unittest.TestCase):
    def test_installed_symlink_entrypoints(self):
        import subprocess
        scripts=Path(__file__).resolve().parents[1]/'scripts'
        with tempfile.TemporaryDirectory() as directory:
            for name in ['prepare_microphone.py','audio_led_alert.py']:
                link=Path(directory)/name
                link.symlink_to(scripts/name)
                result=subprocess.run([sys.executable,str(link),'--help'],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)

    def test_double_flash_timing_and_restore_trigger(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name,value in [('trigger','none timer [actpwr]'),('brightness','1'),('max_brightness','1')]:
                (root/name).write_text(value)
            alert=Alert(root,root/'state.json')
            alert.start()
            self.assertEqual((root/'trigger').read_text(),'none')
            steps=[]
            class Stop:
                def wait(self,seconds):
                    steps.append(((root/'brightness').read_text(),seconds))
                    return False
            alert.pulse_pair(Stop())
            self.assertEqual(steps,[('1',.15),('0',.15),('1',.15),('0',1.0)])
            alert.restore()
            self.assertEqual((root/'trigger').read_text(),'actpwr')
            self.assertFalse((root/'state.json').exists())

    def test_restart_retains_original_state_and_capture_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name,value in [('trigger','[mmc0] none'),('brightness','1'),('max_brightness','1')]:
                (root/name).write_text(value)
            first=Alert(root,root/'state.json');first.start()
            restarted=Alert(root,root/'state.json');restarted.start();restarted.restore()
            self.assertEqual((root/'trigger').read_text(),'mmc0')
            self.assertFalse(capture_present(root))
            (root/'pcmC0D0p').touch()
            self.assertFalse(capture_present(root))
            (root/'pcmC0D0c').touch()
            self.assertTrue(capture_present(root))


if __name__=='__main__':unittest.main()
