#!/usr/bin/env bash
# This script removes all data that has been collected. It is tantamount to
# starting all data-collection from scratch. Only run this if you are sure
# you are okay will losing all the data that you've collected and processed
# so far.
set -x
source /etc/birdnet/birdnet.conf
USER=${BIRDNET_USER}
HOME=/home/${BIRDNET_USER}
my_dir=${HOME}/BirdNET-Pi/scripts
# Serialize against Settings and the manual-analysis start button until done.
exec 9>/run/lock/birdnet-model-switch.lock
flock -n 9 || { echo 'Another settings, analysis-start or cleanup operation is running.' >&2; exit 1; }

echo "Stopping services"
if systemctl cat birdnet-archive-analysis.service >/dev/null 2>&1; then
  # Prevent ExecStopPost from restarting microphone capture during deletion.
  sudo /usr/bin/python3 "$my_dir/archive_recording_pause.py" cancel || exit 1
  sudo systemctl stop birdnet-archive-analysis.service || exit 1
fi
sudo systemctl stop birdnet_recording.service || exit 1
sudo systemctl stop birdnet_analysis.service || exit 1
for unit in birdnet-archive-analysis.service birdnet_recording.service birdnet_analysis.service; do
  state=$(systemctl show "$unit" -p ActiveState --value) || exit 1
  case "$state" in
    inactive|failed|'') ;;
    *) echo "Cannot clear data while $unit is $state." >&2; exit 1 ;;
  esac
done
echo "Removing all data . . . "
sudo rm -drf "${RECS_DIR}"
sudo rm -f "${IDFILE}"
sudo rm -f $(dirname ${my_dir})/BirdDB.txt

echo "Re-creating necessary directories"
[ -d ${EXTRACTED} ] || sudo -u ${USER} mkdir -p ${EXTRACTED}
[ -d ${EXTRACTED}/By_Date ] || sudo -u ${USER} mkdir -p ${EXTRACTED}/By_Date
[ -d ${EXTRACTED}/Charts ] || sudo -u ${USER} mkdir -p ${EXTRACTED}/Charts
[ -d ${PROCESSED} ] || sudo -u ${USER} mkdir -p ${PROCESSED}

sudo -u ${USER} ln -fs $(dirname $my_dir)/exclude_species_list.txt $my_dir
sudo -u ${USER} ln -fs $(dirname $my_dir)/confirmed_species_list.txt $my_dir
sudo -u ${USER} ln -fs $(dirname $my_dir)/include_species_list.txt $my_dir
sudo -u ${USER} ln -fs $(dirname $my_dir)/whitelist_species_list.txt $my_dir
sudo -u ${USER} ln -fs $(dirname $my_dir)/homepage/* ${EXTRACTED}
sudo -u ${USER} ln -fs $(dirname $my_dir)/model/labels.txt ${my_dir}
sudo -u ${USER} ln -fs $my_dir ${EXTRACTED}
sudo -u ${USER} ln -fs $my_dir/play.php ${EXTRACTED}
sudo -u ${USER} ln -fs $my_dir/spectrogram.php ${EXTRACTED}
sudo -u ${USER} ln -fs $my_dir/overview.php ${EXTRACTED}
sudo -u ${USER} ln -fs $my_dir/stats.php ${EXTRACTED}
sudo -u ${USER} ln -fs $my_dir/todays_detections.php ${EXTRACTED}
sudo -u ${USER} ln -fs $my_dir/history.php ${EXTRACTED}
sudo -u ${USER} ln -fs $my_dir/weekly_report.php ${EXTRACTED}
sudo -u ${USER} ln -fs $my_dir/homepage/images/favicon.ico ${EXTRACTED}
sudo -u ${USER} ln -fs ${HOME}/phpsysinfo ${EXTRACTED}
sudo -u ${USER} ln -fs $(dirname $my_dir)/templates/phpsysinfo.ini ${HOME}/phpsysinfo/
sudo -u ${USER} ln -fs $(dirname $my_dir)/templates/green_bootstrap.css ${HOME}/phpsysinfo/templates/
sudo -u ${USER} ln -fs $(dirname $my_dir)/templates/index_bootstrap.html ${HOME}/phpsysinfo/templates/html
chmod -R g+rw $my_dir
chmod -R g+rw ${RECS_DIR}


echo "Ensuring database schema exists; existing detections are preserved"
createdb.sh
echo "Re-generating BirdDB.txt"
touch $(dirname ${my_dir})/BirdDB.txt
echo "Date;Time;Sci_Name;Com_Name;Confidence;Lat;Lon;Cutoff;Week;Sens;Overlap" > $(dirname ${my_dir})/BirdDB.txt
ln -sf $(dirname ${my_dir})/BirdDB.txt ${my_dir}/BirdDB.txt
chown $USER:$USER ${my_dir}/BirdDB.txt && chmod g+rw ${my_dir}/BirdDB.txt
echo "Restarting services"
restart_services.sh
