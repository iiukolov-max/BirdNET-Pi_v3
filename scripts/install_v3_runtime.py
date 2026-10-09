#!/usr/bin/env python3
"""Install the optional, pinned V3 cache profile; commit only after exact checks."""
import argparse
import contextlib
try:
    import fcntl
except ImportError:
    fcntl=None
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request

UNITS=('birdnet_analysis.service','birdnet_recording.service')

def emit(event,**values):print(json.dumps({'event':event,**values}),flush=True)

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
    return h.hexdigest()

def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.chmod(name,0o644);os.replace(name,path)
    finally:
        Path(name).unlink(missing_ok=True)

def state(unit):
    return subprocess.check_output(['systemctl','show',unit,'--value','-p','ActiveState'],text=True).strip()

def restore(root):
    path=root/'runtime/install-restore.json'
    if not path.exists():return
    saved=json.loads(path.read_text())
    if saved.get('recovered'):return
    manual=state('birdnet-archive-analysis.service') in ('active','activating','deactivating')
    for unit in saved['active_units']:
        if unit=='birdnet_recording.service' and manual:continue
        policy=root/'scripts/birdnet_service_policy.py'
        if policy.exists() and subprocess.run(['/usr/bin/python3',str(policy),'check',unit],capture_output=True).returncode:continue
        subprocess.run(['systemctl','start',unit],check=True,timeout=120)
    saved.update(recovered=True,recovered_at=time.time());atomic(path,json.dumps(saved,indent=2).encode())
    emit('v3_runtime_services_restored',units=saved['active_units'])

@contextlib.contextmanager
def paused(root,manage):
    if not manage:
        yield;return
    if state('birdnet-archive-analysis.service') in ('active','activating','deactivating'):
        raise RuntimeError('Manual analysis is running; retry runtime installation after completion')
    saved={'active_units':[u for u in UNITS if state(u) in ('active','activating')],
           'recovered':False,'started':time.time()}
    atomic(root/'runtime/install-restore.json',json.dumps(saved,indent=2).encode())
    try:
        # Finish/stop normal inference first, then pause microphone recording.
        subprocess.run(['systemctl','stop',*UNITS],check=True,timeout=180)
        emit('v3_runtime_preflight_started',microphone_paused=True)
        yield
    finally:restore(root)

def compatible(supported):
    if platform.machine()!=supported['machine'] or list(sys.version_info[:2])!=supported['python']:return False
    os_release=Path('/etc/os-release').read_text()
    if ('VERSION_CODENAME='+supported['os_codename']) not in os_release:return False
    device=Path('/proc/device-tree/model')
    if not device.exists() or supported['device_contains'] not in device.read_text().rstrip('\0'):return False
    libc,version=platform.libc_ver()
    if libc!='glibc' or tuple(int(n) for n in version.split('.')[:2])<tuple(supported['glibc_min']):return False
    import numpy as np
    return int(np.__version__.split('.')[0])==supported['numpy_major']

def artifact(entry,folder,assets):
    name=entry['name']
    if Path(name).name!=name or name in ('.','..'):raise ValueError('Unsafe artifact name')
    target=folder/name
    if assets:
        shutil.copyfile(assets/name,target)
    else:
        if not entry['url'].startswith('https://github.com/iiukolov-max/birdnet-tflite-runtime/releases/download/'):
            raise ValueError('Unexpected runtime artifact origin')
        request=urllib.request.Request(entry['url'],headers={'User-Agent':'BirdNET-Pi-runtime-installer/1'})
        with urllib.request.urlopen(request,timeout=90) as inp,target.open('wb') as out:
            count=0
            for chunk in iter(lambda:inp.read(1048576),b''):
                count+=len(chunk)
                if count>entry['bytes']:raise ValueError('Oversized artifact')
                out.write(chunk)
    if target.stat().st_size!=entry['bytes'] or digest(target)!=entry['sha256']:raise ValueError('Artifact checksum/size mismatch: '+name)
    return target

