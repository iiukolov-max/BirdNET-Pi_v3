"""Optional, reversible V3 runtime; other models retain the installed runtime."""
import ctypes
import gc
import hashlib
import importlib
import json
import logging
import os
from pathlib import Path
import platform
import sys

import numpy as np

CONFIG = Path('/etc/birdnet/v3-runtime.json')
log = logging.getLogger(__name__)


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def verified_profile(path=CONFIG):
    if not path.exists():
        return None
    profile = json.loads(path.read_text())
    if not profile.get('enabled'):
        return None
    if platform.machine() != profile['machine'] or list(sys.version_info[:2]) != profile['python']:
        raise ValueError('Optimized V3 runtime does not match this platform')
    for name, expected in profile['artifacts'].items():
        target = Path(name)
        if not target.is_absolute() or digest(target) != expected:
            raise ValueError('Optimized V3 artifact failed verification: ' + name)
    if profile['model'] not in profile['artifacts'] or profile['cache'] not in profile['artifacts']:
        raise ValueError('Optimized V3 model/cache missing from verified artifacts')
    return profile


def allocate(factory, path, threads):
    model = factory(model_path=str(path), num_threads=threads)
    model.resize_tensor_input(model.get_input_details()[0]['index'], [1, 96000])
    model.allocate_tensors()
    return model


def create(original_runtime, original_model, threads):
    previous = os.environ.pop('BIRDNET_RESEARCH_XNNPACK_CACHE', None)
    model = None
    try:
        try:
            profile = verified_profile()
            if profile:
                if profile.get('original_model_sha256') and digest(Path(original_model)) != profile['original_model_sha256']:
                    raise ValueError('Optimized profile does not match the selected original V3 model')
                directory = profile['runtime_dir']
                sys.path.insert(0, directory)
                try:
                    runtime = importlib.import_module('birdnet_tflite_cached.interpreter')
                finally:
                    sys.path.remove(directory)
                os.environ['BIRDNET_RESEARCH_XNNPACK_CACHE'] = profile['cache']
                model = allocate(runtime.Interpreter, profile['model'], threads)
                output = [item for item in model.get_output_details() if list(item['shape']) == [1, 11560]]
                if len(output) != 1:
                    raise ValueError('Optimized V3 output taxonomy mismatch')
                # Verify actual invocation before declaring the optimized runtime ready.
                model.set_tensor(model.get_input_details()[0]['index'],
                                 np.random.default_rng(42).normal(0, .02, (1, 96000)).astype(np.float32))
                model.invoke()
                if not np.isfinite(model.get_tensor(output[0]['index'])).all():
                    raise ValueError('Optimized V3 returned non-finite values')
                ctypes.CDLL(None).malloc_trim(0)
                log.info('V3 optimized runtime ready: FP32 storage, mmap weight cache; threads=%d', threads)
                print(json.dumps({'event':'v3_runtime_ready','profile':'fp32-mmap-cache','threads':threads}),flush=True)
                return model
        except Exception:
            log.exception('Optimized V3 unavailable; reverting to original model/runtime')
            model = None
            gc.collect()
        os.environ.pop('BIRDNET_RESEARCH_XNNPACK_CACHE', None)
        log.info('V3 original runtime/model selected')
        return allocate(original_runtime.Interpreter, original_model, threads)
    finally:
        os.environ.pop('BIRDNET_RESEARCH_XNNPACK_CACHE', None)
        if previous is not None:
            os.environ['BIRDNET_RESEARCH_XNNPACK_CACHE'] = previous
