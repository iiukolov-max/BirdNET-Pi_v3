#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")/.." && pwd)
# A dedicated group grants traversal only, with write access to audio.jsonl
# through file ownership. pi cannot replace files or write other diagnostics.
getent group birdnet-audio >/dev/null || sudo groupadd --system birdnet-audio
sudo usermod -a -G birdnet-audio pi
sudo install -d -m 0755 /etc/tmpfiles.d /etc/udev/rules.d /usr/local/libexec
sudo install -m 0644 "$root/templates/birdnet-audio-log.tmpfiles" /etc/tmpfiles.d/birdnet-audio-log.conf
sudo systemd-tmpfiles --create /etc/tmpfiles.d/birdnet-audio-log.conf
sudo install -m 0644 "$root/templates/birdnet-audio-log.logrotate" /etc/logrotate.d/birdnet-audio-log
sudo ln -sfn "$root/scripts/audio_device_event.py" /usr/local/libexec/birdnet-audio-device-event.py
sudo ln -sfn "$root/scripts/audio_startup.py" /usr/local/libexec/birdnet-audio-startup.py
sudo ln -sfn "$root/scripts/read_audio_log.py" /usr/local/bin/birdnet-audio-log
sudo ln -sfn "$root/scripts/audio_led_alert.py" /usr/local/libexec/birdnet-audio-led.py
sudo install -m 0644 "$root/templates/80-birdnet-audio.rules" /etc/udev/rules.d/80-birdnet-audio.rules
for name in birdnet-audio-led.service birdnet-audio-late.service birdnet-audio-late.timer birdnet-audio-rotate.service birdnet-audio-rotate.timer; do
    sudo install -m 0644 "$root/templates/$name" "/etc/systemd/system/$name"
done
sudo systemctl daemon-reload
sudo udevadm control --reload-rules
sudo systemctl enable --now birdnet-audio-led.service birdnet-audio-late.timer birdnet-audio-rotate.timer
# Does not restart recording or change capture/gain/model settings.
