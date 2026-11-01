import sys,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analysis_backend as backend

class BackendTest(unittest.TestCase):
 def setUp(self):
  backend._endpoints.clear()
  self.config={'MODEL':backend.V3,'ANALYSIS_BACKEND':'remote','REMOTE_ANALYSIS_IP':'192.168.0.145','REMOTE_ANALYSIS_BATCH':'10'}
 def test_missing_setting_defaults_local(self):self.assertEqual(backend.validate({})[0],'local')
 def test_invalid_selection_does_not_probe(self):
  for field,value in [('ANALYSIS_BACKEND','shell'),('REMOTE_ANALYSIS_BATCH','0'),('REMOTE_ANALYSIS_BATCH','101'),('REMOTE_ANALYSIS_IP','example.com'),('REMOTE_ANALYSIS_IP','8.8.8.8'),('MODEL','legacy')]:
   candidate=dict(self.config);candidate[field]=value
   with self.subTest(field=field,value=value),patch.object(backend,'health') as health:
    with self.assertRaises(ValueError):backend.validate(candidate,check=True)
    health.assert_not_called()
 def test_direct_lan_selected_and_cached(self):
  with patch.object(backend,'health',return_value={'ready':True}) as health:
   self.assertEqual(backend.endpoint(self.config),'http://192.168.0.145:8766')
   self.assertEqual(backend.endpoint(self.config),'http://192.168.0.145:8766')
   health.assert_called_once()
 def test_ssh_fallback_matches_configured_computer(self):
  with patch.object(backend,'health',side_effect=[OSError('blocked'),{'addresses':['192.168.0.145']}]) as health:
   self.assertEqual(backend.endpoint(self.config),'http://127.0.0.1:8766')
 def test_other_tunnel_computer_rejected(self):
  with patch.object(backend,'health',side_effect=[OSError('blocked'),{'addresses':['192.168.0.146']}]):
   with self.assertRaises(OSError):backend.endpoint(self.config)
 def test_forget_rechecks_service(self):
  with patch.object(backend,'health',return_value={}) as health:
   backend.endpoint(self.config);backend.forget(self.config);backend.endpoint(self.config)
   self.assertEqual(health.call_count,2)

if __name__=='__main__':unittest.main()
