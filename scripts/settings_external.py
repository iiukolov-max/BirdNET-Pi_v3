"""Transactional updates of auxiliary server files; never log credentials."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET


def atomic(path, data):
    info=path.stat();fd,name=tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(data)
        os.chown(name,info.st_uid,info.st_gid);os.chmod(name,info.st_mode&0o777)
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


def command(args):
    try:result=subprocess.run(args,capture_output=True,timeout=60)
    except (OSError,subprocess.TimeoutExpired):
        raise RuntimeError('Auxiliary server command failed or timed out') from None
    if result.returncode:raise RuntimeError('Auxiliary server validation or reload failed')
    return result.stdout


def icecast(password, active, path=Path('/etc/icecast2/icecast.xml')):
    original=path.read_bytes();root=ET.fromstring(original)
    auth=root.find('authentication')
    if auth is None:raise ValueError('Icecast authentication section is missing')
    for name in ('source-password','relay-password','admin-password'):
        element=auth.find(name)
        if element is not None:element.text=password
    candidate=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    try:
        atomic(path,candidate)
        if active:command(['systemctl','restart','icecast2.service'])
    except Exception:
        atomic(path,original)
        if active:command(['systemctl','restart','icecast2.service'])
        raise


def caddy(before, after, active, path=Path('/etc/caddy/Caddyfile')):
    original=path.read_bytes();text=original.decode()
    if before.get('CADDY_PWD')!=after.get('CADDY_PWD'):
        password=after.get('CADDY_PWD','')
        if not password:raise ValueError('Web password cannot be empty')
        hashed=command(['caddy','hash-password','--plaintext',password]).decode().strip()
        if not hashed.startswith('$2'):raise RuntimeError('Password hashing failed')
        text,count=re.subn(r'(?m)^(\s*birdnet\s+)\S+\s*$',lambda m:m[1]+hashed,text)
        if not count:raise ValueError('Existing web authentication entry was not found; current routes retained')
    if before.get('BIRDNETPI_URL','')!=after.get('BIRDNETPI_URL',''):
        address=after.get('BIRDNETPI_URL','').strip()
        if any(c in address for c in '\r\n{}\t '):raise ValueError('Invalid web address')
        # Only replace the main site's address; leave every route intact.
        headers=list(re.finditer(r'(?m)^([^\s#{}][^{}\n]*)[ \t]*\{[ \t]*$',text))
        if len(headers)!=1:raise ValueError('Cannot safely identify the main web site')
        header=headers[0]
        old=before.get('BIRDNETPI_URL','').strip()
        tokens=header[1].strip().split()
        if old:
            if old not in tokens:raise ValueError('Configured web address differs from the active site')
            tokens=[address if token==old else token for token in tokens]
        elif address:tokens.append(address)
        new_header=' '.join(token for token in tokens if token)+' {'
        text=text[:header.start()]+new_header+text[header.end():]
    if text.encode()==original:return
    candidate=path.with_name('.Caddyfile.settings-candidate')
    try:
        candidate.write_text(text);os.chmod(candidate,0o600)
        command(['caddy','validate','--config',str(candidate),'--adapter','caddyfile'])
        atomic(path,text.encode())
        if active:command(['systemctl','reload','caddy.service'])
    except Exception:
        if path.read_bytes()!=original:
            atomic(path,original)
            if active:command(['systemctl','reload','caddy.service'])
        raise
    finally:candidate.unlink(missing_ok=True)
