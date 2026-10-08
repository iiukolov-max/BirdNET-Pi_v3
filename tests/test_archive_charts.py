import importlib.util,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('charts',Path(__file__).resolve().parents[1]/'scripts/archive_charts.py')
charts=importlib.util.module_from_spec(spec);spec.loader.exec_module(charts)
class ChartsTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  for key,value in {'ROOT':self.root,'CONFIG':self.root/'config','LEASE':self.root/'lease','REQUEST':self.root/'request','LOCK':self.root/'lock'}.items():
   mock=patch.object(charts,key,value);mock.start();self.addCleanup(mock.stop)
  charts.CONFIG.write_text('OPERATION_MODE=archive\nSERVICE_ALLOW_CHARTS=0\nSITE_NAME=Keep\n')
  (self.root/'.archive-analysis.json').write_text(json.dumps(dict(status='done',started=123,pid=456,processed=2)))
  charts.REQUEST.write_text(json.dumps(dict(started=123,pid=456)))
 def test_permission_only_enabled_during_plot(self):
  def plot(*args,**kw):self.assertEqual(charts.values()[charts.KEY],'1')
  with patch.object(charts.subprocess,'run',side_effect=plot):charts.run()
  self.assertEqual(charts.values()[charts.KEY],'0');self.assertFalse(charts.LEASE.exists());self.assertFalse(charts.REQUEST.exists())
  self.assertEqual(charts.read(self.root/'.archive-charts.json')['status'],'done')
 def test_failure_restores_permission(self):
  with patch.object(charts.subprocess,'run',side_effect=subprocess.CalledProcessError(1,['plot'])):
   with self.assertRaises(subprocess.CalledProcessError):charts.run()
  self.assertEqual(charts.values()[charts.KEY],'0');self.assertFalse(charts.LEASE.exists())
  self.assertEqual(charts.read(self.root/'.archive-charts.json')['status'],'failed')
 def test_original_enabled_stays_enabled(self):
  charts.permission('1')
  with patch.object(charts.subprocess,'run'):charts.run()
  self.assertEqual(charts.values()[charts.KEY],'1')
 def test_boot_recovers_interrupted_permission(self):
  charts.LEASE.write_text(json.dumps({'original':'0'}));charts.permission('1')
  charts.recover()
  self.assertEqual(charts.values()[charts.KEY],'0');self.assertEqual(charts.values()['SITE_NAME'],'Keep');self.assertFalse(charts.REQUEST.exists())
 def test_reject_stale_or_interrupted_analysis(self):
  self.assertTrue(charts.eligible())
  state=charts.read(self.root/'.archive-analysis.json');state['status']='interrupted'
  (self.root/'.archive-analysis.json').write_text(json.dumps(state));self.assertFalse(charts.eligible())
  with patch.object(charts.subprocess,'run') as run:self.assertFalse(charts.request(state));run.assert_not_called()
 def test_normal_mode_does_not_schedule(self):
  charts.CONFIG.write_text('OPERATION_MODE=normal\nSERVICE_ALLOW_CHARTS=0\n')
  self.assertFalse(charts.eligible())
  with patch.object(charts.subprocess,'run') as run:self.assertFalse(charts.request(charts.read(self.root/'.archive-analysis.json')));run.assert_not_called()
 def test_no_request_does_not_run(self):
  charts.REQUEST.unlink()
  with patch.object(charts.subprocess,'run') as run:charts.run();run.assert_not_called()
if __name__=='__main__':unittest.main()
