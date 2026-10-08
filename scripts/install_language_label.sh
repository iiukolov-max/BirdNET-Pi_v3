#!/usr/bin/env bash
set -euo pipefail
source /etc/birdnet/birdnet.conf
script=$(readlink -f -- "${BASH_SOURCE[0]}")
root=$(cd -- "$(dirname -- "$script")/.." && pwd)
cd "$root/scripts"
exec "$root/birdnet/bin/python3" -c 'from utils.helpers import set_label_file; set_label_file()'
