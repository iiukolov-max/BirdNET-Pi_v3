#!/usr/bin/env python3
"""Two short ACT flashes, then one second dark, while capture hardware is absent."""
import argparse
import json
from pathlib import Path
import re
import signal
import threading
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.audio_log import emit

STATE = Path('/run/birdnet-audio-root/led-state.json')


def capture_present(sound=Path('/sys/class/sound')):
    # Capture PCM nodes, not playback-only cards, and no arecord subprocess.
    return any(sound.glob('pcmC*D*c'))


def choose_led(root=Path('/sys/class/leds')):
    for name in ('ACT', 'act', 'led0'):
        led = root / name
        if (led / 'trigger').is_file() and 'virtual' not in str(led.resolve()):
            return led
    return None


class Alert:
    def __init__(self, led, state=STATE):
        self.led, self.state = led, state
        self.saved = None
        if state.exists():
            saved = json.loads(state.read_text())
            if saved.get('led') != str(led):
                raise ValueError('Saved LED differs from selected LED')
            self.saved = saved

    def start(self):
        if self.saved is not None:
            return
        if self.state.exists():
            saved = json.loads(self.state.read_text())
            if saved.get('led') != str(self.led):
                raise ValueError('Saved LED differs; restore it before selecting another LED')
        else:
            trigger = re.search(r'\[([^]]+)\]', (self.led / 'trigger').read_text())
            if not trigger:
                raise ValueError('Cannot determine original LED trigger')
            saved = {'led': str(self.led), 'trigger': trigger[1],
                     'brightness': (self.led / 'brightness').read_text().strip()}
            if trigger[1] == 'timer':
                saved.update(delay_on=(self.led / 'delay_on').read_text().strip(),
                             delay_off=(self.led / 'delay_off').read_text().strip())
            self.state.write_text(json.dumps(saved))
        self.saved = saved
        (self.led / 'trigger').write_text('none')

    def pulse_pair(self, stop):
        maximum = (self.led / 'max_brightness').read_text().strip()
        for value, seconds in ((maximum,.15),('0',.15),(maximum,.15),('0',1.0)):
            (self.led / 'brightness').write_text(value)
            if stop.wait(seconds):
                return

    def restore(self):
        if self.saved is None:
            return
        saved = self.saved
        (self.led / 'trigger').write_text(saved['trigger'])
        if saved['trigger'] == 'none':
            maximum = int((self.led / 'max_brightness').read_text())
            (self.led / 'brightness').write_text(str(min(maximum, int(saved['brightness']))))
        if saved['trigger'] == 'timer':
            (self.led / 'delay_on').write_text(saved['delay_on'])
            (self.led / 'delay_off').write_text(saved['delay_off'])
        self.state.unlink(missing_ok=True)
        self.saved = None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--grace-seconds', type=float, default=20)
    args = parser.parse_args()
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    led = choose_led()
    if led is None:
        emit('audio_led_unavailable', 'audio_led', console=True)
        return 0
    alert = Alert(led)
    alarm = False
    try:
        stop.wait(args.grace_seconds)
        while not stop.is_set():
            missing = not capture_present()
            if missing:
                alert.start()
                if not alarm:
                    emit('audio_led_alert_started', 'audio_led', console=True,
                         pattern_ms=[150,150,150,1000], led=led.name, reason='no capture card')
                    alarm = True
                alert.pulse_pair(stop)
            else:
                alert.restore()
                if alarm:
                    emit('audio_led_alert_cleared', 'audio_led', console=True, led=led.name)
                    alarm = False
                stop.wait(5)
    except (OSError, ValueError) as error:
        emit('audio_led_error', 'audio_led', console=True, reason=str(error))
        return 1
    finally:
        try:
            alert.restore()
        except (OSError, ValueError) as error:
            emit('audio_led_restore_failed', 'audio_led', console=True, reason=str(error))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
