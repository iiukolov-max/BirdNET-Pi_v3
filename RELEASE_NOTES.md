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
