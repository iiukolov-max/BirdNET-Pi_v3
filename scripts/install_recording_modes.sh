#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
sudo /usr/bin/python3 "$root/scripts/install_sqlite_runtime.py"
sudo install -d /etc/systemd/system/birdnet_analysis.service.d /etc/systemd/system/birdnet_recording.service.d
printf '[Unit]\nAfter=sound.target\n' | sudo tee /etc/systemd/system/birdnet_recording.service.d/77-audio-ready.conf >/dev/null
printf '[Service]\nExecCondition=/usr/bin/python3 %s/scripts/operation_mode.py\n' "$root" | sudo tee /etc/systemd/system/birdnet_analysis.service.d/75-operation-mode.conf >/dev/null
printf '[Service]\nExecStop=/usr/bin/python3 %s/scripts/operation_mode.py --stop-recording $MAINPID\n' "$root" | sudo tee /etc/systemd/system/birdnet_recording.service.d/75-archive-stop.conf >/dev/null
printf '[Service]\nNice=-5\nCPUWeight=1000\nIOWeight=1000\nIOSchedulingClass=best-effort\nIOSchedulingPriority=0\n' | sudo tee /etc/systemd/system/birdnet_recording.service.d/76-recording-priority.conf >/dev/null
sudo chmod 755 "$root/scripts/birdnet_recording.sh"
sudo /usr/bin/python3 "$root/scripts/render_archive_unit.py" | sudo tee /etc/systemd/system/birdnet-archive-analysis.service >/dev/null
sudo chmod 644 /etc/systemd/system/birdnet-archive-analysis.service
sudo /usr/bin/python3 "$root/scripts/render_archive_unit.py" --charts | sudo tee /etc/systemd/system/birdnet-archive-charts.service >/dev/null
sudo install -m 755 "$root/scripts/archive_charts.py" /usr/local/libexec/archive_charts.py
sudo install -m 755 "$root/scripts/birdnet_minimal_services.py" /usr/local/libexec/birdnet_minimal_services.py
sudo install -m 755 "$root/scripts/birdnet_service_policy.py" /usr/local/libexec/birdnet_service_policy.py
sudo install -m 644 "$root/scripts/service_policy.json" /usr/local/libexec/service_policy.json
sudo /usr/bin/python3 /usr/local/libexec/birdnet_service_policy.py install
sudo install -m 644 "$root/templates/birdnet-minimal-services.service" /etc/systemd/system/birdnet-minimal-services.service
sudo install -m 755 "$root/scripts/economy_cpu_policy.py" /usr/local/libexec/economy_cpu_policy.py
sudo install -m 644 "$root/templates/birdnet-cpu-policy.service" /etc/systemd/system/birdnet-cpu-policy.service
sudo systemctl daemon-reload
sudo systemctl enable birdnet-minimal-services.service
sudo systemctl enable --now birdnet-cpu-policy.service
sudo systemctl disable birdnet-archive-analysis.service
