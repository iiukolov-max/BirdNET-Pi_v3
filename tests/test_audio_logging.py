"""Audio diagnostics contracts; hardware scenarios are documented separately."""
from array import array
import contextlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from utils import audio_log
from utils.audio_metrics import Levels, Period
import prepare_microphone as microphone
import archive_recording as archive
from read_audio_log import summaries, load


class AudioLogging(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/dev/shm' if Path('/dev/shm').is_dir() else None)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / 'audio.jsonl'
        self.log.touch(mode=0o640)
        self.state = self.root / 'run'
        self.state.mkdir()
        self.options = dict(log_path=self.log, state_dir=self.state)

    def rows(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_format_retry_timer_transition_and_snapshot(self):
        with patch.object(audio_log.time, 'monotonic', return_value=0), \
                patch.object(audio_log, 'envelope', wraps=audio_log.envelope):
            snap = lambda: {'cards': 'none'}
            self.assertTrue(audio_log.emit('microphone_not_found', 'prepare_microphone', repeat=True,
                                           snapshot=snap, **self.options))
        with patch.object(audio_log.time, 'monotonic', return_value=1):
            self.assertTrue(audio_log.emit('microphone_not_found', 'prepare_microphone', repeat=True,
                                           snapshot=lambda: self.fail('repeated snapshot'), **self.options))
        with patch.object(audio_log.time, 'monotonic', return_value=601):
            audio_log.emit('microphone_not_found', 'prepare_microphone', repeat=True, **self.options)
        with patch.object(audio_log.time, 'monotonic', return_value=602):
            audio_log.emit('microphone_not_found', 'prepare_microphone', repeat=True, **self.options)
            audio_log.emit('microphone_selected', 'prepare_microphone', repeat=True, **self.options)
        rows = self.rows()
        self.assertEqual([r['event'] for r in rows],
                         ['microphone_not_found', 'repeated', 'repeated', 'microphone_selected'])
        self.assertEqual([r['count'] for r in rows if r['event'] == 'repeated'], [2, 1])
        self.assertTrue({'schema_version','event','time','boot_id','uptime_seconds','source','pid'} <= rows[0].keys())
        self.assertIn('snapshot', rows[0])

    def test_missing_file_full_log_and_lock_failure_are_harmless(self):
        self.assertFalse(audio_log.emit('x', 'test', log_path=self.root / 'absent'))
        self.assertFalse(audio_log.emit('x', 'test', repeat=True, log_path=self.log, state_dir=self.root / 'missing'))
        self.log.write_bytes(b'x' * audio_log.MAX_BYTES)
        self.assertFalse(audio_log.emit('x', 'test', **self.options))
        self.assertEqual(self.log.stat().st_size, audio_log.MAX_BYTES)

    def test_card_change_gets_new_snapshot_and_serials_redacted(self):
        for signature in ('none','USB'):
            audio_log.emit('microphone_not_found','prepare_microphone',repeat=True,signature=signature,
                           snapshot=lambda: {'device_serial':'SECRET', 'mac':'aa:bb:cc:dd:ee:ff', 'pulse':'alsa_input.usb-SECRET.mono-fallback'},
                           **self.options)
        self.assertEqual(len(self.rows()),2)
        self.assertNotIn('SECRET',self.log.read_text())
        self.assertNotIn('aa:bb:cc:dd:ee:ff',self.log.read_text())

    def test_day_without_card_is_below_100k(self):
        for tick in range(0,86400,5):
            with patch.object(audio_log.time, 'monotonic', return_value=tick):
                audio_log.emit('microphone_not_found','prepare_microphone',repeat=True,
                               snapshot=lambda:{'cards':'none'},**self.options)
                audio_log.emit('archive_microphone_unavailable','archive_recording',repeat=True,
                               interval=86400,returncode=1,**self.options)
        self.assertLess(self.log.stat().st_size,100000)
        self.assertEqual(sum(r.get('count',0) for r in self.rows()), 17160)

    def test_rotation_reopen_retains_permissions(self):
        # Real rename/create, matching logrotate create (not a mocked write).
        audio_log.emit('before','test',**self.options)
        self.log.rename(self.root/'audio.jsonl.1')
        self.log.touch(mode=0o640)
        audio_log.emit('after','test',**self.options)
        self.assertEqual(self.log.stat().st_mode & 0o777,0o640)
        self.assertEqual(self.rows()[0]['event'],'after')

    def test_reader_rotations_boots_and_stall(self):
        common=dict(time='2026-11-16T12:00:00+03:00',boot_id='a',source='archive_recording')
        rows=[dict(common,event='archive_started',uptime_seconds=5),
              dict(common,event='heartbeat',uptime_seconds=905,segments=60,quiet_fraction=.25)]
        self.log.write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
        (self.root/'audio.jsonl.1').write_text(json.dumps(dict(common,event='startup',boot_id='b'))+'\n')
        self.assertEqual(len(load(self.log)),3)
        result=summaries(rows,True,'a',2806)[0]
        self.assertTrue(result['heartbeat_gap'])
        self.assertEqual(result['segments'],60)
        self.assertEqual(result['quiet_fraction'],.25)

    def test_audit_annotation_excludes_only_known_synthetic_events(self):
        base=dict(boot_id='a',time='2026-11-16T12:00:00+03:00',source='prepare_microphone')
        rows=[dict(base,event='microphone_not_found',pid=1),
              dict(base,event='microphone_selected',pid=2,time='2026-11-16T12:01:00+03:00'),
              dict(base,event='repeated',pid=2,of='microphone_not_found',count=10,first_time=base['time']),
              dict(base,event='repeated',pid=3,of='microphone_selected',count=2,first_time='2026-11-16T12:01:00+03:00'),
              dict(base,event='diagnostic_test_records_excluded',source='startup',
                   test_processes=[dict(boot_id='a',pid=2)],
                   test_first_times=[dict(boot_id='a',time='2026-11-16T12:01:00+03:00')])]
        self.log.write_text(''.join(json.dumps(row)+'\n' for row in rows))
        self.assertEqual(len(load(self.log,include_test_events=True)),5)
        filtered=load(self.log)
        self.assertEqual(len(filtered),3)
        # A real repeat flushed by the test process remains a real event.
        self.assertEqual([r['count'] for r in filtered if r['event']=='repeated'],[10])


class AudioLevels(unittest.TestCase):
    def test_silence_sine_fullscale_and_odd_chunks(self):
        for amplitude, expected in [(0,-120),(3276,-23.01),(32767,-3.01)]:
            data=array('h',(int(amplitude*math.sin(i*math.pi/24)) for i in range(48000))).tobytes()
            if sys.byteorder!='little':
                samples=array('h');samples.frombytes(data);samples.byteswap();data=samples.tobytes()
            meter=Levels()
            for offset in range(0,len(data),777):meter.update(data[offset:offset+777])
            self.assertAlmostEqual(meter.result()['rms_dbfs'],expected,delta=.02)
        meter=Levels();meter.update(b'\x00\x80')
        self.assertEqual(meter.result()['peak_dbfs'],0)

    def test_quiet_transitions_and_period(self):
        clock=[0]
        period=Period(interval=900,clock=lambda:clock[0])
        self.assertEqual(period.add(dict(rms_dbfs=-80,peak_dbfs=-60),15,'a'),'audio_quiet')
        self.assertIsNone(period.add(dict(rms_dbfs=-75,peak_dbfs=-55),15,'b'))
        self.assertEqual(period.add(dict(rms_dbfs=-40,peak_dbfs=-10),15,'c'),'audio_signal_present')
        self.assertIsNone(period.summary())
        clock[0]=900
        summary=period.summary()
        self.assertEqual(summary['segments'],3)
        self.assertAlmostEqual(summary['quiet_fraction'],2/3)
        self.assertEqual(summary['rms_median_dbfs'],-75)
        self.assertIsNone(period.summary(force=True))


class MicrophoneAndCapture(unittest.TestCase):
    def invoke(self,*args):
        stdout=io.StringIO()
        with patch.object(sys,'argv',['prepare_microphone.py',*args]), \
                contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(io.StringIO()):
            code=microphone.main()
        return code,stdout.getvalue()

    def test_missing_card_snapshot_and_no_stdout(self):
        with patch.object(microphone,'gain_enabled',return_value=False), \
                patch.object(microphone,'run',return_value=(1,'','no cards')), \
                patch.object(microphone.time,'sleep'),patch.object(microphone,'emit') as emit:
            self.assertEqual(self.invoke(),(1,''))
            self.assertTrue(callable(emit.call_args.kwargs['snapshot']))

    def test_selected_pcm_only_and_configured_missing(self):
        listing='card 1: USB [USB microphone], device 0: USB Audio [USB Audio]\n'
        with patch.object(microphone,'gain_enabled',return_value=False), \
                patch.object(microphone,'run',return_value=(0,listing,'')), \
                patch.object(microphone,'release_idle_pulse_source'),patch.object(microphone,'emit') as emit:
            self.assertEqual(self.invoke('--device','hw:1,0'),(0,'hw:1,0\n'))
            self.assertEqual(self.invoke('--device','hw:2,0'),(1,''))
            self.assertEqual(emit.call_args.args[0],'microphone_configured_device_missing')

    def test_archive_prepare_error_no_trace(self):
        with tempfile.TemporaryDirectory(dir='/dev/shm' if Path('/dev/shm').is_dir() else None) as folder, \
                patch.object(archive.subprocess,'check_output',side_effect=subprocess.CalledProcessError(7,['prepare'])), \
                patch.object(archive,'log') as log, patch.object(archive,'cleanup'):
            self.assertEqual(archive.record({'RECS_DIR':folder}),7)
            self.assertEqual(log.call_args.args[0],'archive_microphone_unavailable')
            self.assertEqual(log.call_args.kwargs['returncode'],7)

    def test_arecord_exit_reports_stderr_and_status(self):
        native_popen=subprocess.Popen
        def popen(args,**kwargs):
            self.assertEqual(args[0],'arecord')
            return native_popen([sys.executable,'-c',
                "import sys;sys.stderr.write('capture disconnected\\n');sys.exit(9)"],**kwargs)
        with tempfile.TemporaryDirectory(dir='/dev/shm' if Path('/dev/shm').is_dir() else None) as folder, \
                patch.object(archive.subprocess,'check_output',return_value='fake'), \
                patch.object(archive.subprocess,'Popen',side_effect=popen), \
                patch.object(archive,'log') as log, \
                patch.object(archive.Path,'home',return_value=Path(folder)), patch.object(archive,'cleanup'):
            with self.assertRaisesRegex(RuntimeError,'Microphone stopped unexpectedly'):
                archive.record({'RECS_DIR':folder})
            stopped=[c for c in log.call_args_list if c.args[0]=='archive_stopped'][-1]
            self.assertEqual(stopped.kwargs['returncode'],9)
            self.assertIn('capture disconnected',stopped.kwargs['stderr'])

    def test_real_encoder_preserves_pcm_and_emits_first_segment_and_heartbeat(self):
        import shutil
        if not shutil.which('ffmpeg'):
            self.skipTest('ffmpeg required')
        native_popen=subprocess.Popen
        native_output=subprocess.check_output
        def popen(args,**kwargs):
            if args[0]=='arecord':
                return native_popen([sys.executable,'-c',
                    "import sys;sys.stdout.buffer.write(b'\\x10\\x00'*96000)"],**kwargs)
            return native_popen(args,**kwargs)
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(archive.subprocess,'check_output',return_value='fake'), \
                patch.object(archive.subprocess,'Popen',side_effect=popen), \
                patch.object(archive,'log') as log,patch.object(archive,'emit') as emit, \
                patch.object(archive.Path,'home',return_value=Path(folder)),patch.object(archive,'cleanup'):
            (Path(folder)/'BirdNET-Pi').mkdir()
            with self.assertRaisesRegex(RuntimeError,'Microphone stopped unexpectedly'):
                archive.record({'RECS_DIR':folder,'RECORDING_LENGTH':'1','AUDIO_HEARTBEAT_SECONDS':'0'})
            completed=[c for c in log.call_args_list if c.args[0]=='archive_segment_completed']
            self.assertEqual(len(completed),2)
            self.assertEqual([c.kwargs['first_segment'] for c in completed],[True,False])
            self.assertEqual(len([c for c in emit.call_args_list if c.args[0]=='heartbeat']),2)
            files=sorted((Path(folder)/'Archive').glob('*.flac'))
            self.assertEqual(len(files),2)
            for path in files:
                decoded=native_output(['ffmpeg','-v','error','-i',str(path),'-f','s16le','pipe:1'])
                self.assertEqual(decoded,b'\x10\x00'*48000)


if __name__ == '__main__':
    unittest.main()
