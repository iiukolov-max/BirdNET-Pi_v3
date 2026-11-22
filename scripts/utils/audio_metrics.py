"""Incremental S16_LE level measurements; no audioop/numpy and no file reread."""
import operator
import struct
from collections import deque
import math
import statistics
import threading
import time


def dbfs(value):
    # Finite floor keeps JSON interoperable for digital silence.
    return max(-120.0, 20 * math.log10(value / 32768)) if value else -120.0


class Levels:
    def __init__(self):
        self.count = self.squares = self.peak = 0
        self.pending = b''

    def update(self, data):
        data = self.pending + data
        end = len(data) & ~1
        self.pending = data[end:]
        samples = struct.unpack('<' + str(end // 2) + 'h', data[:end])
        self.count += len(samples)
        self.squares += (math.sumprod(samples, samples) if hasattr(math, 'sumprod')
                         else sum(map(operator.mul, samples, samples)))
        if samples:
            self.peak = max(self.peak, abs(min(samples)), abs(max(samples)))

    def result(self):
        return {'rms_dbfs': dbfs(math.sqrt(self.squares / self.count)) if self.count else -120.0,
                'peak_dbfs': dbfs(self.peak)}


class Period:
    def __init__(self, interval=900, quiet_dbfs=-70, clock=time.monotonic):
        self.interval, self.quiet_dbfs, self.clock = interval, quiet_dbfs, clock
        self.started = clock()
        self.rms = []
        self.quiet = 0
        self.seconds = 0
        self.peak = -120.0
        self.last_segment = None
        self.was_quiet = None

    def add(self, levels, duration, stamp):
        quiet = levels['rms_dbfs'] < self.quiet_dbfs
        changed = self.was_quiet is None or self.was_quiet != quiet
        self.was_quiet = quiet
        self.rms.append(levels['rms_dbfs'])
        self.quiet += quiet
        self.seconds += duration
        self.peak = max(self.peak, levels['peak_dbfs'])
        self.last_segment = stamp
        return ('audio_quiet' if quiet else 'audio_signal_present') if changed else None

    def summary(self, force=False):
        if not self.rms or (not force and self.clock() - self.started < self.interval):
            return None
        result = {'segments': len(self.rms), 'audio_seconds': self.seconds,
                  'quiet_fraction': self.quiet / len(self.rms),
                  'rms_median_dbfs': statistics.median(self.rms), 'rms_max_dbfs': max(self.rms),
                  'peak_dbfs': self.peak, 'last_segment_time': self.last_segment,
                  'period_seconds': self.clock() - self.started, 'interval_seconds': self.interval}
        self.rms.clear()
        self.quiet = 0
        self.seconds = 0
        self.peak = -120.0
        self.started = self.clock()
        return result


class StderrTail:
    """Continuously drain child stderr; bounded memory even without newlines."""
    def __init__(self, pipe):
        self.pipe = pipe
        self.chunks = deque(maxlen=8)
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self):
        try:
            while True:
                chunk = self.pipe.read(512)
                if not chunk:
                    break
                self.chunks.append(chunk)
                try:
                    sys.stderr.buffer.write(chunk)
                    sys.stderr.buffer.flush()
                except Exception:
                    pass
        except (OSError, ValueError):
            pass

    def text(self):
        self.thread.join(timeout=.1)
        return b''.join(self.chunks).decode('utf-8', errors='replace')[-4096:]
