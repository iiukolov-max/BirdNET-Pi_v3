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
    def test_v2_v3_rounding_is_rejected(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            np.savez(root/'a.npz',output=np.array([[1.,2.]],dtype=np.float32))
            np.savez(root/'b.npz',output=np.array([[1.000001,2.]],dtype=np.float32))
            with np.load(root/'a.npz') as a,np.load(root/'b.npz') as b:
                with self.assertRaisesRegex(ValueError,'compatibility limits'):
                    installer.compare_compatibility(a,b)

    def test_legacy_v1_small_rounding_allowed_but_rank_change_rejected(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            np.savez(root/'a.npz',output=np.array([[1.,2.,3.,4.,5.,6.]],dtype=np.float32))
            np.savez(root/'b.npz',output=np.array([[1.000001,2.,3.,4.,5.,6.]],dtype=np.float32))
            with np.load(root/'a.npz') as a,np.load(root/'b.npz') as b:
                self.assertFalse(installer.compare_compatibility(a,b,legacy=True)['bit_exact'])
            np.savez(root/'b.npz',output=np.array([[2.,1.,3.,4.,5.,6.]],dtype=np.float32))
            with np.load(root/'a.npz') as a,np.load(root/'b.npz') as b:
                with self.assertRaises(ValueError):installer.compare_compatibility(a,b,legacy=True)

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
