"""Batch offload; Pi retains filtering, clips and atomic database completion."""
import argparse
import collections
from contextlib import closing
import hashlib
import http.client
import io
import json
import math
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import urllib.parse
import zipfile
import ipaddress
from analysis_backend import endpoint,forget,validate as validate_backend

MODEL_SHA='f4af6290690e0031cd785d4c810167af83467ce1426f4eba249ca994681000db'
LABELS_SHA='8124b0ea2d187104c5e2cd95a0f937165647e20349c8fd34d4d5ef991821f8f0'

class RemoteAnalysisStopped(InterruptedError):pass


def request(url, body=None):
    # Reverse SSH forwarding exposes the PC only on the Pi's loopback interface.
    endpoint=urllib.parse.urlsplit(url)
    address=ipaddress.ip_address(endpoint.hostname or '')
    if endpoint.scheme!='http' or address.version!=4 or not (address.is_loopback or address.is_private) or endpoint.port!=8766 or endpoint.username or endpoint.password or endpoint.path not in ('','/') or endpoint.query or endpoint.fragment:
        raise ValueError('Invalid remote analysis endpoint')
    req=urllib.request.Request(url+('/v1/analyze' if body is not None else '/health'), data=body,
                               headers={'Content-Type':'application/zip'} if body is not None else {})
    with urllib.request.urlopen(req,timeout=600) as response:
        result=json.load(response)
    if result.get('model_sha256')!=MODEL_SHA or result.get('labels_sha256')!=LABELS_SHA:
        raise ValueError('Remote model or taxonomy mismatch')
    return result


def make_batch(paths, conf):
    import archive_analysis as jobs
    manifest={'schema':1,'model_sha256':MODEL_SHA,'labels_sha256':LABELS_SHA,
              'overlap':conf.getfloat('OVERLAP'),
              'top_k':max(10,int(6000*conf.getfloat('PRIVACY_THRESHOLD')/100.)), 'items':[]}
    buffer=io.BytesIO();identities={}
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_STORED) as archive:
        for i,path in enumerate(paths):
            try:
                with path.open('rb') as source:
                    info=os.fstat(source.fileno());data=source.read(16*1024**2+1)
                if len(data)!=info.st_size or len(data)>16*1024**2:raise ValueError('Recording exceeds transfer limit')
                key=(path.name,info.st_size,info.st_mtime_ns)
                if jobs.key(path)!=key:continue
            except FileNotFoundError:continue
            member=f'{i:04d}.audio';sha=hashlib.sha256(data).hexdigest()
            archive.writestr(member,data)
            manifest['items'].append({'member':member,'sha256':sha,'size':len(data)})
            identities[member]=(path,key,sha)
        archive.writestr('manifest.json',json.dumps(manifest))
    return buffer.getvalue(),identities


class Predictions:
    sample_rate=32000
    chunk_duration=3
    def __init__(self,conf):
        from utils.helpers import get_model_labels
        from utils.models import get_geo_v3_labels,GEO_CACHE_WORKER
        if conf['MODEL']!='BirdNET+_V3.0-preview3.1_Global_11K_FP16_pruned':
            raise ValueError('Remote worker currently supports V3 Preview 3.1 only')
        mode=conf.get('GEO_MODEL','v3.0.4' if Path('/etc/birdnet/geomodel-v3.enabled').is_file() else 'legacy')
        if mode not in ('v3.0.4','off','legacy'):raise ValueError('Unknown geographic mode')
        self._geomodel_v3=mode=='v3.0.4';self.off=mode=='off'
        self.labels=get_model_labels(conf['MODEL'])
        self.geo_labels=get_geo_v3_labels() if self._geomodel_v3 else get_model_labels('BirdNET_GLOBAL_6K_V2.4_Model_FP16')
        self.unknown=set(self.labels)-set(self.geo_labels)
        self.position=(conf.getfloat('LATITUDE'),conf.getfloat('LONGITUDE'))
        self.cache={}
        if not self.off:
            query={'lat':self.position[0],'lon':self.position[1],'version':conf.getint('DATA_MODEL_VERSION'),
                   'geo_v3':self._geomodel_v3,'threshold':conf.getfloat('SF_THRESH')}
            run=subprocess.run([sys.executable,GEO_CACHE_WORKER],input=json.dumps(query),capture_output=True,text=True,check=True,timeout=180)
            self.cache=json.loads(run.stdout)
        self.rows=collections.deque()
        self.conf=conf
        self.skip_transfer=False

    def prepare_file(self,path):
        if self.skip_transfer:
            self.skip_transfer=False
            return
        self.rows.clear()
        body,identities=make_batch([Path(path)],self.conf)
        if len(identities)!=1:raise ValueError('Source changed during transfer')
        while True:
            if getattr(sys.modules.get('__main__'),'shutdown',False):raise RemoteAnalysisStopped('Analysis stopped')
            try:
                response=request(endpoint(self.conf),body);break
            except urllib.error.HTTPError as error:
                if error.code<500:raise RuntimeError('PC rejected recording') from error
                forget(self.conf);time.sleep(5)
            except InterruptedError:raise
            except (OSError,http.client.HTTPException):forget(self.conf);time.sleep(5)
        results=response.get('items',[])
        identity=next(iter(identities.values()))
        if len(results)!=1 or results[0]['sha256']!=identity[2] or results[0].get('error'):raise ValueError('Invalid remote recording result')
        self.feed(results[0])

    def set_meta_data(self,lat,lon,week):
        if (lat,lon)!=self.position:raise ValueError('Position changed; restart analysis')
        self.week=str(week)

    def get_species_list(self):
        if self.off:return []
        return list({self.geo_labels[i] for i in self.cache[self.week]}|self.unknown)

    def predict_top(self,chunk,count):
        if not self.rows:raise ValueError('Remote response contains too few audio windows')
        row=self.rows.popleft()
        if len(row)!=count:raise ValueError('Remote top-k mismatch')
        for name,value in row:
            if name not in self.label_set or not isinstance(value,(float,int)) or not math.isfinite(value) or not 0<=value<=1:
                raise ValueError('Invalid remote prediction')
        return row

    def feed(self,result,skip_transfer=False):
        self.label_set=set(self.labels)
        self.rows=collections.deque(result['predictions'])
        self.skip_transfer=skip_transfer


