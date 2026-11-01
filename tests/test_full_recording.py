"""Full-length detections share audio and survive independent cleanup."""
import configparser
import datetime
import errno
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from utils.classes import ParseFileName, Detection
from utils import reporting
import normal_cleanup


class FullRecording(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.wav = self.root / '2026-11-01-birdnet-12:00:00.wav'
        sf.write(self.wav, np.sin(np.arange(32000 * 6) * .04) * .1, 32000)
        parser = configparser.ConfigParser()
        parser['settings'] = dict(EXTRACTION_LENGTH='6', RECORDING_LENGTH='6',
            EXTRACTED=str(self.root / 'extracted'), AUDIOFMT='flac', RAW_SPECTROGRAM='0')
        self.conf = parser['settings']
        self.file = ParseFileName(str(self.wav))
        self.addCleanup(patch.stopall)
        patch.object(reporting, 'get_settings', return_value=self.conf).start()
        patch.object(reporting, 'spectrogram').start()

    def detection(self, seconds=0):
        return Detection(datetime.datetime(2026, 11, 1, 12), seconds, seconds + 3,
                         'Pica pica', 'Eurasian Magpie', .9)

    def test_archive_links_survive_original_and_other_detection_removal(self):
        original = self.root / self.wav.with_suffix('.flac').name
        data, rate = sf.read(self.wav)
        sf.write(original, data, rate)
        self.file.original_recording = str(original)
        with patch.object(reporting, 'extract_safe', side_effect=AssertionError('trimmed')), \
             patch.object(reporting.subprocess, 'run', side_effect=AssertionError('encoded')):
            first = Path(reporting.extract_detection(self.file, self.detection()))
            second = Path(reporting.extract_detection(self.file, self.detection(3)))
        self.assertTrue(os.path.samefile(original, first))
        self.assertTrue(os.path.samefile(first, second))
        self.assertEqual(sf.info(second).frames, 32000 * 6)
        original.unlink()
        base = self.root / 'extracted' / 'By_Date'
        protected = {second.relative_to(base).as_posix()}
        # Cleanup may remove the unprotected name, but the protected audio survives.
        from collections import namedtuple
        Disk = namedtuple('Disk', 'total used free')
        normal_cleanup.cleanup(base, protected, usage=lambda _: Disk(100, 99, 1))
        self.assertFalse(first.exists())
        self.assertEqual(sf.info(second).frames, 32000 * 6)
        np.testing.assert_allclose(sf.read(second)[0], data, atol=1e-4)

    def test_normal_wav_encodes_once_and_keeps_entire_recording(self):
        native_run = subprocess.run
        with patch.object(reporting.subprocess, 'run', wraps=native_run) as run:
            first = Path(reporting.extract_detection(self.file, self.detection()))
            second = Path(reporting.extract_detection(self.file, self.detection(3)))
        self.assertEqual(run.call_count, 1)
        self.assertNotIn('trim', run.call_args.args[0])
        self.assertTrue(os.path.samefile(first, second))
        self.wav.unlink()
        self.assertEqual(sf.info(second).frames, 32000 * 6)

    def test_short_extraction_still_trims(self):
        self.conf['EXTRACTION_LENGTH'] = '3'
        result = reporting.extract_detection(self.file, self.detection(3))
        self.assertEqual(sf.info(result).frames, 32000 * 3)

    def test_cross_filesystem_falls_back_to_complete_copy(self):
        self.conf['AUDIOFMT'] = 'wav'
        with patch.object(reporting.os, 'link', side_effect=OSError(errno.EXDEV, 'cross device')):
            result = reporting.extract_detection(self.file, self.detection(3))
        self.assertEqual(Path(result).read_bytes(), self.wav.read_bytes())

    def test_link_failure_does_not_publish_partial_file(self):
        self.conf['AUDIOFMT'] = 'wav'
        with patch.object(reporting.os, 'link', side_effect=OSError(errno.ENOSPC, 'full')):
            with self.assertRaises(OSError):
                reporting.extract_detection(self.file, self.detection())
        self.assertEqual(list((self.root / 'extracted').rglob('*.wav')), [])

    def test_stale_partial_from_interrupted_encoder_does_not_block_link(self):
        self.conf['AUDIOFMT'] = 'wav'
        directory = self.root / 'extracted' / 'By_Date' / '2026-11-01' / 'Eurasian_Magpie'
        directory.mkdir(parents=True)
        stale = directory / 'Eurasian_Magpie-90-2026-11-01-birdnet-12:00:00.wav.partial.wav'
        stale.write_bytes(b'interrupted old encoder')
        result = reporting.extract_detection(self.file, self.detection())
        self.assertTrue(os.path.samefile(result, self.wav))
        self.assertEqual(sf.info(result).frames, 32000 * 6)
        self.assertEqual(stale.read_bytes(), b'interrupted old encoder')


if __name__ == '__main__':
    unittest.main()
