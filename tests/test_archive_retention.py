"""Data-loss regression checks for zero-result archive retention."""
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import types
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from archive_retention import record_result, record_failure, remove_empty_source
from archive_analysis_history import rows as history_rows
import archive_remote


class ArchiveRetention(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / ('2026-11-02-birdnet-12-00-00.flac' if os.name=='nt' else '2026-11-02-birdnet-12:00:00.flac')
        self.source.write_bytes(b'original audio')
        info = self.source.stat()
        self.identity = (self.source.name, info.st_size, info.st_mtime_ns)
        self.database = self.root / 'birds.db'
        with sqlite3.connect(self.database) as db:
            db.execute('CREATE TABLE archive_processed(name TEXT,size INTEGER,mtime INTEGER,processed REAL,PRIMARY KEY(name,size,mtime))')

    def commit(self, count):
        with sqlite3.connect(self.database) as db:
            db.execute('INSERT INTO archive_processed VALUES (?,?,?,0)', self.identity)
            record_result(db, self.identity, count)

    def test_zero_result_removes_only_after_commit(self):
        self.assertEqual(remove_empty_source(self.source,self.identity,self.database),'retained_unknown')
        self.commit(0)
        self.assertEqual(remove_empty_source(self.source,self.identity,self.database),'removed')
        self.assertFalse(self.source.exists())
        self.assertEqual(remove_empty_source(self.source,self.identity,self.database),'missing')

    def test_positive_result_keeps_audio(self):
        self.commit(2)
        self.assertEqual(remove_empty_source(self.source,self.identity,self.database),'retained_detections')
        self.assertEqual(self.source.read_bytes(),b'original audio')

    def test_changed_and_symlinked_sources_are_retained(self):
        self.commit(0)
        self.source.write_bytes(b'new audio is different')
        self.assertEqual(remove_empty_source(self.source,self.identity,self.database),'retained_changed')
        other=self.root/'other.flac';other.write_bytes(b'keep me')
        self.source.unlink()
        try:self.source.symlink_to(other)
        except OSError:self.skipTest('symlinks unavailable')
        self.assertEqual(remove_empty_source(self.source,self.identity,self.database),'retained_changed')
        self.assertEqual(other.read_bytes(),b'keep me')

    def test_shared_audio_is_retained(self):
        self.commit(0)
        os.link(self.source,self.root/'detection.flac')
        self.assertEqual(remove_empty_source(self.source,self.identity,self.database),'retained_shared')

    def test_legacy_completion_is_not_zero_evidence(self):
        with sqlite3.connect(self.database) as db:
            db.execute('INSERT INTO archive_processed VALUES (?,?,?,0)',self.identity)
        self.assertEqual(remove_empty_source(self.source,self.identity,self.database),'retained_unknown')

    def test_rollback_cannot_authorize_deletion(self):
        with sqlite3.connect(self.database) as db:
            db.execute('BEGIN')
            db.execute('INSERT INTO archive_processed VALUES (?,?,?,0)',self.identity)
            record_result(db,self.identity,0)
            db.rollback()
        self.assertEqual(remove_empty_source(self.source,self.identity,self.database),'retained_unknown')

    def remote_commit(self, detections):
        from types import SimpleNamespace as Obj
        with sqlite3.connect(self.database) as db:
            db.execute('CREATE TABLE IF NOT EXISTS detections (Date,Time,Sci_Name,Com_Name,Confidence,Lat,Lon,Cutoff,Week,Sens,Overlap,File_Name)')
        helpers=types.ModuleType('utils.helpers')
        helpers.DB_PATH=str(self.database)
        helpers.get_settings=lambda:dict(LATITUDE='0',LONGITUDE='0',CONFIDENCE='.6',SENSITIVITY='1',OVERLAP='0')
        reporting=types.ModuleType('utils.reporting')
        reporting.extract_detection=lambda parsed,d:str(self.root/'saved_detection.flac')
        database=types.ModuleType('utils.database');database.connect=sqlite3.connect
        jobs=types.ModuleType('archive_analysis')
        jobs.key=lambda path:(path.name,path.stat().st_size,path.stat().st_mtime_ns)
        with patch.dict(sys.modules,{'utils.helpers':helpers,'utils.reporting':reporting,'utils.database':database,'archive_analysis':jobs}), \
             patch.object(archive_remote,'analyze_result',return_value=iter([(Obj(),detections)])):
            return archive_remote.commit(self.source,self.identity,{},None)

    def test_remote_zero_commit_is_durable_and_deletable(self):
        self.assertEqual(self.remote_commit([]),0)
        self.assertEqual(remove_empty_source(self.source,self.identity,self.database),'removed')

    def test_remote_legacy_duplicate_does_not_claim_zero(self):
        with sqlite3.connect(self.database) as db:
            db.execute('INSERT INTO archive_processed VALUES (?,?,?,0)',self.identity)
        self.assertIsNone(self.remote_commit([]))
        self.assertEqual(remove_empty_source(self.source,self.identity,self.database),'retained_unknown')

    def test_remote_transaction_failure_keeps_source(self):
        with patch('archive_retention.record_result',side_effect=sqlite3.OperationalError('disk full')):
            with self.assertRaises(sqlite3.OperationalError):self.remote_commit([])
        self.assertTrue(self.source.exists())
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM archive_processed').fetchone()[0],0)

    def test_remote_positive_result_retains_source_and_detection(self):
        detection=types.SimpleNamespace(date='2026-11-02',time='12:00:00',scientific_name='Pica pica',
            common_name='Magpie',confidence=.9,week=44)
        self.assertEqual(self.remote_commit([detection]),1)
        self.assertEqual(remove_empty_source(self.source,self.identity,self.database),'retained_detections')
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM detections').fetchone()[0],1)

    def test_history_exports_result_after_audio_removal(self):
        self.remote_commit([])
        remove_empty_source(self.source,self.identity,self.database)
        result=history_rows(self.database)
        self.assertEqual(len(result),1)
        self.assertEqual((result[0]['backend'],result[0]['outcome'],result[0]['detections']),('remote','ok',0))
        self.assertEqual(result[0]['evidence'],'live')

    def test_failure_is_recorded_without_authorizing_deletion(self):
        database=types.ModuleType('utils.database');database.connect=sqlite3.connect
        with patch.dict(sys.modules,{'utils.database':database}):
            record_failure(self.source,self.database,RuntimeError('test failure'),'remote',1.5)
        result=history_rows(self.database)[0]
        self.assertEqual((result['outcome'],result['detections'],result['error']),('error',-1,'test failure'))
        self.assertEqual(remove_empty_source(self.source,self.identity,self.database),'retained_unknown')
        self.assertTrue(self.source.exists())

    def test_old_history_schema_is_migrated(self):
        with sqlite3.connect(self.database) as db:
            db.execute('CREATE TABLE archive_analysis_results(name TEXT,size INTEGER,mtime INTEGER,detections INTEGER NOT NULL,PRIMARY KEY(name,size,mtime))')
            record_result(db,self.identity,0,backend='local',seconds=2.5)
        row=history_rows(self.database)[0]
        self.assertEqual((row['backend'],row['seconds'],row['outcome']),('local',2.5,'ok'))

    @unittest.skipIf(os.name=='nt','Local worker uses Linux fcntl')
    def test_local_worker_commits_history_before_deleting_source(self):
        import importlib.util,signal
        helpers=types.ModuleType('utils.helpers')
        helpers.BASE_PATH=str(self.root);helpers.DB_PATH=str(self.database)
        helpers.get_settings=lambda:dict(OPERATION_MODE='archive',ANALYSIS_BACKEND='local')
        failures=types.ModuleType('utils.file_failures')
        failures.InvalidRecording=ValueError;failures.failures=lambda:{}
        failures.preserve_failure=lambda *a,**k:None
        analysis=types.ModuleType('utils.analysis');analysis.load_global_model=lambda:None
        analysis.run_analysis=lambda parsed:[]
        classes=types.ModuleType('utils.classes');classes.ParseFileName=lambda name:types.SimpleNamespace(file_name=name)
        reporting=types.ModuleType('utils.reporting');reporting.extract_detection=lambda *a:None
        database=types.ModuleType('utils.database');database.connect=sqlite3.connect
        recorder=types.ModuleType('archive_recording');recorder.PATTERN=None
        capacity=types.ModuleType('recording_capacity');capacity.capacity=lambda *a:None
        modules={'utils.helpers':helpers,'utils.file_failures':failures,'utils.analysis':analysis,
                 'utils.classes':classes,'utils.reporting':reporting,'utils.database':database,
                 'archive_recording':recorder,'recording_capacity':capacity}
        spec=importlib.util.spec_from_file_location('local_history_worker',Path(__file__).resolve().parents[1]/'scripts/archive_analysis.py')
        module=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,modules),patch.object(signal,'signal'):
            spec.loader.exec_module(module)
            module.pending=lambda:[self.source]
            module.decode_archive=lambda source,wav:wav.write_bytes(b'test audio')
            module.worker()
        self.assertFalse(self.source.exists())
        row=history_rows(self.database)[0]
        self.assertEqual((row['backend'],row['outcome'],row['detections']),('local','ok',0))


if __name__ == '__main__':unittest.main()
