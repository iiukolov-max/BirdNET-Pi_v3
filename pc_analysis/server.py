"""BirdNET V3 batch inference service for an allowlisted local network."""
import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import threading
import time
import zipfile
import ipaddress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL_SHA = 'f4af6290690e0031cd785d4c810167af83467ce1426f4eba249ca994681000db'
LABELS_SHA = '8124b0ea2d187104c5e2cd95a0f937165647e20349c8fd34d4d5ef991821f8f0'
MAX_BODY = 256 * 1024**2


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Engine:
    def __init__(self, model, labels, cache, threads=4):
        import numpy as np
        import tensorflow as tf
        if digest(Path(model).read_bytes()) != MODEL_SHA or digest(Path(labels).read_bytes()) != LABELS_SHA:
            raise ValueError('Model or labels checksum mismatch')
        with open(labels, encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f, delimiter=';'))
        if len(rows) != 11560 or any(int(r['idx']) != i for i, r in enumerate(rows)):
            raise ValueError('Unexpected label order')
        self.labels = [r['sci_name'] for r in rows]
        self.np = np
        self.cache = Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.model = tf.lite.Interpreter(model_path=str(model), num_threads=threads)
        self.input = self.model.get_input_details()[0]['index']
        self.model.resize_tensor_input(self.input, [1, 96000])
        self.model.allocate_tensors()
        self.output = next(d['index'] for d in self.model.get_output_details() if list(d['shape']) == [1, 11560])
        self.lock = threading.Lock()
        self.started = time.time()
        self.files = 0
        self.hits = 0
        self.threads = threads
        self.predict(np.random.default_rng(42).normal(0, .02, 96000).astype('float32'), 10)

    def predict(self, chunk, top_k):
        np = self.np
        if not np.any(chunk):
            return [[name, 0.] for name in self.labels[:top_k]]
        self.model.set_tensor(self.input, chunk[None, :])
        self.model.invoke()
        values = self.model.get_tensor(self.output)[0]
        if not np.isfinite(values).all():
            raise ValueError('Non-finite model output')
        indices = np.argsort(-values, kind='stable')[:top_k]
        return [[self.labels[i], float(values[i])] for i in indices]

    def analyze(self, data, overlap, top_k):
        import soundfile as sf
        import soxr
        np = self.np
        # Match archive_analysis.decode_archive -> float32 WAV reading on Pi.
        audio, rate = sf.read(io.BytesIO(data), dtype='int16', always_2d=True)
        if not len(audio) or len(audio) / rate > 120:
            raise ValueError('Empty recording or duration above 120 seconds')
        signal = audio.astype('float32') / np.float32(32768.)
        if signal.shape[1] == 2:
            signal = np.add(signal[:, 0], signal[:, 1]) * np.float32(.5)
        elif signal.shape[1] == 1:
            signal = signal[:, 0]
        else:
            signal = signal.mean(axis=1)
        if rate != 32000:
            length = int(np.ceil(len(signal) * 32000 / rate))
            signal = soxr.resample(signal, rate, 32000, quality='HQ')
            signal = signal[:length] if len(signal) >= length else np.pad(signal, (0, length - len(signal)))
        chunks = []
        for offset in range(0, len(signal), int((3. - overlap) * 32000)):
            chunk = signal[offset:offset + 96000]
            if len(chunk) < 48000:
                break
            if len(chunk) < 96000:
                chunk = np.pad(chunk, (0, 96000 - len(chunk)))
            chunks.append(chunk)
        return {'predictions': self.predict_many(chunks, top_k), 'duration': len(audio) / rate}

    def predict_many(self, chunks, top_k):
        return [self.predict(chunk, top_k) for chunk in chunks]

    def batch(self, body):
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            if len(archive.infolist()) > 101 or sum(i.file_size for i in archive.infolist()) > MAX_BODY:
                raise ValueError('Batch exceeds limits')
            if len(set(archive.namelist())) != len(archive.namelist()):
                raise ValueError('Duplicate ZIP member')
            request = json.loads(archive.read('manifest.json'))
            if request.get('schema') != 1 or request.get('model_sha256') != MODEL_SHA or request.get('labels_sha256') != LABELS_SHA:
                raise ValueError('Incompatible protocol/model/labels')
            overlap = float(request['overlap']); top_k = int(request['top_k'])
            items = request['items']
            if not math.isfinite(overlap) or not 0 <= overlap < 3 or not 1 <= top_k <= 11560 or not 1 <= len(items) <= 100:
                raise ValueError('Invalid batch parameters')
            if set(archive.namelist()) != {'manifest.json'} | {r['member'] for r in items} or len({r['member'] for r in items}) != len(items):
                raise ValueError('Manifest/member mismatch')
            results = []
            with self.lock:
                for item in items:
                    data = archive.read(item['member'])
                    sha = digest(data)
                    if len(data) > 16 * 1024**2 or sha != item['sha256'] or len(data) != item['size']:
                        raise ValueError('Source checksum/size mismatch')
                    cache_key = digest(json.dumps([1, getattr(self,'cache_identity',MODEL_SHA), LABELS_SHA, sha, overlap, top_k]).encode())
                    path = self.cache / (cache_key + '.json')
                    began = time.monotonic()
                    try:
                        if path.exists():
                            result = json.loads(path.read_text(encoding='utf-8')); self.hits += 1
                        else:
                            result = self.analyze(data, overlap, top_k)
                            temp = path.with_suffix('.tmp')
                            temp.write_text(json.dumps(result, allow_nan=False), encoding='utf-8')
                            os.replace(temp, path)
                            self.files += 1
                        results.append(dict(result, member=item['member'], sha256=sha, seconds=time.monotonic()-began))
                    except (ValueError, RuntimeError) as error:
                        results.append({'member':item['member'], 'sha256':sha, 'error':str(error)[:500]})
            return {'schema':1, 'model_sha256':MODEL_SHA, 'labels_sha256':LABELS_SHA,
                    'backend':getattr(self,'backend','tflite-cpu'), 'items':results}


