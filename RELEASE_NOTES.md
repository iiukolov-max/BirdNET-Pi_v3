# BirdNET-Pi V3 — Preview 3

Released: 2026-10-08. This preview combines the accepted Orange Pi contribution with recording, analysis, settings and Overview changes.

## Orange Pi contribution

Merged [PR #1: Add orangepi support](https://github.com/iiukolov-max/BirdNET-Pi_v3/pull/1) by [miketimofeev](https://github.com/miketimofeev). Orange Pi hardware testing was performed by the contributor, as confirmed by the project owner. Installation paths and account handling no longer require the username `pi`. Thank you for the contribution and testing.

Our regression and reboot checks were performed on Raspberry Pi. Additional Preview 3 recording-mode and service-policy features have not been hardware-tested by us on Orange Pi. The Zero 2 W headless profile remains Raspberry Pi-specific.

## Recording and analysis

- Normal mode records and analyzes automatically. Economy retains complete audio for manual analysis from Overview, using the selected recording length and format.
- Manual analysis pauses microphone recording before loading the model and restores it after completion, error or cancellation. An Economy reboot starts recording and leaves both analyzers stopped.
- Economy CPU control uses a reduced recording profile and increases available CPU capacity for analysis, with temperature-based limits. Normal restores the original CPU policy.
- Archive decoding uses SoundFile with FFmpeg fallback; labels are cached and unnecessary notification imports deferred. Two inference threads and the full V3 model are retained.
- Queue counts distinguish files in the current run from later arrivals. Progress, speed and finish estimates reset for a new run and reflect processing rather than stale model-loading data.
- Space-before-cleanup estimates account for current recording settings, measured recording sizes and the configured disk-use threshold. Cleanup removes the oldest complete recordings in batches.

## Settings and services

- A separate Services block below Model controls optional live audio, statistics, charts, spectrogram generation, logs and terminal services.
- Permissions apply to settings changes, mode transitions, direct service starts and reboots. Recording and analysis cannot be unchecked; their activity follows the selected mode.
- Fresh-install defaults are Normal, acoustic V3, geographic V3.0.4 and all optional permissions enabled. Existing settings are preserved.
- Geographic V3 filtering matches names and uses the 48-period seasonal calendar. Earlier geographic filtering and Off remain selectable for V3.
- Settings save in the background, restart affected services selectively and roll back failed mode/model transactions. Unchanged saves preserve ongoing recording and manual analysis.
- Tools → Services separates automatic BirdNET Analysis from manual Archive Analysis. The archive explanation is centered.
- Clear all data stops recording and analysis before deleting audio and spectrogram data; the database and settings are retained.

## Overview and diagnostics

- Reworked layout with week/month detection and species counts, including verified species across all animal labels.
- Two compact lists show the ten most recently introduced species over all time and in the current month, including last encounter and confidence. Links open the corresponding recording's spectrogram.
- Five recent detections remain below the main lists. Redundant latest-detection and currently-analyzing cards and spectra were removed.
- Recent boots always shows three entries with date, time and RTC presence, in both modes. The terminal boot history remains available through `sudo birdnet-boot-log`.
- Spectrograms can be generated on demand and cached; unchanged recent-detection players are preserved during page updates.
- The top-left project link points to this fork. V3 limitations sit alongside the older model descriptions in Settings.

## Validation

On Raspberry Pi Zero 2 W: real mode transitions and reboots in Normal and Economy, new microphone FLAC recordings, completed automatic analysis, optional services remaining disabled, CPU policy and no reported throttling during the recorded checks. The service-policy validation passed 37 Python regression checks plus PHP syntax/table checks before the final path-renderer addition; final release checks are recorded separately.

A live archive run completed 60 of 60 thirty-second FLAC files without failures, averaging about 18.1 seconds per file after warm-up (approximately 3.3 files/minute). Hardware, temperature, audio and model settings affect throughput.

This remains a preview. A fully uninterrupted fresh installation of the final source, a complete existing-device upgrade, attached RTC operation and long-term endurance remain unverified. V3 has no human-voice filter; sensitivity is fixed at 1.0 and species absent from the geographic model remain unrestricted. Audio capture is paused during manual analysis.

---
# BirdNET-Pi V3 — Preview 2

This fork adds local BirdNET+ V3 Preview recognition and manual verification while retaining the earlier BirdNET models in Settings. This preview includes fixes from a clean Raspberry Pi OS Lite 64-bit Debian Trixie installation on Raspberry Pi Zero 2 W.

## Included

- Sudo password authentication with refresh during long installation operations.
- The explicit Zero 2 W headless profile now adds 1 GiB disk-backed fallback swap, retaining Trixie zram at higher priority. This addresses V3 allocation OOM reproduced even with `cma=0`. See [Trixie installation](docs/TRIXIE_INSTALLATION.md).
- Current system time, RTC presence/time and service startup diagnostics once after boot, with rotated local logs. See [time and RTC logging](docs/STARTUP_LOGGING.md).
- Microphone discovery, USB preference and maximum ALSA capture gain/unmute. Automatic recording and streaming share a PulseAudio source; user audio startup does not depend on an SSH session. Busy cold boot discovery is retried, and streaming timestamps follow audio sample count.
- V3 Preview 3.1 Global 11K FP16 pruned as the default for new installations; previous model selection and saved parameter profiles remain available.
- Expanded label coverage for birds, mammals, insects and amphibians, with smaller groups of other labels. Model coverage and accuracy depend on the species and recording; this is a developer preview.
- Local audio processing optimisations using SoundFile/soxr, stereo-to-mono processing, top-k selection and configurable V3 inference threads.
- Manual TP/FP marks, changing or removing marks, authenticated POST and CSRF protection.
- Tools → System Controls generation/download of `BirdDB_verified.txt`, including **all detections** and review columns. The existing exporter is unchanged.
- Pinned, separately downloaded V3 model and labels with size/SHA-256 verification.
- Fresh installer that refuses an existing installation, requires user `pi`, uses this fork and leaves reboot to the operator.
- Update source `iiukolov-max/BirdNET-Pi_v3`, private backups, fast-forward updates, refusal of local changes/diverged history and inference readiness checks.
- Optional, explicitly selected Zero 2 W headless boot profile with boot backup, `cma=0`, `gpu_mem=16` and graphics/camera disabled.
- Full attributed upstream README plus fork changes, V3 capabilities, measured energy comparisons, limitations and recovery documentation.

## Validation

Raspberry Pi OS Lite 64-bit Bookworm has not been installation-tested with this release. Bookworm compatibility is a separate acceptance requirement; this release does not claim verified Bookworm support.

The clean Trixie device installed actual apt/pip dependencies, verified downloaded model/labels, recorded from a Sound Blaster Play! 3 and processed WAV files with V3. Reboot checks cover `CmaTotal=0`, swap, capture gain, HTTP and one time/RTC log per boot. The device has no RTC board: absence is verified, an attached RTC read remains untested. An interrupted SSH session during dependency download was resumed from the unfinished Python/model stage; this was not an uninterrupted installer run.

Database initialisation and repeated migration preserved every row of an offline development snapshot: 79,341 detections and 4,050 reviews. Local tests cover model-download integrity and boot configuration transformations. An isolated PHP/SQLite server exercised TP, FP, mark removal and invalid/unauthorised requests.

Real local Git/SQLite fixtures exercised successful updates, global-symlink invocation, dirty/staged/diverged history, wrong origin, disabled auto updates, untracked collisions, dependency/readiness failures, remote migration and code-only recovery preserving newer detections. Privileged, dependency and model actions were simulated in these updater tests. Export launch/download was separately tested through the development device's existing web interface.

## Limits and existing data

The development device was not upgraded with this candidate; its current recordings and review work remain available. Backups made by the updater contain database/configuration/code, **not a full audio archive**. Entire-update automatic rollback is not implemented. See [updates and recovery](docs/UPDATES_AND_RECOVERY.md).

V3 has no human-voice detection and limited environmental-noise handling. The integration uses the V2 geographic model with scientific-name matching; species absent from that model are not restricted by the geographic filter. Independently validated recognition accuracy across animal groups is not provided.

Hourly batch operation and a bird/noise prefilter are future work. CPU frequency and radio settings are not automatically changed. A full upgrade of an existing device with production history remains untested; isolated updater checks cover Git/SQLite preservation, while the clean card validates installation and startup.

The model has separate [sources and terms](docs/MODEL_SOURCES.md). Existing upstream source licensing and attribution are preserved.

## Install this release on a clean Zero 2 W

Run as user `pi` on Raspberry Pi OS Lite 64-bit Trixie:

```bash
curl -fL https://raw.githubusercontent.com/iiukolov-max/BirdNET-Pi_v3/v3-preview.2/newinstaller.sh -o birdnet-install.sh
BIRDNET_FORK_REF=v3-preview.2 bash birdnet-install.sh --zero2-headless
```

Reboot after successful installation to apply the boot profile. The installer refuses an existing installation; use the documented updater for an existing device. Read the [Trixie installation notes](docs/TRIXIE_INSTALLATION.md) before installing.

Inspect the boot time/RTC snapshot and microphone setup:

```bash
sudo tail -n 1 /var/log/birdnet/startup.jsonl | python3 -m json.tool
sudo journalctl -u birdnet_recording.service -b
```
# Local updates, 2026-10-08

- Overview aligns statistics, the latest detection and archive status in one responsive row, with tablet and phone layouts.
- Clear ALL data stops manual analysis before deleting audio, prevents recording restoration during cleanup, and serializes with Settings/manual start. Its confirmation now states that SQLite detection history and settings remain while audio, plots and BirdDB.txt are cleared.
- Economy recording uses CPU0 at600MHz on the tested Pi and one FFmpeg encoder thread. Manual analysis uses the original CPU mask, two V3 inference threads and an adaptive frequency cap. Normal mode and controller shutdown restore original CPU settings. Eight CPU-policy tests and a real recording-to-analysis transition passed; a fresh reboot of this new controller remains untested.
- Settings has a separate Services block below Model, with launch permissions for live audio, statistics, daily charts, the spectrogram viewer, log viewer and web terminal. Unchecked services are stopped and cannot start through systemd, mode switches or reboot. Recording and automatic/manual analysis cannot be restricted by these checkboxes; the selected mode still determines when analysis runs. Fresh installations default to all permissions enabled, Normal mode, full acoustic V3 preview3.1 and Geomodel V3.0.4. The pinned download manifest now includes both geomodel assets. Existing configurations are retained.

