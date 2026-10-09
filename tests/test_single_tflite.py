"""A failed canonical import must restore both package and distribution metadata."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

path=Path(__file__).resolve().parents[1]/'scripts/single_tflite.py'
spec=importlib.util.spec_from_file_location('single',path)
single=importlib.util.module_from_spec(spec);spec.loader.exec_module(single)

class SwitchTests(unittest.TestCase):
    def test_failed_probe_restores_package_and_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);site=root/'site';stage=root/'stage'
            site.mkdir();stage.mkdir()
            for name in ('tflite_runtime','tflite_runtime-2.17.1.dist-info'):
                (site/name).mkdir();(site/name/'original').write_text('preserve')
            (stage/'tflite_runtime').mkdir();(stage/'tflite_runtime-2.17.1.post2.dist-info').mkdir()
            with mock.patch.object(single.subprocess,'check_output',return_value=str(site)), \
                 mock.patch.object(single.subprocess,'run',side_effect=subprocess.CalledProcessError(1,'probe')):
                with self.assertRaises(subprocess.CalledProcessError):single.switch('python',stage)
            self.assertEqual((site/'tflite_runtime/original').read_text(),'preserve')
            self.assertTrue((site/'tflite_runtime-2.17.1.dist-info/original').exists())
            self.assertFalse((site/'tflite_runtime-2.17.1.post2.dist-info').is_symlink())

if __name__=='__main__':unittest.main()