def worker(args):
    import numpy as np
    os.environ.pop('BIRDNET_RESEARCH_XNNPACK_CACHE',None)
    if args.worker=='candidate':
        sys.path.insert(0,str(args.runtime_dir))
        from birdnet_tflite_cached.interpreter import Interpreter
        if args.cache:os.environ['BIRDNET_RESEARCH_XNNPACK_CACHE']=str(args.cache.resolve())
    else:
        try:from tflite_runtime.interpreter import Interpreter
        except ImportError:from tensorflow.lite import Interpreter
    model=Interpreter(model_path=str(args.model),num_threads=2)
    if args.compatibility:
        model.allocate_tensors()
        inputs=model.get_input_details();outputs=model.get_output_details()
        geo=len(inputs)==1 and list(inputs[0]['shape'])==[1,3]
        rng=np.random.default_rng(20261009)
        samples=([[np.array([[lat,lon,week]],dtype=np.float32)]
                  for lat,lon in ((55.75,37.62),(0,0),(-33.87,151.21)) for week in range(-1,54)] if geo else
                 [[rng.normal(0,.02,tuple(d['shape'])).astype(d['dtype']) for d in inputs] for _ in range(2)])
        values={str(d['index']):[] for d in outputs}
        for sample in samples:
            for d,value in zip(inputs,sample):model.set_tensor(d['index'],value)
            model.invoke()
            for d in outputs:
                value=model.get_tensor(d['index'])
                if not np.isfinite(value).all():raise ValueError('Non-finite compatibility output')
                values[str(d['index'])].append(value)
        np.savez(args.output,**{k:np.stack(v) for k,v in values.items()});return
    inp=model.get_input_details()[0]['index'];model.resize_tensor_input(inp,[1,96000]);model.allocate_tensors()
    outputs=[row['index'] for row in model.get_output_details() if list(row['shape'])==[1,11560]]
    if len(outputs)!=1:raise ValueError('Full V3 taxonomy/output mismatch')
    values=[]
    for sample in np.load(args.input,allow_pickle=False):
        model.set_tensor(inp,sample.reshape(1,96000));model.invoke()
        value=model.get_tensor(outputs[0]).reshape(-1)
        if not np.isfinite(value).all():raise ValueError('Non-finite inference output')
        values.append(value)
    np.save(args.output,np.stack(values),allow_pickle=False)

def invoke(args,stage,kind,output,model,runtime=None,cache=None,compatibility=False):
    command=[str(args.python),str(Path(__file__).resolve()),'--worker',kind,'--input',str(stage/'input.npy'),
             '--output',str(output),'--model',str(model)]
    if runtime:command+=['--runtime-dir',str(runtime)]
    if cache:command+=['--cache',str(cache)]
    if compatibility:command+=['--compatibility']
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    with (stage/(output.stem+'.log')).open('w') as log:
        with subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT) as process:
            try:
                deadline=time.monotonic()+600
                while process.poll() is None:
                    if time.monotonic()>deadline:raise TimeoutError('Runtime verification exceeded600s')
                    if not args.no_services and state('birdnet-archive-analysis.service') in ('active','activating'):
                        raise RuntimeError('Manual analysis started during installation; installation deferred')
                    time.sleep(2)
                if process.returncode:raise RuntimeError('Runtime verification child failed: '+str(process.returncode)+'; see '+str(stage))
            except BaseException:
                process.kill();process.wait();raise

def compare_compatibility(expected,actual,legacy=False):
    import numpy as np
    if set(expected.files)!=set(actual.files):raise ValueError('Model output tensors differ')
    exact=True;delta=0.
    for name in expected.files:
        a,b=expected[name],actual[name]
        if a.shape!=b.shape or not np.isfinite(b).all():raise ValueError('Invalid compatibility output')
        same=np.array_equal(a,b);exact &= same
        difference=float(np.max(np.abs(a-b)));delta=max(delta,difference)
        if not same and (not legacy or difference>1e-4 or
                not np.array_equal(np.argsort(a,axis=-1)[...,-5:],np.argsort(b,axis=-1)[...,-5:])):
            raise ValueError('Model outputs differ beyond qualified compatibility limits')
    return {'bit_exact':bool(exact),'max_abs':delta,'legacy_v1':legacy}

