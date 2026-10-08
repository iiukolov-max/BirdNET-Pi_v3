"""Analyzer-only label cache, invalidated when either source file changes."""
from functools import lru_cache
import os
from .helpers import MODEL_PATH, get_language, get_settings

V3 = 'BirdNET+_V3.0-preview3.1_Global_11K_FP16_pruned'


@lru_cache(maxsize=1)
def _load(language, model, signatures):
    return get_language(language)


def language_names(language):
    model = get_settings()['MODEL']
    paths = [os.path.join(MODEL_PATH, 'l18n', 'labels_' + language + '.json')]
    if model == V3:
        paths.append(os.path.join(MODEL_PATH, 'BirdNET+_V3.0-preview3.1_Global_11K_Labels.csv'))
    signatures = []
    for path in paths:
        stat = os.stat(path)
        signatures.append((path, stat.st_mtime_ns, stat.st_size, stat.st_ino))
    return _load(language, model, tuple(signatures))
