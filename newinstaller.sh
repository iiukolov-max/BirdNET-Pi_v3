#!/usr/bin/env bash
set -euo pipefail
# Fresh installations only; never reinstall over user data.
headless=0
case "${1:-}" in
  '') ;;
  --zero2-headless) headless=1 ;;
  *) echo "Usage: $0 [--zero2-headless]" >&2; exit 2 ;;
esac
if [ "$EUID" = 0 ] || [ "$(id -un)" != pi ] || [ "$HOME" != /home/pi ]; then
  echo 'Run as user pi with home /home/pi (required by the unchanged export script).' >&2
  exit 1
fi
target="$HOME/BirdNET-Pi"
if [ -e "$target" ] || [ -L "$target" ] || [ -e /etc/birdnet/birdnet.conf ]; then
  echo 'Existing installation found. Nothing was changed. Use the migration procedure.' >&2
  exit 1
fi
case "$(uname -m)" in
  aarch64|x86_64) ;;
  *) echo 'A 64-bit operating system is required.' >&2; exit 1 ;;
esac
python_version=$(python3 -c 'import sys; print("%s.%s" % sys.version_info[:2])')
case "$python_version" in
  3.11|3.12|3.13) ;;
  *) echo "Unsupported Python: $python_version." >&2; exit 1 ;;
esac
if [ "$headless" = 1 ]; then
  if ! grep -aq 'Raspberry Pi Zero 2' /proc/device-tree/model 2>/dev/null; then
    echo '--zero2-headless is only supported on Raspberry Pi Zero 2 W.' >&2
    exit 1
  fi
  echo 'Selected headless profile disables graphics/camera and CMA; boot files will be backed up.'
fi
sudo -n true 2>/dev/null || sudo -v || { echo 'Sudo access is required.' >&2; exit 1; }
# Keep interactive sudo authentication valid during lengthy package downloads.
# No permanent sudoers policy is installed by this bootstrap.
installer_pid=$$
(
  while kill -0 "$installer_pid" 2>/dev/null; do
    sleep 45
    sudo -n -v || exit
  done
) </dev/null >/dev/null 2>&1 &
sudo_refresh_pid=$!
trap 'kill "$sudo_refresh_pid" 2>/dev/null || true' EXIT
packages=()
for command in git jq; do
  command -v "$command" >/dev/null || packages+=("$command")
done
if [ "${#packages[@]}" -gt 0 ]; then
  sudo apt-get update
  sudo apt-get install -y "${packages[@]}"
fi
release_ref="${BIRDNET_FORK_REF:-main}"
git clone --depth 1 --branch "$release_ref" https://github.com/iiukolov-max/BirdNET-Pi_v3.git "$target"
git -C "$target" config remote.origin.fetch '+refs/heads/main:refs/remotes/origin/main'
export BIRDNET_ZERO2_HEADLESS="$headless"
bash "$target/scripts/install_birdnet.sh"
echo 'Installation steps completed. Reboot, then verify recording, model readiness and the web interface.'
if [ "$headless" = 1 ]; then
  echo 'The headless profile takes effect after reboot; check CmaTotal in /proc/meminfo.'
fi
echo 'No automatic reboot was requested.'