def check_models(args,stage,canonical=False):
    import numpy as np
    names=['BirdNET+_Geomodel_V3.0.4_Global_14K_FP32.tflite','BirdNET_6K_GLOBAL_MODEL.tflite',
           'BirdNET_GLOBAL_6K_V2.4_Model_FP16.tflite','BirdNET_GLOBAL_6K_V2.4_MData_Model_FP16.tflite',
           'BirdNET_GLOBAL_6K_V2.4_MData_Model_V2_FP16.tflite']
    results=[]
    for index,name in enumerate(names):
        model=args.root.resolve()/'model'/name
        if not model.is_file():raise ValueError('Required model missing: '+name)
        original=stage/('compat-original-'+str(index)+'.npz')
        candidate=stage/('compat-'+('canonical-' if canonical else 'candidate-')+str(index)+'.npz')
        if not canonical:invoke(args,stage,'original',original,model,compatibility=True)
        invoke(args,stage,'original' if canonical else 'candidate',candidate,model,
               None if canonical else stage,compatibility=True)
        with np.load(original,allow_pickle=False) as a,np.load(candidate,allow_pickle=False) as b:
            results.append({'model':name,**compare_compatibility(a,b,name=='BirdNET_6K_GLOBAL_MODEL.tflite')})
    atomic(stage/('canonical-model-checks.json' if canonical else 'model-checks.json'),json.dumps(results,indent=2).encode())
    return results

