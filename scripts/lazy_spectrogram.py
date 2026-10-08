"""Generate one allowed detection image, serialized and cached, as the Pi user."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import time

from utils.helpers import get_settings
from utils.spectrograms import render_spectrogram


def resolve_audio(relative):
    root = Path(get_settings()['EXTRACTED']).resolve()
    parts = relative.lstrip('/').split('/')
    if len(parts) != 4 or parts[0] != 'By_Date' or any(part in ('', '.', '..') for part in parts):
        raise ValueError('Invalid audio path')
    source = root.joinpath(*parts).resolve(strict=True)
    source.relative_to(root / 'By_Date')
    if not source.is_file() or source.suffix.lower() not in ('.flac', '.wav', '.mp3', '.ogg', '.opus'):
        raise ValueError('Invalid audio file')
    output = Path(str(source) + '.png')
    if output.is_symlink():
        raise ValueError('Invalid image path')
    return source, output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('audio')
    args = parser.parse_args()
    source, output = resolve_audio(args.audio)
    if output.is_file() and output.stat().st_size > 0:
        print(json.dumps({'cached': True}))
        return
    if not Path('/etc/birdnet/lazy-spectrograms.enabled').is_file():
        raise RuntimeError('On-demand spectrograms are disabled')
    cache = Path.home() / 'BirdNET-Pi/.cache/lazy-spectrograms'
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (cache / 'generation.lock').open('a') as lock:
        deadline = time.monotonic() + 20
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError('Spectrogram generator busy')
                time.sleep(0.1)
        if not output.is_file() or output.stat().st_size == 0:
            started = time.monotonic()
            render_spectrogram(str(source), source.parent.name.replace('_', ' '),
                               str(source).replace(str(Path.home())+'/', ''), get_settings()['RAW_SPECTROGRAM'])
            print(json.dumps({'cached': False, 'seconds': time.monotonic()-started}))
        else:
            print(json.dumps({'cached': True}))


if __name__ == '__main__':
    main()
