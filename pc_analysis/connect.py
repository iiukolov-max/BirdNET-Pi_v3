"""Keep the authenticated reverse SSH tunnel alive; no credentials are saved."""
import argparse
import getpass
import os
from pathlib import Path
import subprocess
import sys
import time

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host',required=True,help='BirdNET SSH user@host')
    parser.add_argument('--host-key',required=True,help='Verified PuTTY SHA256 host fingerprint')
    parser.add_argument('--plink',default=r'C:\Program Files\PuTTY\plink.exe')
    parser.add_argument('--port',type=int,default=8766)
    parser.add_argument('--background',action='store_true',help='Run tunnel in a hidden background process')
    parser.add_argument('--log-file',default='pc-analysis-tunnel.log')
    parser.add_argument('--pid-file',default='pc-analysis-tunnel.pid')
    parser.add_argument('--password-stdin',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if not Path(args.plink).is_file():parser.error('PuTTY plink.exe not found')
    password=sys.stdin.readline().rstrip('\r\n') if args.password_stdin else getpass.getpass('SSH password (not saved): ')
    if args.background:
        if os.name!='nt':parser.error('Background launcher currently supports Windows only')
        with open(args.log_file,'a',encoding='utf-8') as log:
            child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--host',args.host,
                '--host-key',args.host_key,'--plink',args.plink,'--port',str(args.port),'--password-stdin'],
                stdin=subprocess.PIPE,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        child.stdin.write((password+'\n').encode());child.stdin.flush();child.stdin.close();password=None
        Path(args.pid_file).write_text(str(child.pid),encoding='ascii')
        print('Background SSH tunnel manager PID',child.pid,flush=True)
        return
    process=None
    try:
        while True:
            process=subprocess.Popen([args.plink,'-batch','-hostkey',args.host_key,'-pw',password,
                '-N','-R',f'127.0.0.1:{args.port}:127.0.0.1:{args.port}',args.host],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            print('SSH connection started; reconnects automatically. Ctrl+C to disconnect.',flush=True)
            code=process.wait()
            print('SSH connection ended ('+str(code)+'); retrying in 10 seconds.',flush=True)
            time.sleep(10)
    except KeyboardInterrupt:pass
    finally:
        if process is not None and process.poll() is None:process.terminate();process.wait(timeout=15)
        password=None

if __name__=='__main__':main()
