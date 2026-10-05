#!/usr/bin/env bash
set -euo pipefail
configuration="${BIRDNET_CONFIG:-/etc/birdnet/birdnet.conf}"
source "$configuration"
script=$(readlink -f -- "${BASH_SOURCE[0]}")
root=$(cd -- "$(dirname -- "$script")/.." && pwd)
owner="${BIRDNET_USER:-pi}"
remote=origin
branch=main
auto_update=0
while getopts ':r:b:a' option; do
  case "$option" in
    r) remote="$OPTARG" ;;
    b) branch="$OPTARG" ;;
    a) auto_update=1 ;;
    *) echo "Usage: $0 [-r origin] [-b main] [-a]" >&2; exit 2 ;;
  esac
done
[ "$remote" = origin ] && [ "$branch" = main ] || { echo 'This release updates from origin/main only.' >&2; exit 1; }
if [ "$auto_update" = 1 ] && [ "${AUTOMATIC_UPDATE:-0}" != 1 ]; then
  echo 'Automatic updates are disabled.'
  exit 0
fi
as_owner() { sudo -u "$owner" "$@"; }
git_owner() { as_owner git -C "$root" "$@"; }
case "$(git_owner config --get remote.origin.url)" in
  https://github.com/iiukolov-max/BirdNET-Pi_v3.git|https://github.com/iiukolov-max/BirdNET-Pi_v3|git@github.com:iiukolov-max/BirdNET-Pi_v3.git) ;;
  *) echo 'Update refused: origin is not iiukolov-max/BirdNET-Pi_v3. Follow the fork migration instructions.' >&2; exit 1 ;;
esac
exec 9>"$root/.release-update.lock"
flock -n 9 || { echo 'Another update is running.' >&2; exit 1; }
if ! git_owner diff --quiet || ! git_owner diff --cached --quiet; then
  echo 'Local tracked code changes found. Update refused; preserve and integrate those changes first.' >&2
  exit 1
fi
git_owner fetch origin '+refs/heads/main:refs/remotes/origin/main'
old_commit=$(git_owner rev-parse HEAD)
new_commit=$(git_owner rev-parse origin/main)
if [ "$old_commit" = "$new_commit" ]; then
  echo 'Already up to date.'
  exit 0
fi
git_owner merge-base --is-ancestor "$old_commit" "$new_commit" || {
  echo 'Local history diverges from origin/main; update refused without changing files.' >&2
  exit 1
}
backup=$(as_owner python3 "$root/scripts/backup_before_update.py" --configuration "$configuration")
echo "Private backup created: $backup"
trap 'echo "Update failed. Inspect the error; backup is at $backup. No user data was deleted." >&2' ERR
# Fast-forward refuses collisions with untracked files. No reset or clean is used.
git_owner merge --ff-only origin/main
as_owner python3 "$root/scripts/download_v3.py"
as_owner "$root/birdnet/bin/python3" -m pip install 'numpy<2; python_version < "3.13"' 'numpy; python_version >= "3.13"' 'soxr==1.0.0'
as_owner python3 "$root/scripts/migrate_review_db.py"
as_owner bash "$root/scripts/install_language_label.sh"
sudo install -d /etc/systemd/system/birdnet_analysis.service.d
printf '[Service]\nEnvironment=OPENBLAS_NUM_THREADS=1\nEnvironment=OMP_NUM_THREADS=1\nEnvironment=MKL_NUM_THREADS=1\nEnvironment=NUMEXPR_NUM_THREADS=1\n' | sudo tee /etc/systemd/system/birdnet_analysis.service.d/35-library-threads.conf >/dev/null
sudo systemctl daemon-reload
# Recording and the audio archive stay in place; reload the inference worker only.
sudo systemctl restart birdnet_analysis.service
sudo systemctl is-active --quiet birdnet_analysis.service
sudo python3 "$root/scripts/check_model_ready.py"
echo 'Code update completed. Verify model readiness and recent detections in the web interface.'
