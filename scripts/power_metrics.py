"""Minute-scale power-related telemetry. No credentials or audio contents."""
import datetime
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

INTERVAL=60
DIRECTORY=Path('/home/pi/BirdNET-Pi/power-logs')
DIRECTORY.mkdir(exist_ok=True)
logger=logging.getLogger('power_metrics')
logger.setLevel(logging.INFO)
handler=RotatingFileHandler(DIRECTORY/'metrics.jsonl',maxBytes=8*1024*1024,backupCount=7,encoding='utf-8')
handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(handler)

def read(path):
    try:return Path(path).read_text().strip()
    except OSError:return None

def command(args):
    try:
        result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,timeout=8)
        return result.stdout.strip() if result.returncode==0 else None
    except (OSError,subprocess.TimeoutExpired):return None

def settings():
    # Never log arbitrary config: it can contain passwords and notification URLs.
    allowed={'MODEL','OVERLAP','RECORDING_LENGTH','CHANNELS','CONFIDENCE','EXTRACTION_LENGTH','AUDIOFMT','RECS_DIR'}
    result={}
    for line in (read('/home/pi/BirdNET-Pi/birdnet.conf') or '').splitlines():
        key,separator,value=line.partition('=')
        if separator and key in allowed:result[key]=value.strip().strip('"\'')
    return result

def service(name):
    result=command(['systemctl','show',name,'-p','MainPID','-p','NRestarts','-p','ActiveState','-p','CPUUsageNSec'])
    info=dict(line.split('=',1) for line in (result or '').splitlines() if '=' in line)
    pid=int(info.get('MainPID','0'))
    if pid:
        memory={}
        for line in (read('/proc/'+str(pid)+'/status') or '').splitlines():
            key,_,value=line.partition(':')
            if key in {'VmRSS','VmSwap','VmHWM','Threads'}:memory[key]=value.strip()
        info['memory']=memory
        stat=read('/proc/'+str(pid)+'/stat')
        if stat:
            fields=stat.rsplit(')',1)[1].split()
            info['cpu_ticks']=int(fields[11])+int(fields[12])
            info['major_faults']=int(fields[9])
        io=read('/proc/'+str(pid)+'/io')
        if io:info['io']={key:int(value) for key,value in (line.split(':',1) for line in io.splitlines())}
        # Select only this non-secret control value from the process environment.
        env=read('/proc/'+str(pid)+'/environ')
        if env:
            for value in env.split('\0'):
                if value.startswith('BIRDNET_V3_THREADS='):
                    info['v3_threads_environment']=value.split('=',1)[1]
    return info

