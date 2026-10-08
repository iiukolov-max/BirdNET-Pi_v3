#!/usr/bin/env bash
# Stop processing without deleting recordings or bypassing mode restrictions.
set -euo pipefail
source /etc/birdnet/birdnet.conf
for unit in birdnet-archive-analysis.service birdnet_analysis.service birdnet_recording.service custom_recording.service chart_viewer.service spectrogram_viewer.service; do
  sudo systemctl stop "$unit"
done
