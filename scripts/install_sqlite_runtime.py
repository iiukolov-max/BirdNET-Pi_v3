"""Install/upgrade SQLite policy with a verified, private migration backup."""
import datetime,os,subprocess,sys,uuid
from pathlib import Path
def install(root):
    root=Path(root).resolve();database=root/'scripts/birds.db'
    if not database.is_file():raise RuntimeError('Create the BirdNET database before configuring SQLite')
    folder=root.parent/'birdnet-backups'/('sqlite-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
    folder.mkdir(parents=True,mode=0o700);os.chmod(folder,0o700)
    subprocess.run([sys.executable,str(root/'scripts/migrate_sqlite_wal.py'),str(database),str(folder/'birds.db')],check=True,timeout=120)
    print('SQLite runtime configured; private backup: '+str(folder),flush=True)
if __name__=='__main__':
    if os.geteuid()!=0:raise SystemExit('Run as root')
    install(Path(__file__).resolve().parent.parent)
