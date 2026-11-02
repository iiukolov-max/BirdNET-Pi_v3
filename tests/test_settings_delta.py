import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import unittest
from unittest.mock import patch
from test_model_switch import TransactionTests
import model_switch as switch
import birdnet_service_policy as policy


class DeltaTests(TransactionTests):
    def test_disk_limit_does_not_touch_capture_or_analysis(self):
        with patch.object(switch,'active') as active, patch.object(switch,'await_archive') as ready, patch.object(switch,'recording_service') as recording:
            switch.apply(switch.replace(self.old,'ARCHIVE_MAX_USED_PERCENT','90'))
        active.assert_not_called();ready.assert_not_called();recording.assert_not_called()
        self.assertEqual(switch.values(self.config.read_text())['ARCHIVE_MAX_USED_PERCENT'],'90')

    def test_cleanup_limit_reloads_and_ignores_invalid_value(self):
        from archive_recording import cleanup_limit
        self.config.write_text('ARCHIVE_MAX_USED_PERCENT=90\n')
        self.assertEqual(cleanup_limit(85,self.config),90)
        self.config.write_text('ARCHIVE_MAX_USED_PERCENT="80"\n')
        self.assertEqual(cleanup_limit(90,self.config),80)
        self.config.write_text('ARCHIVE_MAX_USED_PERCENT=2\n')
        self.assertEqual(cleanup_limit(80,self.config),80)

    def test_identical_settings_touch_nothing(self):
        with patch.object(switch,'active') as active, patch.object(switch,'atomic') as atomic:
            switch.apply(self.old)
        active.assert_not_called();atomic.assert_not_called()

    def test_quotes_and_default_permissions_are_not_changes(self):
        candidate=switch.replace(self.old,'CONFIDENCE','"0.6"')
        candidate=switch.replace(candidate,'SERVICE_ALLOW_TERMINAL','1')
        with patch.object(switch,'active') as active, patch.object(switch,'atomic') as atomic:
            switch.apply(candidate)
        active.assert_not_called();atomic.assert_not_called()

    def test_only_selected_permission_is_reconciled(self):
        with patch.object(switch,'enforce_services') as enforce, patch.object(switch,'active') as active:
            switch.apply(switch.replace(self.old,'SERVICE_ALLOW_TERMINAL','0'))
        enforce.assert_called_once_with({'SERVICE_ALLOW_TERMINAL'})
        active.assert_not_called()

    def test_display_setting_keeps_all_services_untouched(self):
        with patch.object(switch,'active') as active, patch.object(switch,'enforce_services') as enforce:
            switch.apply(switch.replace(self.old,'SITE_NAME','"New station"'))
        active.assert_not_called();enforce.assert_not_called()

    def test_policy_only_queries_selected_unit(self):
        from types import SimpleNamespace
        commands=[]
        def run(args,**kwargs):
            commands.append(args)
            return SimpleNamespace(stdout='loaded' if 'LoadState' in args else 'disabled',returncode=0)
        with patch.object(policy,'settings',return_value={'OPERATION_MODE':'normal','SERVICE_ALLOW_TERMINAL':'0'}), patch.object(policy.subprocess,'run',side_effect=run):
            policy.reconcile({'SERVICE_ALLOW_TERMINAL'})
        units={arg for command in commands for arg in command if arg.endswith('.service')}
        self.assertEqual(units,{'web_terminal.service'})


if __name__=='__main__':unittest.main()
