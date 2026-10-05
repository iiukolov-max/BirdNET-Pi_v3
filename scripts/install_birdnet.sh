#!/usr/bin/env bash
# Install BirdNET script
set +x # Do not trace private configuration into the installation log.
exec > >(tee -i installation-$(date +%F).txt) 2>&1 # Make log
set -e # exit installation if anything fails

my_dir=$HOME/BirdNET-Pi
export my_dir=$my_dir

cd $my_dir/scripts || exit 1
git log -n 1 --pretty=oneline --no-color --decorate

source install_helpers.sh

if [ "$(uname -m)" != "aarch64" ] && [ "$(uname -m)" != "x86_64" ];then
  echo "BirdNET-Pi requires a 64-bit OS.
It looks like your operating system is using $(uname -m),
but would need to be aarch64."
  exit 1
fi

#Install/Configure /etc/birdnet/birdnet.conf
./install_config.sh || exit 1
sudo -E HOME=$HOME USER=$USER ./install_services.sh || exit 1
source /etc/birdnet/birdnet.conf

install_birdnet() {
  TMP_SIZE=$(df --output=avail /tmp | tail -n 1)
  if [[ $TMP_SIZE -lt 300000 ]]; then
    mkdir -p $HOME/bird_tmp
    export TMPDIR=$HOME/bird_tmp
  fi
  cd ~/BirdNET-Pi || exit 1
  echo "Establishing a python virtual environment"
  python3 -m venv birdnet
  source ./birdnet/bin/activate
  pip3 install wheel
  get_tf_whl || exit 1
  LOOP_COUNT=2
  while ! pip3 install -U -r ./requirements_custom.txt
  do
    LOOP_COUNT=$(( LOOP_COUNT - 1 ))
    pip3 cache purge
    [ $LOOP_COUNT == 0 ] && exit 1
    sleep 5
  done
  rm -rf $HOME/bird_tmp
}

[ -d ${RECS_DIR} ] || mkdir -p ${RECS_DIR} &> /dev/null

install_birdnet

cd $my_dir/scripts || exit 1

# tzlocal.get_localzone() will fail if the Debian specific /etc/timezone is not in sync
CURRENT_TIMEZONE=$(timedatectl show --value --property=Timezone)
[ -f /etc/timezone ] && echo "$CURRENT_TIMEZONE" | sudo tee /etc/timezone > /dev/null

# Model artifacts are pinned separately from application source code.
python3 "$my_dir/scripts/download_v3.py" || exit 1
./install_language_label.sh || exit 1
python3 "$my_dir/scripts/migrate_review_db.py" || exit 1
sudo install -d /etc/systemd/system/birdnet_analysis.service.d
printf '[Service]\nEnvironment=OPENBLAS_NUM_THREADS=1\nEnvironment=OMP_NUM_THREADS=1\nEnvironment=MKL_NUM_THREADS=1\nEnvironment=NUMEXPR_NUM_THREADS=1\n' | sudo tee /etc/systemd/system/birdnet_analysis.service.d/35-library-threads.conf >/dev/null
sudo systemctl daemon-reload
if [ "${BIRDNET_ZERO2_HEADLESS:-0}" = 1 ]; then
  sudo python3 "$my_dir/scripts/zero2_headless.py" --apply || exit 1
fi

exit 0