def serve(engine, port, bind='127.0.0.1', allowed_clients=None, addresses=None):
    addresses=set(addresses or [])|{'127.0.0.1'}
    allowed=set(allowed_clients or [])|addresses
    for address in allowed:ipaddress.IPv4Address(address)
    if bind!='127.0.0.1' and not allowed_clients:raise ValueError('LAN binding requires an explicit device allowlist')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            print(json.dumps({'event':'http','message':fmt % args}), flush=True)

        def send(self, code, body):
            data=json.dumps(body, allow_nan=False).encode()
            self.send_response(code); self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)

        def do_GET(self):
            if self.client_address[0] not in allowed:return self.send(403,{'error':'Device is not allowed'})
            if self.path != '/health':return self.send(404, {'error':'Not found'})
            self.send(200, {'ready':True,'model_sha256':MODEL_SHA,'labels_sha256':LABELS_SHA,
                            'backend':getattr(engine,'backend','tflite-cpu'),
                            'addresses':sorted(addresses),
                            'threads':engine.threads,'analyzed_files':engine.files,'cache_hits':engine.hits})

        def do_POST(self):
            if self.client_address[0] not in allowed:return self.send(403,{'error':'Device is not allowed'})
            if self.path != '/v1/analyze':return self.send(404, {'error':'Not found'})
            self.connection.settimeout(600)
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0 < size <= MAX_BODY:return self.send(413, {'error':'Batch exceeds limits'})
                body=self.rfile.read(size)
                if len(body)!=size:raise ValueError('Incomplete request')
                self.send(200, engine.batch(body))
            except (ValueError, KeyError, zipfile.BadZipFile) as error:
                self.send(400, {'error':str(error)[:500]})
            except (BrokenPipeError, ConnectionResetError):pass
            except Exception as error:
                print(json.dumps({'event':'error','type':type(error).__name__}),flush=True)
                self.send(500, {'error':'Analysis service error; retry batch'})
    server=ThreadingHTTPServer((bind,port),Handler)
    print(json.dumps({'event':'ready','bind':bind,'port':port,'allowed_clients':sorted(allowed)}),flush=True)
    server.serve_forever()


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',required=True);parser.add_argument('--labels',required=True)
    parser.add_argument('--cache',required=True);parser.add_argument('--threads',type=int,default=4)
    parser.add_argument('--port',type=int,default=8766)
    parser.add_argument('--bind',default='127.0.0.1');parser.add_argument('--allow-client',action='append',default=[])
    parser.add_argument('--advertise-ip',action='append',default=[])
    args=parser.parse_args()
    if not 1 <= args.threads <= 16:parser.error('threads must be 1..16')
    serve(Engine(args.model,args.labels,args.cache,args.threads),args.port,args.bind,args.allow_client,args.advertise_ip)
