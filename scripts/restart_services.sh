#!/usr/bin/env bash
# Restarts ALL services and removes ALL unprocessed audio
source /etc/birdnet/birdnet.conf
set -x
my_dir=$HOME/BirdNET-Pi/scripts

if [ -f /usr/local/libexec/birdnet_minimal_services.py ]; then
  sudo /usr/bin/python3 /usr/local/libexec/birdnet_minimal_services.py || exit 1
fi
if [ "${OPERATION_MODE:-normal}" = archive ]; then
  sudo systemctl stop birdnet-archive-analysis.service
  sudo systemctl stop birdnet_analysis.service
  sudo systemctl restart birdnet_recording.service
  exit $?
fi


sudo systemctl stop birdnet_recording.service

services=(chart_viewer.service
  spectrogram_viewer.service
  icecast2.service
  birdnet_recording.service
  birdnet_analysis.service
  birdnet_log.service
  birdnet_stats.service)

for i in  "${services[@]}";do
  sudo systemctl restart "${i}"
done

for i in {1..5}; do
  # We want to loop here (5*5seconds) until the birdnet_analysis.service is running
  systemctl is-active --quiet birdnet_analysis.service \
	  && logger "[$0] birdnet_analysis.service is running" \
	  && break

  sleep 5
done
