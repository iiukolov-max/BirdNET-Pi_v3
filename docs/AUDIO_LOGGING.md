# Persistent audio diagnostics

Audio capture now keeps `/var/log/birdnet/audio.jsonl` across boots. It records
hardware discovery, missing microphone reasons with a bounded read-only
snapshot, capture/encoder start and exit, USB sound-card add/remove, first
completed segment, signal transitions, and 15-minute aggregate heartbeats.
No inference, capture mode, gain or model setting is changed by the installer.
The existing 15-second RTC snapshot remains; audio is sampled then and again
120 seconds after boot. New timers are preserved by the minimal-services policy.

## Install on an already updated system

After checking out the reviewed commit:

```sh
cd ~/BirdNET-Pi
bash scripts/install_startup_logging.sh
sudo systemctl restart birdnet_recording.service
sudo birdnet-audio-log
sudo birdnet-audio-log --boot BOOT_ID_PREFIX --since 2026-11-01 --json
```

Restart recording only when it is appropriate to interrupt capture; existing
processes pick up the new Python code and supplementary group on next start.
The installer itself does not restart recording. It is idempotent and called
from the existing install/update path. `update_birdnet.sh` still does nothing
when HEAD equals origin/main, so run the installer manually in that case.

## Permissions, rotation and failure behavior

`systemd-tmpfiles` provisions the log as `pi:adm 0640`. The containing directory
is `root:birdnet-audio 0710`; pi joins this dedicated group for traversal only.
pi cannot list or create/replace files there or write any other diagnostics.
The old startup service's LogsDirectory directive is removed so it cannot reset
directory permissions. Existing startup logs retain their own ownership/mode.
Administrative readers use sudo; raw logs are not made available to the web.
Runtime deduplication files live in `/run/birdnet-audio`, not on the SD card.

Each JSON record uses one O_APPEND write, no fsync, no whole-log read. File,
state or snapshot failures are contained; existing recorder console events and
exit codes remain. Serial properties and USB PulseAudio source identifiers are
redacted from persisted JSON. Snapshot commands use a shared 4.5-second budget,
run without sudo, and include errors rather than requiring privileges.

Rotation checks every 15 minutes: `maxsize 256k`, five compressed rotations,
`create 0640 pi adm`. This is deliberately smaller than the suggested 1 MiB:
even incompressible logs stay below approximately 1.6 MiB. Writers stop appending
at 256 KiB until rotation, bounding storage if the timer fails; console output
continues, but persistent events can be lost while the cap is reached.
Rotation uses rename/create, so new opens pick up the correct file permissions.
A concurrent append at the rotation boundary may land in the previous file.

Retries are coalesced across process restarts, keyed by event/reason/card set.
First event includes a snapshot, then `repeated` every ten minutes and a final
pending count before a lifecycle change. The duplicate archive-unavailable notice
and unchanged partial-file notices are kept once per day; the microphone source
provides the ten-minute retry counts. Counts are increments since the prior
summary; first_time anchors the original occurrence. Pending counts in tmpfs
are lost on power failure, while all persisted summaries survive.

Archive mode computes S16_LE RMS/peak in memory using `struct.unpack` and `math.sumprod` (3.11 uses a standard-library fallback), no audioop
or numpy. Digital silence is represented by finite -120 dBFS, not JSON Infinity.
Optional config keys: `AUDIO_QUIET_DBFS=-70`, `AUDIO_HEARTBEAT_SECONDS=900`.
Quiet means low broadband RMS, not absence of birds: hum can mask an otherwise
failed microphone. Heartbeats include segment counts, duration, quiet fraction,
median/max RMS, peak, free space, PCM and card. A final short summary is flushed
on orderly stop. Abrupt power loss can lose up to one heartbeat period of counts.
Normal/RTSP mode logs subprocess lifecycle and return codes but does not measure
levels or produce archive heartbeats. RTSP URLs are never logged by the logger.

The reader includes compressed rotations, filters by boot prefix/date, and warns
about gaps exceeding two heartbeat periods during an archive recording session,
including an ongoing session if recording is active. Confirmed segment counts
come from heartbeats; the first segment provides a lower bound until a summary.
The Overview boot-history UI remains a next step: publish sanitized per-boot
aggregates to its public JSON, rather than granting PHP access to private logs.

## Device acceptance procedure (physical hardware required)

1. On bookworm and trixie with no card, boot, wait 120 seconds, run
   `sudo birdnet-audio-log --json`. Expect `startup`, `microphone_not_found`
   with snapshot, `archive_microphone_unavailable`; after ten minutes expect
   `repeated`. After 24 hours run `sudo wc -c /var/log/birdnet/audio.jsonl` and
   check rotations; missing-card diagnostics should stay below 100 kB/day.
2. Connect USB capture through the intended OTG hub after boot, enable recording
   through the usual service controls. Expect `sound_card_added`,
   `microphone_selected`, `archive_started`, first segment and heartbeat with
   levels. Disconnect while recording: expect `sound_card_removed`,
   `archive_stopped` including code/signal/stderr and retry reason. Reconnect:
   expect added/selected/start/segments without manual code changes.
3. Reboot when no manual analysis is running. Check the previous boot remains
   readable and the reader shows both IDs. Verify the early and 120-second
   snapshots, timers, and `sudo -u pi test ! -w /var/log/birdnet/startup.jsonl`.
4. For rotation test: `sudo logrotate -f /etc/logrotate.d/birdnet-audio-log`;
   check `stat` on current log and trigger discovery as pi. Do not insert fake
   hardware events into the production log.
5. Compare capture CPU before/after on the same microphone/sample rate/channels
   with `pidstat -p PID 1 60` (or cgroup CPUUsageNSec deltas); repeat in similar
   system load. A synthetic PCM benchmark isolates meter cost but is not a full
   recording CPU measurement.

Unit/integration tests use mocked discovery and synthetic subprocesses. They
cannot establish physical USB reconnect reliability, 24-hour storage growth,
or successful recording after a real reboot. Report those results separately.
No journald configuration changes are required.

## Built-in activity LED alarm

`birdnet-audio-led.service` checks capture PCM nodes in sysfs. With no capture
card it replaces ACT's activity trigger with two 150 ms flashes, separated by
150 ms, followed by 1000 ms dark, repeated. At startup it waits 20 seconds for
USB enumeration. Reconnection is detected within approximately 1.45 seconds
while alarming; absence is checked every five seconds while healthy. No mixer,
GPIO wiring, microphone gain, recording state or audio format is changed.

The previous LED trigger is saved once on tmpfs and restored on reconnection or
service stop, including restart recovery after a process crash. Only ACT/act/led0
on a physical sysfs device is selected; virtual LEDs are excluded. `audio_led`
is an additional source for alarm start/clear/error events. Flash transitions
write only sysfs, not the SD card or audio log. The alarm indicates missing
capture hardware, not microphone quality or presence of bird vocalizations.
Disable/restore activity indication with `sudo systemctl disable --now
birdnet-audio-led.service`. No buzzer or speaker is required.

## Audit annotations for synthetic test events

Mocked gain tests patch the durable logger so hardware fixtures never enter the
production log. If an older test run produced synthetic events, a root-created
`diagnostic_test_records_excluded` annotation can identify the exact boot/PID
pairs and synthetic first-event timestamps. The reader excludes those events
and only their derived repeats from summaries. Real repeat summaries flushed
by a test process remain visible. Original JSON lines are preserved, including
rotations; `--include-test-events --json` exposes the complete retained evidence.
This is an explicit correction, not a reconstruction of hardware history.
