import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_model_switch import TransactionTests
import model_switch as switch
from settings_plan import FAST_KEYS,AUXILIARY
import settings_external as external


class ApplicationTests(TransactionTests):
    def test_microphone_gain_only_restarts_recording_and_not_analysis(self):
        for mode in ('normal', 'archive'):
            current=switch.replace(self.old,'OPERATION_MODE',mode)
            self.config.write_text(current)
            with patch.object(switch,'recording_service') as recording, \
                    patch.object(switch,'service') as analysis, patch.object(switch,'await_archive'):
                switch.apply(switch.replace(current,'MICROPHONE_GAIN_100','1'))
                self.assertEqual([c.args for c in recording.call_args_list],[('stop',),('start',)])
                analysis.assert_not_called()
                self.assertEqual(switch.values(self.config.read_text())['MICROPHONE_GAIN_100'],'1')

    def test_missing_gain_setting_is_off_and_unchanged_save_keeps_services(self):
        with patch.object(switch,'recording_service') as recording,patch.object(switch,'service') as analysis:
            switch.apply(switch.replace(self.old,'MICROPHONE_GAIN_100','0'))
            recording.assert_not_called();analysis.assert_not_called()
            self.assertEqual(self.config.read_text(),self.old)

    def test_invalid_microphone_gain_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Invalid microphone gain'):
            switch.apply(switch.replace(self.old,'MICROPHONE_GAIN_100','2'))
        self.assertEqual(self.config.read_text(),self.old)

    def test_inactive_archive_permission_is_saved_without_systemctl(self):
        current=switch.replace(self.old,'OPERATION_MODE','archive');self.config.write_text(current)
        with patch.object(switch,'active') as active,patch.object(switch,'enforce_services') as enforce:
            switch.apply(switch.replace(current,'SERVICE_ALLOW_TERMINAL','0'))
        active.assert_not_called();enforce.assert_not_called()

    def test_mixed_save_preserves_spelling_of_unchanged_fields(self):
        candidate=switch.replace(self.old,'CONFIDENCE','"0.6"')
        candidate=switch.replace(candidate,'SITE_NAME','"Example"')
        merged=switch.merge_changed(self.old,candidate)
        self.assertIn('CONFIDENCE=0.6\n',merged)
        self.assertIn('SITE_NAME="Example"',merged)
    def test_fast_ui_and_notification_keys_do_not_touch_services(self):
        values={'SITE_NAME':'"Example"','APPRISE_WEEKLY_REPORT':'0','APPRISE_NOTIFICATION_TITLE':'"New title"',
                'BIRDWEATHER_ID':'new-id','REMOTE_ANALYSIS_BATCH':'20'}
        for key,value in values.items():
            with self.subTest(key=key),patch.object(switch,'active') as active,patch.object(switch,'service') as service:
                switch.apply(switch.replace(self.config.read_text(),key,value))
            active.assert_not_called();service.assert_not_called()

    def test_manual_worker_resumes_after_non_backend_analysis_change(self):
        current=switch.replace(self.old,'OPERATION_MODE','archive');self.config.write_text(current)
        with patch.object(switch,'active',side_effect=lambda u:u=='birdnet-archive-analysis'),patch.object(switch,'manual_service') as manual:
            switch.apply(switch.replace(current,'CONFIDENCE','0.8'))
        self.assertEqual([call.args for call in manual.call_args_list],[('stop',),('start',)])

    def test_dependencies_match_actual_consumers(self):
        self.assertNotIn('SITE_NAME',AUXILIARY['chart_viewer'])
        self.assertNotIn('RARE_SPECIES_THRESHOLD',AUXILIARY['chart_viewer'])
        self.assertTrue({'REC_CARD','CHANNELS'}<=AUXILIARY['livestream'])
        self.assertTrue({'RAW_SPECTROGRAM','RECORDING_LENGTH'}<=AUXILIARY['spectrogram_viewer'])


