# BirdNET-Pi V3

Local acoustic monitoring based on [Nachtzuster/BirdNET-Pi](https://github.com/Nachtzuster/BirdNET-Pi), with BirdNET+ V3 Preview, recording modes and manual detection review.

**Current release:** [v3-preview.4](https://github.com/iiukolov-max/BirdNET-Pi_v3/releases/tag/v3-preview.4) · [Release notes](RELEASE_NOTES.md) · [Published releases](https://github.com/iiukolov-max/BirdNET-Pi_v3/releases)

## Features

- Economy refreshes Charts once after completed manual analysis, restoring its previous permission. SQLite WAL/FULL, verified backups and failed-file preservation improve recording reliability.
- Full BirdNET+ V3 Preview recognition of species represented in its label list, including birds and other animals. Earlier acoustic models remain selectable.
- **Normal:** microphone recording and automatic analysis. **Economy:** retain complete recordings and start archive analysis manually from Overview. Recording pauses during manual analysis and resumes when the run ends; rebooting in Economy starts recording without restarting analysis.
- Separate service permissions in Settings constrain optional services across mode changes, direct service starts and reboots. Recording and analysis remain mandatory, subject to the selected mode.
- Economy CPU control reduces recording CPU use and restores analysis capacity when needed. Normal restores the original CPU policy. Hardware capabilities determine available frequencies.
- Overview shows detections, species and verified species for the week/month, newly encountered species, recent detections and the last three boots with RTC information. Detection links open the specific recording's spectrogram.
- Archive progress separates the current queue from files added later. Storage estimates use recording settings, measured file sizes and the configured cleanup threshold.
- Manual TP/FP review and export of all detections with their review status through System Controls.
- Fresh-install defaults: **Normal**, acoustic **V3**, geographic model **V3.0.4**, all optional services allowed. Existing installation settings are preserved.

## Install

The Raspberry Pi configuration was tested on **Raspberry Pi OS Lite 64-bit Trixie**, including Zero 2 W. Use a new SD card, enable SSH and configure networking. Log in as your regular installation user; sudo may request a password.

Orange Pi support was contributed and hardware-tested by [miketimofeev](https://github.com/miketimofeev) in [PR #1: Add orangepi support](https://github.com/iiukolov-max/BirdNET-Pi_v3/pull/1). Our integration and reboot checks were performed on Raspberry Pi. The installer uses the current account and its home directory rather than requiring the username `pi`.

Install the latest published preview:

```bash
curl -fsSL https://raw.githubusercontent.com/iiukolov-max/BirdNET-Pi_v3/v3-preview.4/newinstaller.sh -o birdnet-install.sh && BIRDNET_FORK_REF=v3-preview.4 bash birdnet-install.sh
```

For **Raspberry Pi Zero 2 W without a display or camera**, add `--zero2-headless` to the installer command. This Raspberry Pi profile backs up boot settings, applies `cma=0` and `gpu_mem=16`, disables graphics/camera and adds 1 GiB disk swap while retaining zram. Do not select this profile for Orange Pi.

After successful installation, run `sudo reboot` and open `http://<device-hostname>.local` or the device's IP address. Check location, audio format and recording length in **Tools → Settings**. Confirm that recording and analysis work. Installation downloads dependencies and checksum-verified model files; recognition then runs locally.

The fresh installer refuses an existing installation. See [updates and recovery](docs/UPDATES_AND_RECOVERY.md) for updates, and [Trixie setup](docs/TRIXIE_INSTALLATION.md) for Raspberry Pi checks.

## Validation and limitations

- Raspberry Pi checks cover real Normal/Economy transitions and reboots, recording new 30-second FLAC files, analysis and disabled optional services remaining stopped.
- A Zero 2 W archive run processed 60 FLAC recordings without failures; warm processing averaged about 18.1 seconds per 30-second file. This is a device-specific measurement. Two inference threads are retained; the full V3 model remains in use.
- Orange Pi hardware testing is credited to the contributor. The new release's additional recording-mode and service-policy features have not been hardware-tested by us on Orange Pi.
- V3 is a developer preview. Its human-voice filter is unavailable and sensitivity is fixed at 1.0. Geographic filtering matches species names; unmatched species remain unrestricted.
- An uninterrupted clean installation of the final Preview 4 source, a complete existing-device upgrade, attached RTC operation and long-term endurance remain to be verified. Updater backups exclude the complete audio archive; full automatic update rollback is unavailable.

## Documentation and sources

- [Recording modes and service policy](docs/RECORDING_MODES.md)
- [Archive performance](docs/ARCHIVE_PERFORMANCE.md)
- [Boot history, RTC and microphone diagnostics](docs/STARTUP_LOGGING.md)
- [Detailed project notes](docs/PROJECT_DETAILS.md)
- [V2.4 versus V3 field comparison](docs/model-comparison/field-comparison.md)
- [Model sources and terms](docs/MODEL_SOURCES.md)
- [Preserved upstream README](docs/UPSTREAM_README.md) · [Source licence](LICENSE)

This fork retains upstream attribution and licence terms. Models have separate terms; see their linked sources.