def install(args):
    manifest=json.loads(args.manifest.read_text())
    if manifest.get('schema_version')!=1:raise ValueError('Unknown runtime manifest')
    if not compatible(manifest['supported']):
        emit('v3_runtime_skipped',reason='No qualified package for this device/OS/Python/NumPy; original runtime retained')
        return
    if os.geteuid()!=0:raise RuntimeError('Run installer with sudo and the BirdNET Python interpreter')
    root=args.root.resolve();parent=root/'runtime';parent.mkdir(exist_ok=True)
    with (parent/'install.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        previous=json.loads(args.profile.read_text()) if args.profile.exists() else {}
        original=root/'model/BirdNET+_V3.0-preview3.1_Global_11K_FP16_pruned.tflite'
        if digest(original)!=manifest['original_model_sha256']:raise ValueError('Original V3 model checksum mismatch')
        if not args.force and previous.get('release')==manifest['release']:
            artifacts=previous.get('artifacts',{})
            bridge_ready=True
            if manifest.get('unified_runtime'):
                site=Path(subprocess.check_output([str(args.python),'-c','import sysconfig; print(sysconfig.get_path("purelib"))'],text=True).strip())
                bridge_ready=(site/'tflite_runtime').is_symlink() and (site/'tflite_runtime').resolve()==Path(previous['runtime_dir'])/'tflite_runtime'
            if bridge_ready and artifacts and all(Path(p).is_file() and digest(p)==h for p,h in artifacts.items()):
                emit('v3_runtime_already_installed',release=manifest['release'],enabled=previous.get('enabled'));return
        if shutil.disk_usage(parent).free<640*1024**2:raise RuntimeError('At least640MiB free space required')
        stage=Path(tempfile.mkdtemp(prefix='v3-'+manifest['release']+'-',dir=parent));os.chmod(stage,0o755)
        emit('v3_runtime_staging',directory=str(stage),release=manifest['release'])
        wheel=artifact(manifest['wheel'],stage,args.assets_dir)
        compressed=artifact(manifest['model']['compressed'],stage,args.assets_dir)
        model=stage/manifest['model']['name']
        with gzip.open(compressed,'rb') as inp,model.open('wb') as out:
            count=0
            for chunk in iter(lambda:inp.read(1048576),b''):
                count+=len(chunk)
                if count>manifest['model']['bytes']:raise ValueError('Oversized decompressed model')
                out.write(chunk)
        if model.stat().st_size!=manifest['model']['bytes'] or digest(model)!=manifest['model']['sha256']:raise ValueError('FP32 model checksum mismatch')
        subprocess.run([str(args.python),'-m','pip','install','--no-index','--no-deps','--no-compile','--disable-pip-version-check',
                        '--target',str(stage),str(wheel)],check=True,timeout=180)
        bridge=None
        if manifest.get('unified_runtime'):
            bridge=artifact(manifest['compat_wheel'],stage,args.assets_dir)
            subprocess.run([str(args.python),'-m','pip','install','--no-index','--no-deps','--no-compile',
                            '--target',str(stage),str(bridge)],check=True,timeout=180)
        package=stage/'birdnet_tflite_cached'
        if digest(package/'_pywrap_tensorflow_interpreter_wrapper.so')!=manifest['runtime_sha256']:raise ValueError('Runtime binary checksum mismatch')
        import numpy as np
        rng=np.random.default_rng(42)
        samples=np.stack([rng.normal(0,.002,96000).astype(np.float32),rng.normal(0,.02,96000).astype(np.float32),
                          (.02*np.sin(np.arange(96000)*(.01+np.arange(96000)/1e7))).astype(np.float32),
                          rng.normal(0,.1,96000).astype(np.float32)])
        np.save(stage/'input.npy',samples,allow_pickle=False)
        cache=stage/'weights.xnnpack'
        canonical_switch=None
        with paused(root,not args.no_services):
            invoke(args,stage,'original',stage/'original.npy',original)
            invoke(args,stage,'candidate',stage/'candidate.npy',model,stage,cache)
            invoke(args,stage,'candidate',stage/'cache-reload.npy',model,stage,cache)
            expected=np.load(stage/'original.npy',allow_pickle=False)
            for name in ('candidate.npy','cache-reload.npy'):
                if not np.array_equal(expected,np.load(stage/name,allow_pickle=False)):raise ValueError('Optimized full-class outputs differ from original')
            if not cache.is_file() or not cache.stat().st_size:raise ValueError('Cache generation failed')
            if manifest.get('unified_runtime'):check_models(args,stage)
            os.chmod(cache,0o644)
            tracked=[model,cache,*[p for p in package.iterdir() if p.suffix in ('.py','.so')]]
            if manifest.get('unified_runtime'):tracked.extend((stage/'tflite_runtime').glob('*.py'))
            profile={'enabled':previous.get('enabled',True),'release':manifest['release'],'machine':'aarch64','python':[3,13],
                     'original_model_sha256':manifest['original_model_sha256'],
                     'runtime_dir':str(stage),'model':str(model),'cache':str(cache),'installed':time.time(),
                     'artifacts':{str(p):digest(p) for p in tracked},'validation':'4x11560 bit-exact original/cold-cache/reloaded-cache'}
            profile['unified_runtime']=bool(manifest.get('unified_runtime'))
            profile['runtime_sha256']=manifest['runtime_sha256']
            # No new profile can be selected until all native child checks pass.
            if args.profile.exists():atomic(stage/'previous-profile.json',args.profile.read_bytes())
            atomic(args.profile,json.dumps(profile,indent=2).encode())
            if manifest.get('unified_runtime'):
                from single_tflite import switch,rollback
                try:
                    canonical_switch=switch(args.python,stage)
                    check_models(args,stage,canonical=True)
                except BaseException:
                    if canonical_switch:rollback(canonical_switch)
                    if previous:atomic(args.profile,json.dumps(previous,indent=2).encode())
                    else:args.profile.unlink(missing_ok=True)
                    raise
            emit('v3_runtime_installed',release=manifest['release'],enabled=profile['enabled'],validated_outputs=4*11560)
        # Large download containers and private verification inputs are no longer needed.
        for path in (wheel,compressed,stage/'input.npy',stage/'original.npy',stage/'candidate.npy',stage/'cache-reload.npy'):path.unlink(missing_ok=True)
        if bridge:bridge.unlink(missing_ok=True)
        for path in stage.glob('compat-*.npz'):path.unlink()
        if canonical_switch:
            from single_tflite import finish
            finish(canonical_switch,stage)
            retired=Path(previous.get('runtime_dir',''))
            if (previous.get('runtime_dir') and not retired.is_symlink() and retired.resolve()!=stage.resolve()
                    and retired.resolve().parent==parent.resolve() and retired.name.startswith('v3-')):
                shutil.rmtree(retired)
                emit('retired_runtime_removed',directory=str(retired))
            emit('single_tflite_active',original_native_library_removed=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--manifest',type=Path,default=Path(__file__).with_name('v3-runtime-manifest.json'))
    parser.add_argument('--profile',type=Path,default=Path('/etc/birdnet/v3-runtime.json'))
    parser.add_argument('--python',type=Path,default=Path(sys.executable))
    parser.add_argument('--assets-dir',type=Path)
    parser.add_argument('--force',action='store_true');parser.add_argument('--strict',action='store_true')
    parser.add_argument('--no-services',action='store_true');parser.add_argument('--recover',action='store_true')
    parser.add_argument('--worker',choices=('original','candidate'))
    parser.add_argument('--compatibility',action='store_true')
    for name in ('input','output','model','runtime-dir','cache'):parser.add_argument('--'+name,type=Path)
    args=parser.parse_args()
    if args.worker:worker(args);return
    if args.recover:restore(args.root.resolve());return
    signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(RuntimeError('Runtime installation interrupted')))
    try:install(args)
    except Exception as error:
        emit('v3_runtime_install_failed',error=str(error),fallback='Profile is activated only after exact checks; inspect service recovery log and retry if needed')
        if args.strict:raise

if __name__=='__main__':main()
