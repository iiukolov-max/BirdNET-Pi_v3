# BirdNET-Pi V3

Local acoustic monitoring for Raspberry Pi, based on [Nachtzuster/BirdNET-Pi](https://github.com/Nachtzuster/BirdNET-Pi), with BirdNET+ V3 Preview, manual detection review and export from the web interface.

**Current release:** [v3-preview.2](https://github.com/iiukolov-max/BirdNET-Pi_v3/releases/tag/v3-preview.2) · [Release notes](RELEASE_NOTES.md)

## Features

- BirdNET+ V3 recognition of birds, mammals, insects and amphibians represented in its label list. Earlier BirdNET models remain available in **Tools → Settings**.
- Manual **TP / FP** marks: confirm, reject or remove a review.
- **Tools → System Controls** generates and downloads `BirdDB_verified.txt`, containing all detections and their review status.
- Automatic local microphone discovery, USB preference and maximum adjustable capture gain. Recording and streaming share the automatically selected input.
- One time/RTC diagnostic snapshot per boot, approximately two minutes after startup.

## Install

Use a new SD card with **Raspberry Pi OS Lite 64-bit Trixie**. Create user **`pi`**, enable SSH and configure networking in Raspberry Pi Imager. Log in as `pi`; sudo may request your password.

Install the published release:

```bash
curl -fsSL https://raw.githubusercontent.com/iiukolov-max/BirdNET-Pi_v3/v3-preview.2/newinstaller.sh -o birdnet-install.sh && BIRDNET_FORK_REF=v3-preview.2 bash birdnet-install.sh
```

**For Raspberry Pi Zero 2 W without a display or camera**, use this command instead:

```bash
curl -fsSL https://raw.githubusercontent.com/iiukolov-max/BirdNET-Pi_v3/v3-preview.2/newinstaller.sh -o birdnet-install.sh && BIRDNET_FORK_REF=v3-preview.2 bash birdnet-install.sh --zero2-headless
```

The Zero 2 W profile backs up boot settings, applies `cma=0` and `gpu_mem=16`, disables graphics/camera and adds **1 GiB disk swap**, retaining zram. On the tested Trixie device, CMA=0 and zram alone were insufficient for V3. Disk swap uses storage and writes to the SD card.

After successful installation, run `sudo reboot`. Open `http://<your-Pi-hostname>.local` or the Pi's IP address, then check location and recording settings under **Tools → Settings**. Confirm that recording and analysis work. See [Trixie setup and post-reboot checks](docs/TRIXIE_INSTALLATION.md).

Installation requires internet access to download dependencies and checksum-verified model files; recognition runs locally afterwards. The fresh installer refuses an existing installation: use [updates and recovery](docs/UPDATES_AND_RECOVERY.md) and back up your data first.

## Logs

View the latest system time, RTC presence/time and service startup snapshot:

```bash
sudo tail -n 1 /var/log/birdnet/startup.jsonl | python3 -m json.tool
```

Microphone detection and capture setup:

```bash
sudo journalctl -u birdnet_recording.service -b
```

Snapshots run once per boot, without minute-by-minute logging. A missing RTC does not prevent operation. See [time, RTC and microphone diagnostics](docs/STARTUP_LOGGING.md).

## Compatibility and limitations

- **Tested:** Trixie on Zero 2 W with Sound Blaster Play! 3, recording, V3 inference and reboot startup. **Bookworm is not yet verified** for this release.
- The installation was interrupted and resumed. A fully uninterrupted run of the revised installer, a full existing-device upgrade, attached RTC reading and long-term stability remain untested.
- V3 is a developer preview. Recognition depends on species coverage, recording quality and settings; more detections do not establish greater accuracy. Human-voice detection and a validated bird/noise prefilter are unavailable. The integration uses the V2 geographic model; some V3 species are outside its coverage.
- Zero 2 W has limited memory. CPU frequency and radio settings are not changed automatically; performance and battery life depend on the deployment.
- Updater backups do not include the full audio archive, and an automatic rollback of the entire update is not implemented.

## Documentation and sources

- [Detailed features, measurements and validation](docs/PROJECT_DETAILS.md)
- [V2.4 versus V3 field comparison](docs/model-comparison/field-comparison.md)
- [Model sources and terms](docs/MODEL_SOURCES.md)
- [Preserved upstream README](docs/UPSTREAM_README.md)
- [Source licence](LICENSE)

This fork retains upstream attribution and licence terms. Review the source licence and the model's separate terms before use.
