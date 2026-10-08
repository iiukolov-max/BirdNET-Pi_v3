"""Check non-pi installations without installing packages or changing services."""
import importlib.util
import json
import os
from pathlib import Path
import pwd
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1]


class InstallationPathsTest(unittest.TestCase):
    def test_export_from_another_home_through_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'orangepi' / 'BirdNET-Pi'
            (root / 'scripts').mkdir(parents=True)
            shutil.copy2(SOURCE / 'export_birddb_verified.py', root)
            shutil.copy2(SOURCE / 'scripts/run_verified_export.py', root / 'scripts')
            with sqlite3.connect(root / 'scripts/birds.db') as db:
                db.execute('CREATE TABLE detections (Date, Time, Sci_Name, Com_Name, Confidence, Lat, Lon, Cutoff, Week, Sens, Overlap, File_Name)')
                db.execute("INSERT INTO detections VALUES ('2026-10-07', '12:00', 'Test bird', 'Test', .9, 0, 0, 0, 40, 1, 0, 'test.wav')")
                db.execute('CREATE TABLE detection_reviews (file_path, review_status, reviewed_at)')
                db.execute("INSERT INTO detection_reviews VALUES ('2026-10-07/Test/test.wav', 'correct', 'review-time')")
            launcher = Path(directory) / 'run_verified_export.py'
            launcher.symlink_to(root / 'scripts/run_verified_export.py')
            result = subprocess.run([sys.executable, str(launcher)], cwd='/',
                                    capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout)['rows'], 1)
            self.assertIn(';correct;review-time', (root / 'BirdDB_verified.txt').read_text())

    def test_model_labels_use_installation_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'orangepi' / 'BirdNET-Pi'
            (root / 'scripts').mkdir(parents=True)
            script = root / 'scripts/model_switch.py'
            shutil.copy2(SOURCE / 'scripts/model_switch.py', script)
            spec = importlib.util.spec_from_file_location('model_switch_fixture', script)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.BASE, root.resolve())
            with patch.object(module.subprocess, 'run') as run:
                module.labels()
            args = run.call_args.args[0]
            self.assertEqual(args[:3], ['sudo', '-u', pwd.getpwuid(root.stat().st_uid).pw_name])
            self.assertEqual(args[3], str(root.resolve() / 'birdnet/bin/python3'))

    @unittest.skipIf(os.geteuid() == 0, 'Installer intentionally rejects root')
    def test_orangepi_passes_user_check_and_reaches_existing_install_guard(self):
        # Stop before any real privileged operation or network access.
        with tempfile.TemporaryDirectory() as directory:
            stub = Path(directory) / 'id'
            stub.write_text('#!/bin/sh\necho orangepi\n')
            stub.chmod(0o755)
            script = (SOURCE / 'newinstaller.sh').read_text().replace(
                'target="$HOME/BirdNET-Pi"', 'target=' + directory)
            env = dict(os.environ, HOME='/home/orangepi', USER='stale-user',
                       PATH=directory + ':' + os.environ['PATH'])
            result = subprocess.run(['bash', '-c', script], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Existing installation found', result.stderr)


if __name__ == '__main__':
    unittest.main()
