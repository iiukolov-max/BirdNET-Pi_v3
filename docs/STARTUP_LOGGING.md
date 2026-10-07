# Current system time, RTC and boot logging

New installations enable `birdnet-startup-log.timer`. It records a snapshot two
minutes after each boot, once per boot, in `/var/log/birdnet/startup.jsonl`
and the system journal. Logs rotate daily or at 5 MiB when logrotate runs,
retaining fourteen compressed files.

Read the latest snapshot:

```bash
sudo tail -n 1 /var/log/birdnet/startup.jsonl | python3 -m json.tool
sudo journalctl -u birdnet-startup-log.service -b
sudo tail -f /var/log/birdnet/startup.jsonl
```

Run a fresh check without writing a file:

```bash
sudo python3 /usr/local/bin/startup_diagnostics.py | python3 -m json.tool
```

Records include boot ID, UTC/local observation time, uptime, estimated boot time,
NTP synchronisation and the start times, states and restart counts of analysis,
recording and Caddy. Monotonic start times are seconds after boot and remain
meaningful across clock corrections. An active analysis service does not establish
that the model is ready or that a recording was processed. The two-minute snapshot
is a fixed observation point, not a measurement of inference readiness.

`observed_at_local` is current system time with its timezone offset;
`observed_at_utc` is the same time in UTC. `rtc_detected_by_kernel` explicitly
reports whether an RTC was detected. Each device has its own `date` and `time`
from sysfs; `rtc_read.output` contains `hwclock --show` time with timezone offset.
The system and RTC are read sequentially, so their samples can differ slightly.
If reading fails, `rtc_read.error` reports the failure, separately from detection.

RTC entries include kernel device/name/driver, RTC date/time, `hctosys` and the
result of reading `hwclock`. `hctosys=1` means that RTC supplied system time at boot.
Kernel detection does not prove battery health. An attached board without its
driver/device-tree configuration may be absent from this report. A detected RTC
may be built into the Pi rather than an external board. No I2C bus scan, clock
write or automatic driver configuration is performed. Before RTC/NTP establishes
correct time, wall-clock timestamps and estimated boot time may be inaccurate;
boot ID and uptime still identify the boot.

For an existing installation, after updating source code, install the timer with:

```bash
bash /home/pi/BirdNET-Pi/scripts/install_startup_logging.sh
```

## Microphone at recording startup

Before local recording, `prepare_microphone.py` discovers ALSA capture hardware.
With `REC_CARD=default`, an empty value or `auto`, it prefers USB and selects its
PulseAudio input as the shared capture source for recording and live streaming.
The standalone helper without `--pulse` prints a stable `plughw:CARD=...,DEV=...`
device name for direct ALSA use. An explicit `hw` or
`plughw` selection is retained. Other custom PCM names are retained without
guessing their underlying hardware mixer. RTSP recording skips hardware setup.

Only controls advertising capture volume or capture switch capabilities are
changed: capture level is set to 100% and capture is unmuted. Playback controls
are left alone. Some microphones have fixed gain; their lack of adjustable
controls is logged and recording continues. Hardware maximum gain is distinct
from BirdNET's model sensitivity setting. The recording service retries if a
microphone is absent, including when it is connected after boot.

Inspect detection and mixer results:

```bash
sudo journalctl -u birdnet_recording.service -b
```