def sample():
    conf=settings()
    vm=dict(line.split() for line in (read('/proc/vmstat') or '').splitlines())
    mem={key:int(value.split()[0]) for key,value in (line.split(':',1) for line in (read('/proc/meminfo') or '').splitlines())
         if key in {'MemTotal','MemAvailable','SwapTotal','SwapFree','Dirty','Writeback'}}
    cpustat=next(line for line in read('/proc/stat').splitlines() if line.startswith('cpu '))
    cpu=[int(value) for value in cpustat.split()[1:9]]
    policy=Path('/sys/devices/system/cpu/cpufreq/policy0')
    freq={name:read(policy/name) for name in ['scaling_cur_freq','scaling_min_freq','scaling_max_freq','scaling_governor']}
    freq['time_in_state']=read(policy/'stats/time_in_state')
    recs=Path(conf.get('RECS_DIR','/home/pi/BirdSongs'))/'StreamData'
    files=[]
    for path in recs.glob('*.wav'):
        try:files.append(path.stat())
        except FileNotFoundError:pass
    queue={'wav_count_including_open':len(files),'wav_bytes':sum(s.st_size for s in files),
           'oldest_mtime_age_seconds':max(0,time.time()-min(s.st_mtime for s in files)) if files else 0}
    disk=shutil.disk_usage(recs)
    disks={}
    for line in (read('/proc/diskstats') or '').splitlines():
        fields=line.split()
        if fields[2] in {'mmcblk0','sda','zram0'}:
            disks[fields[2]]={'read_sectors':int(fields[5]),'write_sectors':int(fields[9]),'io_ms':int(fields[12])}
    source=read('/home/pi/BirdNET-Pi/scripts/utils/models.py') or ''
    match=re.search(r"self\.model_name \+ '\.tflite'\), num_threads=(\d+)",source)
    analysis_service=service('birdnet_analysis')
    configured_threads=analysis_service.get('v3_threads_environment')
    if configured_threads is None and "BIRDNET_V3_THREADS" in source:
        configured_threads='2'
    radios=[]
    for path in Path('/sys/class/rfkill').glob('rfkill*'):
        radios.append({key:read(path/key) for key in ['name','type','soft','hard','state']})
    network={path.name:{'operstate':read(path/'operstate'),
                        'tx_bytes':read(path/'statistics/tx_bytes'),'rx_bytes':read(path/'statistics/rx_bytes')}
             for path in Path('/sys/class/net').iterdir() if path.name!='lo'}
    usb=[]
    for path in Path('/sys/bus/usb/devices').iterdir():
        if not (path/'idVendor').exists():continue
        usb.append(dict(device=path.name,vendor=read(path/'idVendor'),product_id=read(path/'idProduct'),
                        product=read(path/'product'),runtime_status=read(path/'power/runtime_status')))
    return dict(schema=1,time=datetime.datetime.now().astimezone().isoformat(),
                monotonic_seconds=time.monotonic(),boot_id=read('/proc/sys/kernel/random/boot_id'),
                uptime_seconds=float(read('/proc/uptime').split()[0]),load_average=list(os.getloadavg()),
                cpu_ticks=cpu,memory_kib=mem,frequency=freq,
                temperature_c=int(read('/sys/class/thermal/thermal_zone0/temp'))/1000,
                throttled=command(['vcgencmd','get_throttled']),
                core_voltage=command(['vcgencmd','measure_volts','core']),
                radios=radios,network=network,usb=usb,display_power=command(['vcgencmd','display_power']),
                vmstat={key:int(vm[key]) for key in ['pswpin','pswpout','pgmajfault']},
                pressure={key:read('/proc/pressure/'+key) for key in ['cpu','memory','io']},
                disk_counters=disks,disk_free_bytes=disk.free,queue=queue,
                analysis=analysis_service,recording=service('birdnet_recording'),
                settings=conf,v3_threads_in_source=int(match.group(1)) if match else None,
                v3_threads_configured=int(configured_threads) if configured_threads else (int(match.group(1)) if match else None))

previous=None
while True:
    started=time.monotonic()
    try:
        current=sample()
        if previous and current['boot_id']==previous['boot_id']:
            elapsed=current['monotonic_seconds']-previous['monotonic_seconds']
            diffs=[a-b for a,b in zip(current['cpu_ticks'],previous['cpu_ticks'])]
            total=sum(diffs)
            current['interval_seconds']=elapsed
            current['cpu_busy_percent']=100*(total-diffs[3]-diffs[4])/total if total else None
            current['cpu_iowait_percent']=100*diffs[4]/total if total else None
            current['swap_in_kib_per_second']=(current['vmstat']['pswpin']-previous['vmstat']['pswpin'])*os.sysconf('SC_PAGE_SIZE')/1024/elapsed
            current['swap_out_kib_per_second']=(current['vmstat']['pswpout']-previous['vmstat']['pswpout'])*os.sysconf('SC_PAGE_SIZE')/1024/elapsed
            for name in ['analysis','recording']:
                now=current[name];old=previous[name]
                if now.get('MainPID')==old.get('MainPID') and 'cpu_ticks' in now and 'cpu_ticks' in old:
                    now['cpu_percent_one_core']=100*(now['cpu_ticks']-old['cpu_ticks'])/os.sysconf('SC_CLK_TCK')/elapsed
                    now['major_faults_per_second']=(now['major_faults']-old['major_faults'])/elapsed
            current['disk_kib_per_second']={name:{'read':(c['read_sectors']-previous['disk_counters'].get(name,c)['read_sectors'])/2/elapsed,
                                                       'write':(c['write_sectors']-previous['disk_counters'].get(name,c)['write_sectors'])/2/elapsed}
                                            for name,c in current['disk_counters'].items()}
        logger.info(json.dumps(current,separators=(',',':')))
        previous=current
    except Exception as exc:
        logger.info(json.dumps(dict(time=datetime.datetime.now().astimezone().isoformat(),error=type(exc).__name__+': '+str(exc))))
    time.sleep(max(1,INTERVAL-(time.monotonic()-started)))
