"""Private background settings jobs; the web response never waits for model load."""
import fcntl,json,os,re,subprocess,sys,time,uuid
from pathlib import Path
import model_switch as switch
ROOT=Path('/var/lib/birdnet/settings-jobs')

def write(path,data):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(data));os.chmod(temporary,0o600);os.replace(temporary,path)

def folder(job):
    if not re.fullmatch(r'[a-f0-9]{32}',job):raise ValueError('Invalid job')
    return ROOT/job

def enqueue():
    text=sys.stdin.read(131073)
    if not text or len(text)>131072:raise ValueError('Invalid settings size')
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    job=uuid.uuid4().hex;path=folder(job);path.mkdir(mode=0o700)
    (path/'candidate.conf').write_text(text);os.chmod(path/'candidate.conf',0o600)
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
            candidate=re.sub(r'^ARCHIVE_(FORMAT|SEGMENT_SECONDS|PURGE_PERCENT|TARGET_PERCENT|PURGE_BATCH)=.*\n?','',candidate,flags=re.M)
            before=switch.values(switch.CONFIG.read_text());after=switch.values(candidate)
            changed={k for k in before.keys()|after.keys() if before.get(k)!=after.get(k)}
            state['changed_keys']=sorted(changed);write(path/'status.json',state)
            auxiliary={'chart_viewer':{'SITE_NAME','COLOR_SCHEME','RARE_SPECIES_THRESHOLD'},
                       'livestream':{'ICE_PWD','RTSP_STREAM','RTSP_STREAM_TO_LIVESTREAM','ACTIVATE_FREQSHIFT_IN_LIVESTREAM','FREQSHIFT_HI','FREQSHIFT_LO','LogLevel_LiveAudioStreamService'},
                       'spectrogram_viewer':{'LogLevel_SpectrogramViewerService'}}
            restart=[u for u,keys in auxiliary.items() if changed&keys and switch.active(u)]
            caddy_active=switch.active('caddy')
            switch.apply(candidate)
            if before.get('OPERATION_MODE','normal')==after.get('OPERATION_MODE','normal'):
                for unit in restart:
                    if switch.active(unit):subprocess.run(['systemctl','restart',unit],check=True,timeout=120)
            if changed&{'CADDY_PWD','BIRDNETPI_URL'} and caddy_active:
                subprocess.run(['/usr/local/bin/update_caddyfile.sh'],check=True,timeout=60)
            state.update(status='done',finished=time.time())
    except Exception as error:state.update(status='failed',error=str(error),finished=time.time())
    finally:
        (path/'candidate.conf').unlink(missing_ok=True)
        write(path/'status.json',state)

if __name__=='__main__':
    if os.geteuid()!=0:raise SystemExit('Run using sudo')
    if sys.argv[1:]==['enqueue']:enqueue()
    elif len(sys.argv)==3 and sys.argv[1]=='apply':apply(sys.argv[2])
    elif len(sys.argv)==3 and sys.argv[1]=='status':print((folder(sys.argv[2])/'status.json').read_text())
    else:raise SystemExit('Invalid command')