class HotReloadTests(unittest.TestCase):
    def test_notification_recipient_cache_reloads_only_after_file_change(self):
        import ast,os
        from unittest.mock import MagicMock
        source=(Path(__file__).resolve().parents[1]/'scripts/utils/notifications.py').read_text()
        node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='notify')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'apprise.txt';path.write_text('first')
            api=MagicMock()
            env={'os':os,'apobj':None,'apprise_stamp':None,'APPRISE_CONFIG':str(path),'apprise':api,'userDir':folder}
            exec(compile(ast.Module(body=[node],type_ignores=[]),'notify-test','exec'),env)
            env['notify']('body','title');env['notify']('body','title')
            self.assertEqual(api.Apprise.call_count,1)
            temp=path.with_suffix('.tmp');temp.write_text('second');temp.replace(path)
            env['notify']('body','title')
            self.assertEqual(api.Apprise.call_count,2)

    def test_remote_batch_resize_does_not_skip_or_repeat_files(self):
        import ast,contextlib,io,sys,time,types,os
        from unittest.mock import MagicMock
        node=next(n for n in ast.parse((Path(__file__).resolve().parents[1]/'scripts/archive_remote.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='worker')
        with tempfile.TemporaryDirectory() as folder:
            paths=[Path(folder)/('file-'+str(n)) for n in range(12)]
            jobs=types.ModuleType('archive_analysis');jobs.BASE=Path(folder);jobs.pending=lambda:paths
            states=[];jobs.publish=lambda s:states.append(dict(s))
            helpers=types.ModuleType('utils.helpers');helpers.DB_PATH='unused'
            configs=iter([3,3,5,1,3]);helpers.get_settings=lambda:{'OPERATION_MODE':'archive','REMOTE_ANALYSIS_BATCH':str(next(configs))}
            retention=types.ModuleType('archive_retention');retention.remove_empty_source=MagicMock()
            batches=[];latest={}
            def make_batch(batch,conf):
                batches.append(list(batch));latest.clear();latest.update({p.name:(p,{},'sha') for p in batch})
                return b'body',dict(latest)
            def request(*args):return {'items':[{'member':name,'sha256':'sha','seconds':0} for name in latest]}
            env={'signal':MagicMock(),'time':time,'json':json,'os':os,'validate_backend':lambda c:('remote','192.168.0.145',3),
                 'Predictions':MagicMock(),'make_batch':make_batch,'endpoint':lambda c:'http://test',
                 'request':request,'commit':lambda *args:1}
            exec(compile(ast.Module(body=[node],type_ignores=[]),'remote-worker-test','exec'),env)
            with patch.dict(sys.modules,{'archive_analysis':jobs,'utils.helpers':helpers,'archive_retention':retention}),contextlib.redirect_stdout(io.StringIO()):
                env['worker']()
            self.assertEqual([len(batch) for batch in batches],[3,5,1,3])
            self.assertEqual([p for batch in batches for p in batch],paths)
            self.assertEqual(states[-1]['processed'],12);self.assertEqual(states[-1]['status'],'done')

    def test_hot_keys_refresh_while_model_keeps_original_value(self):
        spec=importlib.util.spec_from_file_location('hot_helpers',Path(__file__).resolve().parents[1]/'scripts/utils/helpers.py')
        helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'birdnet.conf'
            path.write_text('MODEL=old\nBIRDWEATHER_ID=one\nREMOTE_ANALYSIS_BATCH=10\n')
            before=helpers.get_settings(str(path))
            # Settings transactions replace the file atomically; avoid relying
            # on timestamp resolution for two same-size writes in one tick.
            replacement=path.with_suffix('.new')
            replacement.write_text('MODEL=new\nBIRDWEATHER_ID=two\nREMOTE_ANALYSIS_BATCH=20\n')
            replacement.replace(path)
            after=helpers.get_settings(str(path))
            self.assertIs(before,after)
            self.assertEqual(after['MODEL'],'old')
            self.assertEqual(after['BIRDWEATHER_ID'],'two')
            self.assertEqual(after['REMOTE_ANALYSIS_BATCH'],'20')
            self.assertEqual(helpers.get_settings(str(path),force_reload=True)['MODEL'],'new')


class ExternalTests(unittest.TestCase):
    def test_icecast_updates_all_passwords_and_rolls_back_on_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'icecast.xml'
            original=b'<icecast><authentication><source-password>old</source-password><relay-password>old</relay-password><admin-password>old</admin-password></authentication><port>8000</port></icecast>'
            path.write_bytes(original)
            with patch.object(external,'command'):
                external.icecast('new&value',True,path)
            self.assertIn(b'new&amp;value',path.read_bytes());self.assertIn(b'<port>8000</port>',path.read_bytes())
            path.write_bytes(original)
            with patch.object(external,'command',side_effect=[RuntimeError('failed'),b'']):
                with self.assertRaises(RuntimeError):external.icecast('new',True,path)
            self.assertEqual(path.read_bytes(),original)

    def test_caddy_preserves_routes_and_rolls_back(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'Caddyfile'
            original=b'http:// {\n basic_auth /scripts* {\n  birdnet $2old\n }\n handle /By_Date/* {\n  file_server\n }\n}\n'
            path.write_bytes(original)
            before={'CADDY_PWD':'old','BIRDNETPI_URL':''};after={'CADDY_PWD':'new','BIRDNETPI_URL':''}
            with patch.object(external,'command',side_effect=[b'$2new',b'',b'']):external.caddy(before,after,True,path)
            self.assertEqual(path.read_bytes(),original.replace(b'$2old',b'$2new'))
            path.write_bytes(original)
            with patch.object(external,'command',side_effect=[b'$2new',b'',RuntimeError('failed'),b'']):
                with self.assertRaises(RuntimeError):external.caddy(before,after,True,path)
            self.assertEqual(path.read_bytes(),original)


if __name__=='__main__':unittest.main()
