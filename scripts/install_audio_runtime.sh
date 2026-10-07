#!/usr/bin/env bash
set -euo pipefail
source /etc/birdnet/birdnet.conf
owner="${BIRDNET_USER:-pi}"
audio_uid=$(id -u "$owner")
sudo loginctl enable-linger "$owner"
for unit in birdnet_recording livestream; do
  sudo install -d "/etc/systemd/system/$unit.service.d"
  {
    printf '[Unit]\nWants=user@%s.service\nAfter=user@%s.service\n' "$audio_uid" "$audio_uid"
    if [ "$unit" = livestream ]; then
      printf 'Requires=icecast2.service\nAfter=icecast2.service birdnet_recording.service\n'
    fi
    printf '[Service]\nEnvironment=XDG_RUNTIME_DIR=/run/user/%s\nEnvironment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/%s/bus\n' "$audio_uid" "$audio_uid"
  } | sudo tee "/etc/systemd/system/$unit.service.d/30-user-audio.conf" >/dev/null
done
sudo systemctl daemon-reload
