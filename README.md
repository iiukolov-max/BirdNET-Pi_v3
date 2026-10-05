# BirdNET-Pi V3

A development fork of [Nachtzuster/BirdNET-Pi](https://github.com/Nachtzuster/BirdNET-Pi), focused on BirdNET V3 integration and manual TP/FP verification of detections.

> **Development status — not ready for installation.**
> The BirdNET V3 and TP/FP changes developed for this fork have not yet been published here. The repository currently contains the inherited BirdNET-Pi implementation. Do not use it to install or upgrade to the V3 version.
>
> The inherited `newinstaller.sh` currently clones **Nachtzuster/BirdNET-Pi**, not this fork. Downloading that script from this repository does not install BirdNET V3.

## About this fork

The goal is to retain the familiar BirdNET-Pi recording, analysis, and web interface workflow while adding:

- **BirdNET V3 integration** for local acoustic bird classification.
- **Manual verification of detections** as true positives (TP) or false positives (FP).
- A practical deployment option for Raspberry Pi devices, with particular interest in the **Raspberry Pi Zero 2 W**.

These are the goals of the unpublished fork modifications, not features available in the current public code. Implementation details, supported hardware, and installation instructions will be documented when those modifications are published.

## Detection verification: TP and FP

The intended verification workflow lets a user review an audio detection and mark whether the reported species identification is correct:

| Status | Meaning |
| --- | --- |
| TP — true positive | A reviewer confirms the detected species in the recording. |
| FP — false positive | A reviewer determines that the reported species identification is incorrect. |
| Unreviewed | The detection has not been manually verified. |

A confidence score is a model output, not a manual verification result. Unreviewed detections should not be treated as confirmed observations.

The precise interface, storage format, filtering, and export behavior will be documented against the published implementation. Manual TP/FP labels do not by themselves retrain the model or measure false negatives.

## BirdNET model version

This README uses **BirdNET V3** until the exact model artifact and its provenance can be documented from the implementation.

Before a release, the documentation should identify:

- The exact acoustic model version and download source.
- The model filename and checksum.
- The inference runtime and required dependencies.
- Any geographic/species-range model used and its separate version.
- How to verify which model an installation actually loads.

The repository name, description, and this README are not evidence of the installed model version.

## Features inherited from BirdNET-Pi

The upstream BirdNET-Pi system provides:

- Continuous recording and automatic bird sound identification.
- Extraction and cataloguing of detection audio clips.
- A web interface with charts and recorded detection data.
- Live audio and spectrogram viewing.
- Automatic disk space management.
- SQLite storage and database administration tools.
- Backup and restore.
- BirdWeather integration and Apprise notifications.
- Localization of bird names and interface components.

Nachtzuster's fork also includes improvements to the web interface, analysis pipeline, daily charts, backup/restore, and support for newer operating systems. See the [upstream repository](https://github.com/Nachtzuster/BirdNET-Pi) for its current documentation.

## Hardware and operating system

The inherited upstream documentation lists Raspberry Pi 5, 4B, 400, 3B+, and Zero 2 W, with a 64-bit Raspberry Pi OS and a USB microphone or sound card.

**That upstream hardware list is not a compatibility guarantee for the unpublished V3 implementation.** Model runtime requirements, memory use, processing speed, and operating system support must be checked separately.

For Zero 2 W, release documentation should include the tested operating system, runtime, memory configuration, and whether analysis keeps up with continuous recording. Compatibility results for other boards will be listed when available.

## Installation and migration

Installation and migration instructions for **this fork** are not available yet.

Do not switch an existing installation's remote or run its update script expecting to obtain BirdNET V3 or TP/FP verification from the current public repository.

Before installation instructions are published, the installer and updater need to be checked to ensure they use this repository and install the correct model and dependencies. Migration instructions also need to cover preservation of recordings, configuration, detection data, and verification labels.

For the existing upstream version, use [Nachtzuster's documentation](https://github.com/Nachtzuster/BirdNET-Pi). Those instructions install upstream BirdNET-Pi, not the planned V3 version of this fork.

## Known limitations

- BirdNET V3 and TP/FP modifications are not yet present in this public repository.
- The inherited installer points to the upstream Nachtzuster repository.
- The exact V3 model artifact and runtime are not yet documented here.
- V3 hardware compatibility and performance results are not yet published.
- Automatic identifications can be incorrect and require review for uses that depend on confirmed records.

## Reporting issues

Use [this fork's issue tracker](https://github.com/iiukolov-max/BirdNET-Pi_v3/issues) for problems specific to this fork.

Include the commit or release, Raspberry Pi model, operating system, model/runtime versions, reproduction steps, and relevant logs. Remove passwords, tokens, and private information before posting.

## Credits and licensing

This project builds on:

- [BirdNET-Pi by Patrick McGuire](https://github.com/mcguirepr89/BirdNET-Pi).
- [Nachtzuster's BirdNET-Pi fork](https://github.com/Nachtzuster/BirdNET-Pi).
- [BirdNET-Analyzer](https://github.com/kahst/BirdNET-Analyzer) and the BirdNET research team at the K. Lisa Yang Center for Conservation Bioacoustics, Cornell Lab of Ornithology.
- [Pre-built TFLite binaries by PINTO0309](https://github.com/PINTO0309/TensorflowLite-bin) used by the inherited project.
- The upstream contributors and third-party projects credited in the original repository and [LICENSE](LICENSE).

The existing [LICENSE](LICENSE) and upstream attribution are retained. The inherited license identifies BirdNET-Lite and BirdNET-Pi as licensed under **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International** and includes notices for third-party components.

Review the license before use. The upstream project explicitly prohibits using BirdNET-Pi to develop a commercial product. Any newly integrated model or dependency must also be used and distributed under its applicable license.

BirdNET-Pi logo: icon by [Freepik](https://www.freepik.com) from [Flaticon](https://www.flaticon.com).

## Upstream screenshots

The screenshots below illustrate the inherited BirdNET-Pi interface, not the unpublished V3 or TP/FP functionality.

![BirdNET-Pi overview](docs/overview.png)
![BirdNET-Pi spectrogram](docs/spectrogram.png)
