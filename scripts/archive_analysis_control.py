"""Fixed root command for the authenticated archive-analysis button."""
import os,subprocess,sys,fcntl
from utils.helpers import get_settings
from birdnet_service_policy import allowed
if os.geteuid()!=0:raise SystemExit('Run with sudo')
if sys.argv[1:]!=['start']:raise SystemExit('Expected start')
if get_settings().get('OPERATION_MODE','normal')!='archive':raise SystemExit('Archive mode required')
with open('/run/lock/birdnet-model-switch.lock','a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if not allowed('birdnet-archive-analysis.service'):raise SystemExit('File analysis is disabled in Settings')
    subprocess.run(['systemctl','start','--no-block','birdnet-archive-analysis.service'],check=True,timeout=30)
