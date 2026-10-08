"""Boundary, persistence and audio tests using temporary data, never the live DB."""
import datetime,importlib.util,json,os,sqlite3,subprocess,sys,tempfile,unittest,shutil,stat
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from utils.classes import ParseFileName,Detection
from utils.file_failures import InvalidRecording
from utils import file_failures,helpers,reporting
from utils.database import retry_transaction
import normal_cleanup,prepare_microphone
import reidentify
import install_sqlite_runtime
from sqlite_backup import backup as sqlite_backup

SCHEMA='CREATE TABLE detections (Date TEXT,Time TEXT,Sci_Name TEXT,Com_Name TEXT,Confidence FLOAT,Lat FLOAT,Lon FLOAT,Cutoff FLOAT,Week TEXT,Sens FLOAT,Overlap FLOAT,File_Name TEXT)'
class Integration(unittest.TestCase):
 def test_filenames(self):
    self.assertEqual(ParseFileName('2026-10-08-birdnet-RTSP_1-23:59:58.wav').RTSP_id,'RTSP_1-')
    for name in ['foreign.wav','2026-13-08-birdnet-23:59:58.wav','2026-10-08-birdnet-99:59:58.wav']:
      with self.assertRaises(InvalidRecording):ParseFileName(name)
 def test_midnight(self):
    d=Detection(datetime.datetime(2026,10,8,23,59,58),3,6,'Species','Animal',.8)
    self.assertEqual((d.date,d.time),('2026-10-09','00:00:01'))
 def test_corrupt_audio_is_not_empty_success(self):
    from utils.analysis import readAudioData
    with tempfile.TemporaryDirectory() as folder:
      p=Path(folder)/'broken.wav';p.write_bytes(b'not audio')
      with self.assertRaises(InvalidRecording):readAudioData(str(p),0,32000,3)
 def test_memory_error_is_not_corruption(self):
    from utils.analysis import readAudioData
    with patch('utils.analysis.sf.read',side_effect=MemoryError('test')):
      with self.assertRaises(MemoryError):readAudioData('unused',0,32000,3)
 def test_silent_audio_is_valid(self):
    import numpy as np,soundfile as sf
    from utils.analysis import readAudioData
    with tempfile.TemporaryDirectory() as folder:
      p=Path(folder)/'silent.wav';sf.write(p,np.zeros(96000,dtype=np.float32),32000)
      self.assertEqual(len(readAudioData(str(p),0,32000,3)),1)
 def test_quarantine_preserves_original_bytes(self):
    with tempfile.TemporaryDirectory() as folder:
      p=Path(folder)/'foreign.wav';p.write_bytes(b'bad-data');ledger=Path(folder)/'ledger.json'
      with patch.object(file_failures,'ledger_path',return_value=ledger),patch.object(helpers,'get_settings',return_value={'RECS_DIR':folder}):
        row=file_failures.preserve_failure(p,InvalidRecording('bad name'),True)
        self.assertFalse(p.exists());self.assertEqual(Path(row['retained']).read_bytes(),b'bad-data')
        self.assertTrue(row['quarantined'])
 def test_transient_failure_retained_until_changed(self):
    with tempfile.TemporaryDirectory() as folder:
      p=Path(folder)/'good.wav';p.write_bytes(b'a');ledger=Path(folder)/'ledger.json'
      with patch.object(file_failures,'ledger_path',return_value=ledger):
        file_failures.preserve_failure(p,MemoryError('test'))
        self.assertTrue(p.exists());self.assertTrue(file_failures.blocked(p));p.write_bytes(b'changed')
        self.assertFalse(file_failures.blocked(p))
 def test_batch_commit_once_and_idempotent(self):
    with tempfile.TemporaryDirectory() as folder:
      db=Path(folder)/'db';p=Path(folder)/'2026-10-08-birdnet-23:59:58.wav';p.write_bytes(b'a')
      with closing(sqlite3.connect(db)) as con:con.execute(SCHEMA)
      conf=dict(LATITUDE='1',LONGITUDE='2',CONFIDENCE='.6',SENSITIVITY='1',OVERLAP='0')
      detections=[Detection(datetime.datetime(2026,10,8),i,i+3,'Species','Animal',.8) for i in [0,3]]
      for i,d in enumerate(detections):d.file_name_extr=f'clip{i}.flac'
      with patch.object(reporting,'DB_PATH',str(db)),patch.object(reporting,'get_settings',return_value=conf):
        self.assertTrue(reporting.write_detections_to_db(ParseFileName(str(p)),detections))
        self.assertFalse(reporting.write_detections_to_db(ParseFileName(str(p)),detections))
      with closing(sqlite3.connect(db)) as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM detections').fetchone()[0],2)
 def test_failed_transaction_rolls_back_and_raises(self):
    with tempfile.TemporaryDirectory() as folder:
      db=Path(folder)/'db'
      with closing(sqlite3.connect(db)) as con:con.execute('CREATE TABLE t(x INTEGER)')
      def operation(con):con.execute('INSERT INTO t VALUES (1)');raise ValueError('test failure')
      with self.assertRaises(ValueError):retry_transaction(db,operation)
      with closing(sqlite3.connect(db)) as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM t').fetchone()[0],0)
 def test_wal_reader_writer_and_backup(self):
    with tempfile.TemporaryDirectory() as folder:
      db=Path(folder)/'db';backup=Path(folder)/'before.db'
      with closing(sqlite3.connect(db)) as con:con.execute('CREATE TABLE t(x INTEGER)')
      subprocess.run([sys.executable,str(ROOT/'scripts/migrate_sqlite_wal.py'),str(db),str(backup)],check=True,capture_output=True)
      reader=sqlite3.connect(db);writer=sqlite3.connect(db)
      try:
        reader.execute('BEGIN');self.assertEqual(reader.execute('SELECT COUNT(*) FROM t').fetchone()[0],0)
        writer.execute('INSERT INTO t VALUES (1)');writer.commit()
        self.assertEqual(reader.execute('SELECT COUNT(*) FROM t').fetchone()[0],0);reader.commit()
        restored=sqlite3.connect(Path(folder)/'copy.db');writer.backup(restored)
        self.assertEqual(restored.execute('SELECT COUNT(*) FROM t').fetchone()[0],1);restored.close()
      finally:reader.close();writer.close()
 def test_cleanup_protection_symlink_and_recheck(self):
    with tempfile.TemporaryDirectory() as folder:
      base=Path(folder)/'By_Date';species=base/'2026-10-08'/'Animal';species.mkdir(parents=True)
      for name in ['a.flac','a.flac.png','b.flac','b.flac.png','c.flac.partial']: (species/name).write_bytes(b'data')
      outside=Path(folder)/'outside';outside.write_bytes(b'keep');(species/'link.flac').symlink_to(outside)
      protected={'2026-10-08/Animal/a.flac','2026-10-08/Animal/a.flac.png'}
      checks=[]
      def usage(_):
        checks.append(1);return SimpleNamespace(total=1000,free=10 if (species/'b.flac').exists() else 100)
      result=normal_cleanup.cleanup(base,protected,95,usage=usage)
      self.assertEqual(result['deleted'],1);self.assertFalse(result['full']);self.assertGreaterEqual(len(checks),2)
      self.assertTrue((species/'a.flac').exists());self.assertTrue(outside.exists());self.assertTrue((species/'c.flac.partial').exists())
 def test_backup_restore_includes_wal_and_reviews(self):
    with tempfile.TemporaryDirectory() as folder:
      db=Path(folder)/'db';saved=Path(folder)/'saved.db';restored=Path(folder)/'restored.db'
      con=sqlite3.connect(db)
      try:
        con.execute('PRAGMA journal_mode=WAL');con.execute('CREATE TABLE detection_reviews(file_path TEXT,review_status TEXT)')
        con.execute("INSERT INTO detection_reviews VALUES ('a','correct')");con.commit()
        sqlite_backup(db,saved);sqlite_backup(saved,restored)
        with closing(sqlite3.connect(restored)) as copy:self.assertEqual(copy.execute('SELECT review_status FROM detection_reviews').fetchone()[0],'correct')
      finally:con.close()
 def test_cleanup_dry_run_keeps_files(self):
    with tempfile.TemporaryDirectory() as folder:
      base=Path(folder)/'By_Date';species=base/'2026-10-08'/'Animal';species.mkdir(parents=True);p=species/'a.flac';p.write_bytes(b'a')
      result=normal_cleanup.cleanup(base,set(),usage=lambda _:SimpleNamespace(total=100,free=1),dry_run=True)
      self.assertEqual(result['deleted'],0);self.assertTrue(p.exists())
 def test_audio_backend_selection(self):
    for device in ['','default','auto','pulse','pulse:foo']:self.assertTrue(prepare_microphone.needs_pulse(device))
    for device in ['hw:1,0','plughw:CARD=Device,DEV=0','dsnoop:Device','custom']:self.assertFalse(prepare_microphone.needs_pulse(device))
 def test_reidentify_binds_apostrophes_and_moves_review(self):
    with tempfile.TemporaryDirectory() as folder:
      root=Path(folder);base=root/'By_Date';oldfolder=base/'2026-10-08'/'Old';oldfolder.mkdir(parents=True)
      name='Old-80-2026-10-08-birdnet-12:00:00.flac';(oldfolder/name).write_bytes(b'a')
      labels=root/'labels';labels.write_text("Species_O'Brien\n")
      db=root/'db'
      with closing(sqlite3.connect(db)) as con:
        con.execute(SCHEMA);con.execute('CREATE TABLE detection_reviews(file_path TEXT PRIMARY KEY,review_status TEXT)')
        con.execute('INSERT INTO detections VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',('2026-10-08','12:00:00','OldSpecies','Old',.8,0,0,.6,'41',1,0,name))
        con.execute('INSERT INTO detection_reviews VALUES (?,?)',(f'2026-10-08/Old/{name}','correct'));con.commit()
      newname=reidentify.reidentify(db,base,labels,name,"Species_O'Brien")
      self.assertEqual((base/'2026-10-08'/'OBrien'/newname).read_bytes(),b'a')
      with closing(sqlite3.connect(db)) as con:
        self.assertEqual(con.execute('SELECT Com_Name FROM detections').fetchone()[0],"O'Brien")
        self.assertEqual(con.execute('SELECT review_status FROM detection_reviews WHERE file_path=?',(f'2026-10-08/OBrien/{newname}',)).fetchone()[0],'correct')
 def test_direct_does_not_interrupt_active_pulse_capture(self):
    sources=json.dumps([{'name':'source','index':2,'properties':{'alsa.card':'1'}}])
    clients=json.dumps([{'source':2}])
    with patch.object(prepare_microphone,'run',side_effect=[(0,sources,''),(0,clients,'')]) as run:
      with self.assertRaises(RuntimeError):prepare_microphone.release_idle_pulse_source({'number':1})
      self.assertEqual(run.call_count,2)
 def test_config_roundtrip_php_python_shell(self):
    values={'SITE_NAME':'Станция "лес" \\ $HOME ${PATH} $(printf injected) `printf injected` O\'Brien','EMPTY':''}
    code="require $argv[1];$values=json_decode($argv[2],true);echo birdnet_config_update('', $values);"
    text=subprocess.check_output(['php','-r',code,str(ROOT/'scripts/web_safety.php'),json.dumps(values)],text=True)
    conf=helpers.PHPConfigParser(interpolation=None);conf.optionxform=lambda x:x;conf.read_string('[top]\n'+text)
    self.assertEqual(dict(conf['top']),values)
    with tempfile.TemporaryDirectory() as folder:
      p=Path(folder)/'config';p.write_text(text)
      out=subprocess.check_output(['bash','-c','source "$1"; printf "%s" "$SITE_NAME"','test',str(p)],text=True)
      self.assertEqual(out,values['SITE_NAME'])
    parsed=subprocess.check_output(['php','-r',"require $argv[1];echo json_encode(birdnet_config_parse($argv[2]));",str(ROOT/'scripts/web_safety.php'),text],text=True)
    self.assertEqual(json.loads(parsed),values)

 def test_paths_reject_sibling_and_symlink_escape(self):
    with tempfile.TemporaryDirectory() as folder:
      base=Path(folder)/'base';base.mkdir();inside=base/'clip.flac';inside.write_bytes(b'a')
      sibling=Path(folder)/'base-sibling';sibling.mkdir();outside=sibling/'clip.flac';outside.write_bytes(b'b')
      (base/'escape.flac').symlink_to(outside)
      code="require $argv[1];foreach(array_slice($argv,3) as $p){try{birdnet_path_inside($argv[2],$p);echo 'ok\\n';}catch(Throwable $e){echo 'rejected\\n';}}"
      out=subprocess.check_output(['php','-r',code,str(ROOT/'scripts/web_safety.php'),str(base),str(inside),str(outside),str(base/'escape.flac')],text=True)
      self.assertEqual(out,'ok\\nrejected\\nrejected\\n')
 def test_php_sql_binds_quotes_without_changing_query(self):
    code=r'''$source=file_get_contents($argv[1]);$start=strpos($source,'function fetch_species_array(');$end=strpos($source,'function get_summary(',$start);
    function get_db(){return $GLOBALS['test_db'];} function ensure_db_ok($stmt){if(!$stmt)throw new Exception('bad query');}
    eval(substr($source,$start,$end-$start));$GLOBALS['test_db']=new SQLite3(':memory:');$db=$GLOBALS['test_db'];
    $db->exec('CREATE TABLE detections(Date TEXT,Time TEXT,File_Name TEXT,Com_Name TEXT,Sci_Name TEXT,Confidence REAL)');
    $db->exec("INSERT INTO detections VALUES ('2026-10-08','12:00:00','a.flac','Animal','Species',.8)");
    $bad='" OR 1=1 --';$results=[fetch_species_array('date',$bad)->fetchArray(),fetch_best_detection($bad)->fetchArray(SQLITE3_ASSOC),fetch_all_detections($bad,'confidence')->fetchArray()];
    echo json_encode([$results[0]===false,$results[1]['COUNT(*)']==0,$results[2]===false]);'''
    out=subprocess.check_output(['php','-r',code,str(ROOT/'scripts/common.php')],text=True)
    self.assertEqual(json.loads(out),[True,True,True])

 def test_sqlite_install_upgrade_preserves_data_and_shared_group(self):
    with tempfile.TemporaryDirectory() as folder:
      app=Path(folder)/'installation';(app/'scripts').mkdir(parents=True)
      shutil.copyfile(ROOT/'scripts/migrate_sqlite_wal.py',app/'scripts/migrate_sqlite_wal.py')
      db=app/'scripts/birds.db'
      with closing(sqlite3.connect(db)) as con:
        con.execute('CREATE TABLE preserved(value)');con.execute("INSERT INTO preserved VALUES ('review')");con.commit()
      os.chmod(db,0o640);install_sqlite_runtime.install(app)
      self.assertTrue((app/'scripts').stat().st_mode&stat.S_ISGID)
      self.assertTrue(db.stat().st_mode&stat.S_IWGRP)
      with closing(sqlite3.connect(db)) as con:
        self.assertEqual(con.execute('PRAGMA journal_mode').fetchone()[0],'wal')
        self.assertEqual(con.execute('SELECT value FROM preserved').fetchone()[0],'review')
      backup=list((Path(folder)/'birdnet-backups').glob('sqlite-*/birds.db'));self.assertEqual(len(backup),1)
      with closing(sqlite3.connect(backup[0])) as con:self.assertEqual(con.execute('SELECT value FROM preserved').fetchone()[0],'review')
 def test_chart_survives_midnight_without_future_chart(self):
    with tempfile.TemporaryDirectory() as folder:
      base=Path(folder)
      for name in ['Combo-2026-10-07.png','Combo-2026-10-08.png','Combo-2026-10-10.png']:(base/name).write_bytes(b'test')
      code="require $argv[1];echo overview_chart_file($argv[2],$argv[3]);"
      args=['php','-r',code,str(ROOT/'scripts/overview_chart.php'),str(base)]
      self.assertEqual(subprocess.check_output(args+['2026-10-09'],text=True),'Combo-2026-10-08.png')
      self.assertEqual(subprocess.check_output(args+['2026-10-07'],text=True),'Combo-2026-10-07.png')
      self.assertEqual(subprocess.check_output(args+['2026-10-06'],text=True),'')

if __name__=='__main__':unittest.main()
