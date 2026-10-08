import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('cpu_policy',Path(__file__).resolve().parents[1]/'scripts/economy_cpu_policy.py')
policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)

class CpuPolicyTest(unittest.TestCase):
    def test_normal_is_not_limited_by_archive_policy(self):
        self.assertEqual(policy.choose_profile('normal','active','active'),'normal')
    def test_analysis_wins_during_start_transition(self):
        self.assertEqual(policy.choose_profile('archive','activating','active'),'analysis')
    def test_recording_and_idle(self):
        self.assertEqual(policy.choose_profile('archive','inactive','active'),'recording')
        self.assertEqual(policy.choose_profile('archive','failed','inactive'),'idle')
    def test_hot_steps_down_and_resets_cool_timer(self):
        self.assertEqual(policy.thermal_limit([600,700,800],800,78,False,14),(700,0))
    def test_current_firmware_limit_steps_down(self):
        self.assertEqual(policy.thermal_limit([600,700,800],800,73,True,14),(700,0))
    def test_cooling_requires_thirty_seconds(self):
        cap,ticks=700,0
        for _ in range(14):cap,ticks=policy.thermal_limit([600,700,800],cap,74,False,ticks)
        self.assertEqual(cap,700)
        self.assertEqual(policy.thermal_limit([600,700,800],cap,74,False,ticks),(800,0))
    def test_temperature_hysteresis(self):
        self.assertEqual(policy.thermal_limit([600,700,800],700,76,False,10),(700,0))
    def test_hardware_bounds(self):
        self.assertEqual(policy.thermal_limit([600,700],600,85,True,0),(600,0))
        self.assertEqual(policy.thermal_limit([600,700],700,70,False,14),(700,0))
if __name__=='__main__':unittest.main()
