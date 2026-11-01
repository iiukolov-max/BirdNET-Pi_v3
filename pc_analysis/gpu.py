"""CUDA backend for the official V3 Preview 3.1 ONNX export."""
import argparse,csv,hashlib,threading,time,os,sys,ctypes
from pathlib import Path
from server import Engine,serve,digest,LABELS_SHA

ONNX_SHA='69cfc8db3ebec163feb6329e546eb56e1aadac2a309f1ee99aecfabd1aa9bd24'

class GPUEngine(Engine):
    def __init__(self, model, labels, cache, threads=4, profile=False):
        import numpy as np
        import onnxruntime as ort
        if digest(Path(model).read_bytes())!=ONNX_SHA or digest(Path(labels).read_bytes())!=LABELS_SHA:
            raise ValueError('Official ONNX model or labels checksum mismatch')
        with open(labels,encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f,delimiter=';'))
        if len(rows)!=11560 or any(int(r['idx'])!=i for i,r in enumerate(rows)):raise ValueError('Taxonomy mismatch')
        self.labels=[r['sci_name'] for r in rows];self.np=np
        self.cache=Path(cache);self.cache.mkdir(parents=True,exist_ok=True)
        self.lock=threading.Lock();self.started=time.time();self.files=0;self.hits=0;self.threads=threads
        self.dll_handles=[]
        if os.name=='nt':
            bins=list((Path(sys.prefix)/'Lib/site-packages/nvidia').glob('*/bin'))
            self.dll_handles=[os.add_dll_directory(str(p)) for p in bins]
            os.environ['PATH']=os.pathsep.join(str(p) for p in bins)+os.pathsep+os.environ.get('PATH','')
            nvrtc=next((p/'nvrtc64_120_0.dll' for p in bins if (p/'nvrtc64_120_0.dll').exists()),None)
            if nvrtc is not None:self.nvrtc=ctypes.WinDLL(str(nvrtc))
        ort.preload_dlls(directory='')
        options=ort.SessionOptions();options.intra_op_num_threads=threads
        if profile:
            options.enable_profiling=True
            options.profile_file_prefix=str(self.cache.parent/'cuda-profile')
        self.model=ort.InferenceSession(str(model),sess_options=options,
            providers=[('CUDAExecutionProvider',{'cudnn_conv_algo_search':'HEURISTIC','use_tf32':'1'})])
        if 'CUDAExecutionProvider' not in self.model.get_providers():raise RuntimeError('CUDA initialization failed; refusing silent CPU fallback')
        self.backend='onnx-cuda';self.cache_identity=['onnx-cuda',ONNX_SHA,ort.__version__]
        self.input=self.model.get_inputs()[0].name
        self.dtype=np.float16 if 'float16' in self.model.get_inputs()[0].type else np.float32
        self.output=next(o.name for o in self.model.get_outputs() if o.shape[-1]==11560)
        print('CUDA_PROVIDERS',self.model.get_providers(),'INPUT',self.model.get_inputs()[0].shape,self.model.get_inputs()[0].type,flush=True)
        self.predict_many([np.random.default_rng(42).normal(0,.02,96000).astype('float32')],10)

    def predict_many(self,chunks,top_k):
        np=self.np
        result=[[[name,0.] for name in self.labels[:top_k]] for _ in chunks]
        active=[i for i,c in enumerate(chunks) if np.any(c)]
        for offset in range(0,len(active),16):
            indices=active[offset:offset+16]
            batch=np.stack([chunks[i] for i in indices]).astype(self.dtype)
            values=self.model.run([self.output],{self.input:batch})[0].astype('float32')
            if values.shape!=(len(indices),11560) or not np.isfinite(values).all():raise ValueError('Invalid CUDA model output')
            for i,row in zip(indices,values):
                ranked=np.argsort(-row,kind='stable')[:top_k]
                result[i]=[[self.labels[j],float(row[j])] for j in ranked]
        return result

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',required=True);parser.add_argument('--labels',required=True)
    parser.add_argument('--cache',required=True);parser.add_argument('--port',type=int,default=8767)
    parser.add_argument('--bind',default='127.0.0.1');parser.add_argument('--allow-client',action='append',default=[])
    parser.add_argument('--advertise-ip',action='append',default=[])
    args=parser.parse_args()
    serve(GPUEngine(args.model,args.labels,args.cache),args.port,args.bind,args.allow_client,args.advertise_ip)
