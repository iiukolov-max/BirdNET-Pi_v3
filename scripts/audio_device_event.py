#!/usr/bin/env python3
"""Short udev callback; inventory uses sysfs only, never starts services."""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.audio_log import emit, read
from utils.audio_snapshot import card_info


def main():
    action = os.environ.get('ACTION')
    name = os.environ.get('KERNEL', Path(os.environ.get('DEVPATH', '')).name)
    if action not in ('add', 'remove') or not name.startswith('card') or not name[4:].isdigit():
        return
    fields = card_info(name[4:]) if action == 'add' else {'number': name[4:]}
    # udev properties remain available on removal even if sysfs is already gone.
    fields['name'] = os.environ.get('ID_MODEL_FROM_DATABASE', os.environ.get('ID_MODEL', fields.get('name', name)))
    vendor, product = os.environ.get('ID_VENDOR_ID'), os.environ.get('ID_MODEL_ID')
    if vendor and product:
        fields['usb_id'] = vendor + ':' + product
    cache = Path('/run/birdnet-audio-root') / ('card-' + name[4:] + '.json')
    try:
        import json
        if action == 'add':
            cache.write_text(json.dumps(fields))
        elif cache.exists():
            fields = {**json.loads(cache.read_text()), **{k: v for k, v in fields.items() if v != name}}
            cache.unlink()
    except (OSError, ValueError):
        pass
    emit('sound_card_added' if action == 'add' else 'sound_card_removed', 'udev', console=True, **fields)


if __name__ == '__main__':
    main()
