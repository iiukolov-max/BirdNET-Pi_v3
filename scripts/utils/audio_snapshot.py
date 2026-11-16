"""Bounded read-only audio inventory; intentionally never reads USB serials."""
from pathlib import Path
import re
import subprocess
import time


def read(path):
    try:
        return Path(path).read_text().strip()[:4096]
    except (OSError, UnicodeError) as error:
        return str(error)


def card_info(number):
    path = Path('/sys/class/sound/card' + str(number)).resolve()
    result = {'number': number, 'sys_path': str(path)}
    for parent in [path, *path.parents]:
        if (parent / 'idVendor').is_file() and (parent / 'idProduct').is_file():
            result.update(usb_id=read(parent / 'idVendor') + ':' + read(parent / 'idProduct'),
                          name=read(parent / 'product'), bus_speed=read(parent / 'speed'))
            break
    return result


def snapshot(pulse=False):
    deadline = time.monotonic() + 4.5
    def command(args):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return {'error': 'snapshot deadline exceeded'}
        try:
            p = subprocess.run(args, capture_output=True, text=True, timeout=min(.65, remaining))
            output = p.stdout
            if args[0] == 'dmesg':
                output = '\n'.join(line for line in output.splitlines()
                                   if re.search(r'usb|snd|audio|xhci|dwc', line, re.I)
                                   and not re.search(r'serial', line, re.I))
                output = '\n'.join(output.splitlines()[-20:])
            return {'exit_code': p.returncode, 'output': output[:4096], 'error': p.stderr[:1024]}
        except (OSError, subprocess.TimeoutExpired) as error:
            return {'error': str(error)[:1024]}
    result = {'cards': read('/proc/asound/cards'), 'arecord': command(['arecord', '-l']),
              'lsusb': command(['lsusb']),
              'usb_audio': [card_info(p.name[4:]) for p in Path('/sys/class/sound').glob('card[0-9]*')],
              'kernel': command(['dmesg', '--color=never']),
              'power': command(['vcgencmd', 'get_throttled'])}
    if pulse:
        result['pulse_sources'] = command(['pactl', 'list', 'short', 'sources'])
        result['pulse_check'] = command(['pulseaudio', '--check'])
    return result
