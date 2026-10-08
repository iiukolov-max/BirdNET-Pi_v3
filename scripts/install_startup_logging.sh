#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")/.." && pwd)
sudo ln -sfn "$root/scripts/startup_diagnostics.py" /usr/local/bin/startup_diagnostics.py
sudo install -m 0755 "$root/scripts/read_boot_log.py" /usr/local/bin/birdnet-boot-log
sudo ln -sfn "$root/scripts/prepare_microphone.py" /usr/local/bin/prepare_microphone.py
sudo install -m 0644 "$root/templates/birdnet-startup-log.service" /etc/systemd/system/birdnet-startup-log.service
sudo install -m 0644 "$root/templates/birdnet-startup-log.timer" /etc/systemd/system/birdnet-startup-log.timer
sudo install -d -m 0755 /etc/logrotate.d
sudo install -m 0644 "$root/templates/birdnet-startup-log.logrotate" /etc/logrotate.d/birdnet-startup-log
sudo systemctl daemon-reload
sudo systemctl enable --now birdnet-startup-log.timer
