"""Private background settings jobs; the web response never waits for model load."""
import fcntl,json,os,re,subprocess,sys,time,uuid
from pathlib import Path
import model_switch as switch
from settings_plan import fast_keys, AUXILIARY
import settings_external
import hashlib
ROOT=Path('/var/lib/birdnet/settings-jobs')

def write(path,data):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(data));os.chmod(temporary,0o600);os.replace(temporary,path)

def folder(job):
    if not re.fullmatch(r'[a-f0-9]{32}',job):raise ValueError('Invalid job')
    return ROOT/job

def enqueue(revision=None):
    text=sys.stdin.read(131073)
    if not text or len(text)>131072:raise ValueError('Invalid settings size')
    # A live cleanup limit needs neither service work nor a transient unit.
    with open('/run/lock/birdnet-model-switch.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        base_text=switch.CONFIG.read_text()
        if revision is not None and hashlib.sha256(base_text.encode()).hexdigest()!=revision:
            raise RuntimeError('Settings changed in another request; reload the form')
        text=switch.merge_changed(base_text,text)
        changed=switch.changed_settings(switch.values(base_text),switch.values(text))
        if changed <= fast_keys(switch.values(switch.CONFIG.read_text())):
            if changed:switch.apply(text)
            print(json.dumps({'status':'done','changed_keys':sorted(changed),'revision':hashlib.sha256(switch.CONFIG.read_bytes()).hexdigest()}))
            return
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    job=uuid.uuid4().hex;path=folder(job);path.mkdir(mode=0o700)
    (path/'candidate.conf').write_text(text);os.chmod(path/'candidate.conf',0o600)
    (path/'base.conf').write_text(base_text);os.chmod(path/'base.conf',0o600)
    write(path/'status.json',{'job':job,'status':'queued','created':time.time()})
    subprocess.run(['systemd-run','--quiet','--collect','--unit=birdnet-settings-'+job,
                    '/usr/bin/python3',str(Path(__file__).resolve()),'apply',job],check=True,timeout=15)
    print(json.dumps({'job':job,'status':'queued'}))

def apply(job):
    path=folder(job);state={'job':job,'status':'applying','started':time.time()};write(path/'status.json',state)
    try:
        with open('/run/lock/birdnet-model-switch.lock','a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            candidate=(path/'candidate.conf').read_text()
            # Merge only requested changes into the current config. Never replay
            # stale unchanged fields over another completed background save.
            if (path/'base.conf').exists():
                original=switch.values((path/'base.conf').read_text())
                requested=switch.values(candidate);current=switch.values(switch.CONFIG.read_text())
                keys=switch.changed_settings(original,requested)
                if any(current.get(k)!=original.get(k) and current.get(k)!=requested.get(k) for k in keys):
                    raise RuntimeError('Settings changed in another request; reload the form')
                raw=dict(re.findall(r'^([A-Za-z_][A-Za-z_0-9]*)=(.*)$',candidate,re.M))
                candidate=switch.CONFIG.read_text()
                for key in keys:
                    if key in raw:candidate=switch.replace(candidate,key,raw[key])
            candidate=re.sub(r'^ARCHIVE_(FORMAT|SEGMENT_SECONDS|PURGE_PERCENT|TARGET_PERCENT|PURGE_BATCH)=.*\n?','',candidate,flags=re.M)
            before=switch.values(switch.CONFIG.read_text());after=switch.values(candidate)
            changed=switch.changed_settings(before,after)
            state['changed_keys']=sorted(changed);write(path/'status.json',state)
            restart=[u for u,keys in AUXILIARY.items() if changed&keys and switch.active(u)]
            caddy_active=bool(changed&{'CADDY_PWD','BIRDNETPI_URL'}) and switch.active('caddy')
            icecast_active='ICE_PWD' in changed and switch.active('icecast2')
            previous=switch.CONFIG.read_text()
            if changed:switch.apply(candidate)
            icecast_applied=caddy_applied=False
            try:
                if 'ICE_PWD' in changed:
                    settings_external.icecast(after.get('ICE_PWD',''),icecast_active);icecast_applied=True
                if changed&{'CADDY_PWD','BIRDNETPI_URL'}:
                    settings_external.caddy(before,after,caddy_active);caddy_applied=True
                if before.get('OPERATION_MODE','normal')==after.get('OPERATION_MODE','normal'):
                    for unit in restart:
                        if switch.active(unit):subprocess.run(['systemctl','restart',unit],check=True,timeout=120)
            except Exception:
                switch.apply(previous)
                if icecast_applied:settings_external.icecast(before.get('ICE_PWD',''),icecast_active)
                if caddy_applied:settings_external.caddy(after,before,caddy_active)
                for unit in restart:
                    if switch.active(unit):subprocess.run(['systemctl','restart',unit],check=True,timeout=120)
                raise
            state.update(status='done',finished=time.time(),revision=hashlib.sha256(switch.CONFIG.read_bytes()).hexdigest())
    except Exception as error:state.update(status='failed',error=str(error),finished=time.time())
    finally:
        (path/'candidate.conf').unlink(missing_ok=True)
        (path/'base.conf').unlink(missing_ok=True)
        write(path/'status.json',state)

if __name__=='__main__':
    if os.geteuid()!=0:raise SystemExit('Run using sudo')
    if sys.argv[1:2]==['enqueue'] and len(sys.argv) in (2,3):enqueue(sys.argv[2] if len(sys.argv)==3 else None)
    elif len(sys.argv)==3 and sys.argv[1]=='apply':apply(sys.argv[2])
    elif len(sys.argv)==3 and sys.argv[1]=='status':print((folder(sys.argv[2])/'status.json').read_text())
    else:raise SystemExit('Invalid command')