def analyze_result(path,result,proxy):
    import archive_analysis as jobs
    from utils import analysis
    from utils.classes import ParseFileName
    with tempfile.TemporaryDirectory(prefix='birdnet-remote-') as folder:
        wav=Path(folder)/(path.stem+'.wav')
        with path.open('rb') as source:jobs.decode_archive(source,wav)
        proxy.feed(result,skip_transfer=True);analysis.MODEL=proxy
        parsed=ParseFileName(str(wav));parsed.original_recording=str(path)
        detections=analysis.run_analysis(parsed)
        if proxy.rows:raise ValueError('Remote response contains too many audio windows')
        yield parsed,detections


def commit(path,identity,result,proxy):
    import archive_analysis as jobs
    from utils.reporting import extract_detection
    from utils.helpers import get_settings,DB_PATH
    from utils.database import connect
    from archive_retention import record_result
    if jobs.key(path)!=identity:raise ValueError('Source changed after transfer; not committing')
    conf=get_settings()
    with closing(connect(DB_PATH,timeout=30)) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS archive_processed (name TEXT,size INTEGER,mtime INTEGER,processed REAL,PRIMARY KEY(name,size,mtime))')
        # A legacy completion does not prove that this recording had no detections.
        if db.execute('SELECT 1 FROM archive_processed WHERE name=? AND size=? AND mtime=?',identity).fetchone():return None
    for parsed,detections in analyze_result(path,result,proxy):
        for detection in detections:detection.file_name_extr=extract_detection(parsed,detection)
        if jobs.key(path)!=identity:raise ValueError('Source changed during filtering; not committing')
        with closing(connect(DB_PATH,timeout=30)) as db:
            with db:
                if not db.execute('SELECT 1 FROM archive_processed WHERE name=? AND size=? AND mtime=?',identity).fetchone():
                    db.executemany('INSERT INTO detections (Date,Time,Sci_Name,Com_Name,Confidence,Lat,Lon,Cutoff,Week,Sens,Overlap,File_Name) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                        [(d.date,d.time,d.scientific_name,d.common_name,d.confidence,conf['LATITUDE'],conf['LONGITUDE'],conf['CONFIDENCE'],str(d.week),conf['SENSITIVITY'],conf['OVERLAP'],os.path.basename(d.file_name_extr)) for d in detections])
                    db.execute('INSERT INTO archive_processed VALUES (?,?,?,?)',(*identity,time.time()))
                    record_result(db,identity,len(detections),backend='remote',seconds=result.get('seconds'))
        return len(detections)


def worker():
    import fcntl
    import archive_analysis as jobs
    from utils.helpers import get_settings
    conf=get_settings()
    if conf.get('OPERATION_MODE')!='archive':raise ValueError('Archive mode required')
    _,computer_ip,batch_size=validate_backend(conf)
    def interrupted(*args):raise InterruptedError('Remote analysis stopped')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    lock=(jobs.BASE/'.analysis-instance.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    queue=jobs.pending()
    state={'status':'loading','backend':'pc','computer_ip':computer_ip,'batch_size':batch_size,'pid':os.getpid(),'started':time.time(),
           'processed':0,'failed':0,'missing':0,'total':len(queue),'processing_seconds':0}
    jobs.publish(state)
    try:
        proxy=Predictions(conf)
        offset=0
        while offset<len(queue):
            conf=get_settings()
            batch_size=int(conf.get('REMOTE_ANALYSIS_BATCH','10'))
            state['batch_size']=batch_size
            batch=queue[offset:offset+batch_size]
            offset+=len(batch)
            began=time.time();state.update(current=batch[0].name,current_started=began);jobs.publish(state)
            body,identities=make_batch(batch,conf)
            state['missing']+=len(batch)-len(identities)
            if not identities:continue
            while True:
                try:
                    url=endpoint(conf);response=request(url,body);break
                except urllib.error.HTTPError as error:
                    if error.code<500:raise RuntimeError('PC rejected batch: '+error.read(1000).decode(errors='replace')) from error
                    state.update(status='loading',remote_error='PC service unavailable; retrying');jobs.publish(state);time.sleep(10)
                except InterruptedError:
                    raise
                except (OSError,http.client.HTTPException):
                    forget(conf)
                    state.update(status='loading',remote_error='PC service unavailable; retrying');jobs.publish(state);time.sleep(10)
            results=response.get('items',[])
            if len(results)!=len(identities) or {r['member'] for r in results}!=set(identities):raise ValueError('Batch result set mismatch')
            state.update(status='running',remote_error='',service_backend=response.get('backend','unknown'),transport='ssh' if '127.0.0.1' in url else 'lan')
            for result in results:
                path,identity,sha=identities[result['member']]
                if result['sha256']!=sha:raise ValueError('Result/source checksum mismatch')
                if 'error' in result:
                    from archive_retention import record_failure
                    from utils.helpers import DB_PATH
                    record_failure(path,DB_PATH,result['error'],'remote',result.get('seconds'))
                    jobs.preserve_failure(path,RuntimeError(result['error']),quarantine=False)
                    state['failed']+=1
                else:
                    try:
                        detections=commit(path,identity,result,proxy)
                    except FileNotFoundError:
                        state['missing']+=1;continue
                    except Exception as error:
                        from archive_retention import record_failure
                        from utils.helpers import DB_PATH
                        record_failure(path,DB_PATH,error,'remote',result.get('seconds'))
                        raise
                    state['processed']+=1
                    from archive_retention import remove_empty_source
                    from utils.helpers import DB_PATH
                    cleanup='retained_detections' if detections else 'retained_unknown'
                    if detections == 0:
                        try:cleanup=remove_empty_source(path,identity,DB_PATH)
                        except (OSError,sqlite3.Error) as error:
                            cleanup='cleanup_failed'
                            print(json.dumps({'event':'archive_source_cleanup_failed','file':path.name,'error':str(error)}),flush=True)
                    print(json.dumps({'event':'archive_remote_analyzed','file':path.name,'detections':detections,'pc_seconds':result['seconds'],
                                      'original_retained':cleanup not in ('removed','missing'),'source_cleanup':cleanup}),flush=True)
                jobs.publish(state)
            state['processing_seconds']+=time.time()-began
            jobs.publish(state)
        state['status']='done_with_errors' if state['failed'] else 'done'
    except Exception as error:
        state.update(status='interrupted',last_error=str(error)[:500]);raise
    finally:
        state.update(finished=time.time(),current=None);jobs.publish(state)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['probe'])
    parser.add_argument('--url',default='http://127.0.0.1:8766');parser.add_argument('--limit',type=int,default=3)
    args=parser.parse_args()
    import archive_analysis as jobs
    from utils.helpers import get_settings
    conf=get_settings();proxy=Predictions(conf);paths=jobs.pending()[:args.limit]
    t=time.monotonic();body,identities=make_batch(paths,conf);response=request(args.url,body)
    for result in response['items']:
        path,identity,sha=identities[result['member']]
        assert result['sha256']==sha and 'error' not in result,result
        for parsed,detections in analyze_result(path,result,proxy):
            print(json.dumps({'file':path.name,'detections':[{'species':d.scientific_name,'confidence':d.confidence,'start':d.start,'stop':d.stop} for d in detections],'pc_seconds':result['seconds']}),flush=True)
    print(json.dumps({'probe_files':len(identities),'seconds':time.monotonic()-t,'database_changed':False}),flush=True)
