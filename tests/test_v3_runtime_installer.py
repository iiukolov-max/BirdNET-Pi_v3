"""Checksums and failed optional installation must never replace a profile."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

path=Path(__file__).resolve().parents[1]/'scripts/install_v3_runtime.py'
spec=importlib.util.spec_from_file_location('runtime_installer',path)
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)

class RuntimeInstallerTests(unittest.TestCase):
    def test_corrupt_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'assets').mkdir();(root/'target').mkdir()
            (root/'assets/runtime.whl').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'checksum'):
                installer.artifact({'name':'runtime.whl','bytes':7,'sha256':'0'*64},root/'target',root/'assets')

    def test_path_traversal_rejected_before_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'Unsafe'):
                installer.artifact({'name':'../outside'},Path(folder),Path(folder))

    def test_unsupported_target_does_not_touch_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);profile=root/'profile.json';profile.write_text('{"enabled":false}')
            manifest=root/'manifest.json';manifest.write_text(json.dumps({'schema_version':1,'supported':{}}))
            args=mock.Mock(manifest=manifest,profile=profile)
            with mock.patch.object(installer,'compatible',return_value=False):installer.install(args)
            self.assertEqual(profile.read_text(),'{"enabled":false}')

    def test_invalid_manifest_does_not_touch_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);profile=root/'profile.json';profile.write_text('{"enabled":true}')
            manifest=root/'manifest.json';manifest.write_text('{"schema_version":99}')
            with self.assertRaises(ValueError):installer.install(mock.Mock(manifest=manifest,profile=profile))
            self.assertEqual(profile.read_text(),'{"enabled":true}')

if __name__=='__main__':unittest.main()
