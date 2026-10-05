#!/usr/bin/env bash
set -euo pipefail
source /etc/birdnet/birdnet.conf
root="/home/${BIRDNET_USER:-pi}/BirdNET-Pi"
cd "$root/scripts"
exec "$root/birdnet/bin/python3" -c 'from utils.helpers import set_label_file; set_label_file()'
