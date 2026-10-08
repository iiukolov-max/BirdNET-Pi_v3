"""Check generated fresh-install defaults without touching an installation."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InstallDefaultsTest(unittest.TestCase):
    def test_fresh_install_defaults(self):
        text = (ROOT/'scripts/install_config.sh').read_text()
        config = dict(re.findall(r'^([A-Z_]+)=(.*)$', text, re.M))
        self.assertEqual(config['OPERATION_MODE'], 'normal')
        self.assertEqual(config['MODEL'], 'BirdNET+_V3.0-preview3.1_Global_11K_FP16_pruned')
        self.assertEqual(config['GEO_MODEL'], 'v3.0.4')
        for row in json.loads((ROOT/'scripts/service_policy.json').read_text()):
            if row.get('fixed'):continue
            self.assertEqual(row['default'], 1)
            self.assertEqual(config['SERVICE_ALLOW_'+row['key']], '1')
        self.assertIn('if ! [ -f ${birdnet_conf} ];then\n  install_config', text)

    def test_both_geomodel_assets_are_installed(self):
        manifest = json.loads((ROOT/'model/v3-manifest.json').read_text())
        names = {row['name'] for row in manifest['artifacts']}
        self.assertIn('BirdNET+_Geomodel_V3.0.4_Global_14K_FP32.tflite', names)
        self.assertIn('BirdNET+_Geomodel_V3.0.4_Global_14K_Labels.txt', names)


if __name__ == '__main__':unittest.main()
