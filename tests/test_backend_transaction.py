"""Linux: backend switches preserve config on failure and resume running jobs."""
import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import model_switch as switch

class BackendTransactionTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  root=Path(self.temp.name);(root/'model').mkdir()
  (root/'model'/(switch.V3+'.tflite')).write_bytes(b'0'*1000001)
  self.config=root/'birdnet.conf';self.state=root/'profiles.json'
  self.old='MODEL='+switch.V3+'\nGEO_MODEL=off\nSENSITIVITY=1.0\nPRIVACY_THRESHOLD=0\nCONFIDENCE=0.6\nOPERATION_MODE=archive\nRECORDING_LENGTH=30\nANALYSIS_BACKEND=local\nREMOTE_ANALYSIS_IP=192.168.0.145\nREMOTE_ANALYSIS_BATCH=10\n'
  self.config.write_text(self.old);self.actions=[]
  for name,value in [('BASE',root),('CONFIG',self.config),('STATE',self.state),('PAUSE_MARKER',root/'pause'),
    ('atomic',lambda path,text:path.write_text(text)),('active',lambda unit:unit=='birdnet-archive-analysis'),
    ('manual_service',lambda action:self.actions.append(action)),('labels',lambda:None)]:
   p=patch.object(switch,name,value);p.start();self.addCleanup(p.stop)
 def test_remote_probe_failure_preserves_running_local(self):
  with patch.object(switch.analysis_backend,'endpoint',side_effect=OSError('offline')):
   with self.assertRaises(OSError):switch.apply(switch.replace(self.old,'ANALYSIS_BACKEND','remote'))
  self.assertEqual(self.config.read_text(),self.old);self.assertEqual(self.actions,[])
 def test_local_remote_local_resumes_active_archive(self):
  with patch.object(switch.analysis_backend,'endpoint',return_value='http://192.168.0.145:8766') as probe:
   switch.apply(switch.replace(self.old,'ANALYSIS_BACKEND','remote'))
   self.assertEqual(self.actions,['stop','start']);probe.assert_called_once()
  self.actions=[]
  with patch.object(switch.analysis_backend,'endpoint',side_effect=AssertionError('Local mode must not contact PC')):
   switch.apply(switch.replace(self.config.read_text(),'ANALYSIS_BACKEND','local'))
  self.assertEqual(self.actions,['stop','start']);self.assertEqual(self.config.read_text(),self.old)
 def test_invalid_ip_does_not_stop_current_job(self):
  candidate=switch.replace(switch.replace(self.old,'ANALYSIS_BACKEND','remote'),'REMOTE_ANALYSIS_IP','8.8.8.8')
  with self.assertRaises(ValueError):switch.apply(candidate)
  self.assertEqual(self.actions,[]);self.assertEqual(self.config.read_text(),self.old)

if __name__=='__main__':unittest.main()
