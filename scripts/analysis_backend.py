"""Validated local/remote analysis selection shared by Settings and workers."""
import ipaddress,json,urllib.request

V3='BirdNET+_V3.0-preview3.1_Global_11K_FP16_pruned'
MODEL_SHA='f4af6290690e0031cd785d4c810167af83467ce1426f4eba249ca994681000db'
LABELS_SHA='8124b0ea2d187104c5e2cd95a0f937165647e20349c8fd34d4d5ef991821f8f0'
KEYS={'ANALYSIS_BACKEND','REMOTE_ANALYSIS_IP','REMOTE_ANALYSIS_BATCH'}
NETWORKS=[ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')]
_endpoints={}

def clean(value):return str(value).strip().strip('"')

def private_ip(value):
    ip=ipaddress.ip_address(clean(value))
    if ip.version!=4 or not any(ip in net for net in NETWORKS):raise ValueError('Enter a private LAN IPv4 address for the analysis computer')
    return str(ip)

def validate(config,check=False):
    mode=clean(config.get('ANALYSIS_BACKEND','local'))
    if mode not in ('local','remote'):raise ValueError('Unknown analysis backend')
    batch=int(clean(config.get('REMOTE_ANALYSIS_BATCH','10')))
    if not 1<=batch<=100:raise ValueError('Remote batch size must be 1..100')
    host=clean(config.get('REMOTE_ANALYSIS_IP',''))
    if mode=='remote':
        private_ip(host)
        if clean(config.get('MODEL',''))!=V3:raise ValueError('Remote computer analysis currently requires BirdNET V3')
        if check:endpoint(config,refresh=True)
    return mode,host,batch

def health(url):
    with urllib.request.urlopen(url+'/health',timeout=3) as response:data=json.load(response)
    if not data.get('ready') or data.get('model_sha256')!=MODEL_SHA or data.get('labels_sha256')!=LABELS_SHA:
        raise ValueError('Remote service is not ready or uses a different BirdNET model')
    return data

def endpoint(config,refresh=False):
    host=private_ip(config.get('REMOTE_ANALYSIS_IP',''))
    if not refresh and host in _endpoints:return _endpoints[host]
    _endpoints.pop(host,None)
    direct='http://'+host+':8766'
    try:health(direct);_endpoints[host]=direct;return direct
    except (OSError,ValueError):pass
    # Existing installations may retain an authenticated reverse SSH tunnel.
    # Never use a tunnel to a different computer than the configured LAN IP.
    try:
        forwarded='http://127.0.0.1:8766';data=health(forwarded)
        if host in data.get('addresses',[]):_endpoints[host]=forwarded;return forwarded
    except (OSError,ValueError):pass
    raise OSError('Analysis computer '+host+' is unavailable on port 8766; start its service')

def forget(config):_endpoints.pop(clean(config.get('REMOTE_ANALYSIS_IP','')),None)
