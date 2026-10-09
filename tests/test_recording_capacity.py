import importlib.util
from collections import namedtuple
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('capacity',Path(__file__).resolve().parents[1]/'scripts/recording_capacity.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
Disk=namedtuple('Disk','total used free')

class CapacityTests(unittest.TestCase):
    def setUp(self):
        self.conf={'AUDIOFMT':'flac','RECORDING_LENGTH':'30','CHANNELS':'1','ARCHIVE_MAX_USED_PERCENT':'85'}
        self.disk=Disk(64*1024**3,10*1024**3,54*1024**3)

    def test_silent_old_measurement_uses_settings(self):
        result=module.capacity(self.conf,self.disk,{'format':'flac','segment_seconds':30,'bytes_per_second':400})
        self.assertEqual(result['estimate_source'],'format_estimate')
        self.assertLess(result['estimated_days'],20)

    def test_settings_change_invalidates_measurement(self):
        measured={'format':'flac','segment_seconds':30,'channels':1,'sample_rate':48000,'has_signal':True,'bytes_per_second':40000}
        self.assertEqual(module.capacity(self.conf,self.disk,measured)['estimate_source'],'measured')
        for key,value in [('AUDIOFMT','mp3'),('RECORDING_LENGTH','15'),('CHANNELS','2')]:
            changed={**self.conf,key:value}
            self.assertEqual(module.capacity(changed,self.disk,measured)['estimate_source'],'format_estimate')

    def test_lower_cleanup_threshold_reduces_capacity(self):
        a=module.capacity(self.conf,self.disk)
        b=module.capacity({**self.conf,'ARCHIVE_MAX_USED_PERCENT':'70'},self.disk)
        self.assertLess(b['estimated_files'],a['estimated_files'])
        self.assertLess(b['estimated_days'],a['estimated_days'])

    def test_duration_changes_file_count_but_not_daily_audio_volume(self):
        a=module.capacity(self.conf,self.disk)
        b=module.capacity({**self.conf,'RECORDING_LENGTH':'60'},self.disk)
        self.assertAlmostEqual(b['estimated_files']/a['estimated_files'],.5,delta=.01)
        self.assertAlmostEqual(b['estimated_days']/a['estimated_days'],1,delta=.01)

    def test_more_channels_reduce_capacity_and_formats_differ(self):
        a=module.capacity(self.conf,self.disk)
        b=module.capacity({**self.conf,'CHANNELS':'2'},self.disk)
        self.assertLess(b['estimated_days'],a['estimated_days'])
        wav=module.capacity({**self.conf,'AUDIOFMT':'wav'},self.disk)
        mp3=module.capacity({**self.conf,'AUDIOFMT':'mp3'},self.disk)
        self.assertLess(wav['estimated_days'],a['estimated_days'])
        self.assertGreater(mp3['estimated_days'],a['estimated_days'])

    def test_already_at_trigger_has_zero_capacity(self):
        result=module.capacity(self.conf,Disk(64*1024**3,60*1024**3,4*1024**3))
        self.assertEqual(result['estimated_files'],0)
        self.assertEqual(result['estimated_days'],0)

if __name__=='__main__':unittest.main()
