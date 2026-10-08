"""One chart refresh after a completed archive run, with a recoverable permission lease."""
import fcntl,json,os,pwd,re,subprocess,sys,tempfile,time
from pathlib import Path
CONFIG=Path('/etc/birdnet/birdnet.conf')
ROOT=Path(__file__).resolve().parent.parent
LEASE=Path('/var/lib/birdnet/archive-charts-lease.json')
REQUEST=Path('/var/lib/birdnet/archive-charts-request.json')
LOCK=Path('/run/lock/birdnet-model-switch.lock')
KEY='SERVICE_ALLOW_CHARTS'
def values():return dict(re.findall(r'^([A-Z_]+)=(.*)$',CONFIG.read_text(),re.M))
def read(path):
 try:return json.loads(path.read_text())
 except FileNotFoundError:return {}
def atomic(path,text,mode=None):
 path=path.resolve();info=path.stat() if path.exists() else None
 path.parent.mkdir(parents=True,exist_ok=True)
 fd,name=tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
 try:
  with os.fdopen(fd,'w') as out:out.write(text);out.flush();os.fsync(out.fileno())
  os.chmod(name,mode if mode is not None else info.st_mode&0o777 if info else 0o600)
  if info:os.chown(name,info.st_uid,info.st_gid)
  os.replace(name,path)
  directory=os.open(path.parent,os.O_DIRECTORY)
  try:os.fsync(directory)
  finally:os.close(directory)
 finally:
  if os.path.exists(name):os.unlink(name)
def permission(value):
 text=CONFIG.read_text();line=KEY+'='+value
 text=re.sub('^'+KEY+'=.*$',lambda _:line,text,flags=re.M) if re.search('^'+KEY+'=',text,re.M) else text.rstrip()+'\n'+line+'\n'
 atomic(CONFIG,text)
def recover_locked():
 lease=read(LEASE)
 if lease:
  permission(lease['original']);LEASE.unlink()
  print(json.dumps({'event':'charts_permission_restored','value':lease['original']}),flush=True)
 REQUEST.unlink(missing_ok=True)
def recover():
 with LOCK.open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);recover_locked()
def request(state):
 if values().get('OPERATION_MODE','normal')!='archive' or state.get('status') not in ('done','done_with_errors') or state.get('processed',0)<1:return False
 atomic(REQUEST,json.dumps({'started':state['started'],'pid':state['pid']}))
 subprocess.run(['systemctl','start','--no-block','birdnet-archive-charts.service'],check=True,timeout=30)
 return True
def eligible():
 state=read(ROOT/'.archive-analysis.json');request=read(REQUEST)
 return bool(request and values().get('OPERATION_MODE')=='archive' and state.get('status') in ('done','done_with_errors') and state.get('processed',0)>0 and all(state.get(k)==request.get(k) for k in ('started','pid')))
def run():
 with LOCK.open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  if not eligible():return
  original=values().get(KEY,'1');assert original in ('0','1')
  atomic(LEASE,json.dumps({'original':original,'started':time.time()}))
  REQUEST.unlink()
  result={'status':'running','started':time.time(),'original_permission':original}
  status=ROOT/'.archive-charts.json'
  try:
   permission('1');atomic(status,json.dumps(result),0o644)
   print(json.dumps({'event':'charts_permission_enabled','original':original}),flush=True)
   user=pwd.getpwuid(ROOT.stat().st_uid).pw_name
   subprocess.run(['runuser','-u',user,'--',str(ROOT/'birdnet/bin/python3'),str(ROOT/'scripts/daily_plot.py'),'--latest'],check=True,timeout=240)
   result['status']='done'
  except BaseException as error:
   result.update(status='failed',error=str(error));raise
  finally:
   recover_locked();result['finished']=time.time();atomic(status,json.dumps(result),0o644)
if __name__=='__main__':
 if os.geteuid()!=0:raise SystemExit('Run as root')
 if sys.argv[1:]==['run']:run()
 elif sys.argv[1:]==['recover']:recover()
 elif sys.argv[1:]==['check']:raise SystemExit(0 if eligible() else 1)
 else:raise SystemExit('Expected run / recover / check')
