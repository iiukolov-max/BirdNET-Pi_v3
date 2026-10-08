import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import subprocess

spec = importlib.util.spec_from_file_location('policy', Path(__file__).resolve().parents[1]/'scripts/birdnet_service_policy.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class ServicePolicyTest(unittest.TestCase):
    def test_deny_survives_every_mode(self):
        for row in policy.CATALOG:
            if row.get('fixed'):continue
            for unit in row['units']:
                for mode in ('normal', 'archive'):
                    self.assertFalse(policy.allowed(unit, {'OPERATION_MODE': mode, 'SERVICE_ALLOW_'+row['key']: '0'}))

    def test_mode_is_an_additional_constraint(self):
        self.assertFalse(policy.allowed('birdnet_analysis.service', {'OPERATION_MODE':'archive'}))
        self.assertFalse(policy.allowed('birdnet-archive-analysis.service', {'OPERATION_MODE':'normal'}))
        self.assertTrue(policy.allowed('birdnet_recording.service', {'OPERATION_MODE':'archive'}))

    def test_stream_and_server_share_permission(self):
        config = {'SERVICE_ALLOW_LIVE_AUDIO':'0'}
        self.assertFalse(policy.allowed('icecast2.service', config))
        self.assertFalse(policy.allowed('livestream.service', config))

    def test_reconcile_never_starts_denied_or_manual(self):
        for mode in ('normal', 'archive'):
            config = {'OPERATION_MODE':mode, 'SERVICE_ALLOW_TERMINAL':'0'}
            with patch.object(policy, 'settings', return_value=config), patch.object(policy, 'run') as calls, patch.object(policy.subprocess, 'run', return_value=subprocess.CompletedProcess([],0,'loaded\n','')):
                policy.reconcile()
                started = [unit for call in calls.call_args_list if call.args[0] == 'start' for unit in call.args[2:]]
                self.assertIn('birdnet_recording.service', started)
                self.assertNotIn('web_terminal.service', started)
                self.assertNotIn('birdnet-archive-analysis.service', started)

    def test_recording_and_analysis_cannot_be_restricted(self):
        for unit, mode, key in [('birdnet_recording.service','archive','RECORDING'), ('birdnet_analysis.service','normal','ANALYSIS'), ('birdnet-archive-analysis.service','archive','ARCHIVE_ANALYSIS')]:
            self.assertTrue(policy.allowed(unit, {'OPERATION_MODE':mode,'SERVICE_ALLOW_'+key:'0'}))

    def test_permissions_save_does_not_resume_microphone_during_manual_analysis(self):
        def result(args, **kwargs):
            return subprocess.CompletedProcess(args,0,'active\n' if 'ActiveState' in args else 'loaded\n','')
        with patch.object(policy,'settings',return_value={'OPERATION_MODE':'archive'}), patch.object(policy,'run') as calls, patch.object(policy.subprocess,'run',side_effect=result):
            policy.reconcile()
            started=[unit for call in calls.call_args_list if call.args[0]=='start' for unit in call.args[2:]]
            self.assertNotIn('birdnet_recording.service',started)
            stopped=[unit for call in calls.call_args_list if call.args[0]=='stop' for unit in call.args[1:]]
            self.assertNotIn('birdnet_recording.service',stopped)

    def test_invalid_values_are_rejected(self):
        with self.assertRaises(ValueError):policy.validate({'SERVICE_ALLOW_RECORDING':'yes'})
        with self.assertRaises(ValueError):policy.allowed('ssh.service', {})


if __name__ == '__main__':unittest.main()
