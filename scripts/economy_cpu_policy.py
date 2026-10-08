"""Root controller: one recording CPU; thermally bounded economy analysis."""
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

POLICY=Path('/sys/devices/system/cpu/cpufreq/policy0')
ORIGINAL=Path('/run/birdnet-cpu-policy-original.json')
STATUS=Path('/run/birdnet-cpu-policy.json')
CONFIG=Path('/etc/birdnet/birdnet.conf')

def command(*args):
    return subprocess.check_output(args,text=True,timeout=15).strip()

def choose_profile(mode,analysis,recording):
    if mode!='archive':return 'normal'
    if analysis in ('active','activating','reloading'):return 'analysis'
    if recording in ('active','activating','reloading'):return 'recording'
    return 'idle'

def thermal_limit(frequencies,current,temp,limited,cool_ticks):
    index=frequencies.index(current)
    if temp>=78 or limited:
        return frequencies[max(0,index-1)],0
    if temp<=74:
        cool_ticks+=1
        if cool_ticks>=15:return frequencies[min(len(frequencies)-1,index+1)],0
        return current,cool_ticks
    return current,0

def bounds(low,high):
    # Keep min<=max through both upward and downward transitions.
    POLICY.joinpath('scaling_min_freq').write_text(str(min(low,int(POLICY.joinpath('scaling_max_freq').read_text()))))
    POLICY.joinpath('scaling_max_freq').write_text(str(high))
    POLICY.joinpath('scaling_min_freq').write_text(str(low))

def affinity(value):
    command('systemctl','set-property','--runtime','birdnet_recording.service','AllowedCPUs='+value)

def restore():
    if not ORIGINAL.exists():return
    saved=json.loads(ORIGINAL.read_text())
    bounds(saved['min'],saved['max'])
    POLICY.joinpath('scaling_governor').write_text(saved['governor'])
    affinity(saved['recording_cpus'])

def main():
    if os.geteuid()!=0:raise RuntimeError('Run as root')
    if sys.argv[1:]==['restore']:restore();return
    if not POLICY.exists():raise RuntimeError('CPU frequency policy0 unavailable')
    if not ORIGINAL.exists():
        saved={name:int(POLICY.joinpath('scaling_'+name+'_freq').read_text()) for name in ('min','max')}
        saved['governor']=POLICY.joinpath('scaling_governor').read_text().strip()
        saved['recording_cpus']=command('systemctl','show','birdnet_recording.service','-p','AllowedCPUs','--value')
        ORIGINAL.write_text(json.dumps(saved))
    saved=json.loads(ORIGINAL.read_text())
    frequencies=sorted(int(n) for n in POLICY.joinpath('scaling_available_frequencies').read_text().split() if saved['min']<=int(n)<=saved['max'])
    if not frequencies:raise RuntimeError('No supported frequencies within original limits')
    governors=POLICY.joinpath('scaling_available_governors').read_text().split()
    profile=None;cap=frequencies[-1];cool_ticks=0;stopping=False
    def stop(*args):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:
        while not stopping:
            match=re.search(r'^OPERATION_MODE=(.*)$',CONFIG.read_text(),re.M)
            mode=match.group(1).strip().strip('"') if match else 'normal'
            units=command('systemctl','show','birdnet-archive-analysis.service','birdnet_recording.service','-p','Id','-p','ActiveState')
            states={}
            for block in units.split('\n\n'):
                fields=dict(line.split('=',1) for line in block.splitlines() if '=' in line)
                states[fields['Id']]=fields['ActiveState']
            selected=choose_profile(mode,states['birdnet-archive-analysis.service'],states['birdnet_recording.service'])
            temperature=int(Path('/sys/class/thermal/thermal_zone0/temp').read_text())/1000
            limited=False
            if selected=='analysis':
                try:limited=bool(int(command('vcgencmd','get_throttled').split('=')[1],16)&0x6)
                except (OSError,subprocess.SubprocessError,ValueError):pass
            if selected!=profile:
                cool_ticks=0
                if selected=='recording':
                    affinity('0');bounds(frequencies[0],frequencies[0])
                    if 'powersave' in governors:POLICY.joinpath('scaling_governor').write_text('powersave')
                elif selected=='analysis':
                    affinity(saved['recording_cpus']);cap=frequencies[-1]
                    bounds(frequencies[0],cap)
                    if 'ondemand' in governors:POLICY.joinpath('scaling_governor').write_text('ondemand')
                else:restore()
                profile=selected
                print(json.dumps({'event':'cpu_profile','profile':profile}),flush=True)
            if selected=='analysis':
                cap,cool_ticks=thermal_limit(frequencies,cap,temperature,limited,cool_ticks)
                bounds(frequencies[0],cap)
            status={'profile':profile,'temperature_c':temperature,'max_khz':int(POLICY.joinpath('scaling_max_freq').read_text()),'current_khz':int(POLICY.joinpath('scaling_cur_freq').read_text()),'recording_cpus':'0' if profile=='recording' else saved['recording_cpus'],'inference_threads':2 if profile=='analysis' else 0,'firmware_limited':limited,'time':time.time()}
            temporary=STATUS.with_suffix('.tmp');temporary.write_text(json.dumps(status));temporary.replace(STATUS)
            time.sleep(2)
    finally:restore()

if __name__=='__main__':main()
