# BirdNET-Pi V3

BirdNET-Pi V3 extends [Nachtzuster/BirdNET-Pi](https://github.com/Nachtzuster/BirdNET-Pi) with BirdNET V3 Preview support, manual detection verification and a reviewed-detections export available from the web interface.

This file is a working draft for a preview release. Installer and updater code has been prepared and checked in isolation; a fresh installation and a complete device update have not yet been tested. The release tag and installation command have not been finalised.

## Changes in this fork

### BirdNET V3 and model selection

#### What V3 can recognise

BirdNET+ V3 broadens acoustic monitoring beyond birds: its classifier includes **mammals, insects and amphibians**, with smaller sets of other animal labels. It identifies sounds from the animals represented in its label list; support for a group does not mean coverage of every species in that group. The official preview describes broader animal coverage and an expanded training dataset. [Official V3 documentation](https://github.com/birdnet-team/birdnet-V3.0-dev).

The **pinned Preview 3.1 label file used by this release contains 11,560 output labels**. Counting its `class` column gives:

| Group | Labels in the pinned model | Examples from its label list |
| --- | ---: | --- |
| Birds (`Aves`) | 9,834 | Songbirds, owls, waterbirds and other birds |
| Insects (`Insecta`) | 699 | House cricket, other crickets, grasshoppers and cicadas |
| Amphibians (`Amphibia`) | 647 | Frogs and toads |
| Mammals (`Mammalia`) | 350 | Impala, moose and howler monkeys |

There are also smaller groups of reptile, crocodilian, fish and other labels. These counts describe model labels, not an independent accuracy evaluation or a count of strictly species-level taxa. Source: the [pinned official label CSV](https://zenodo.org/records/20703646/files/BirdNET%2B_V3.0-preview3.1_Global_11K_Labels.csv?download=1), whose checksum is recorded in the release manifest.

Selecting V3 enables this broader classifier without installing a separate mammal or insect detector. Results still depend on the recorded sound, microphone, thresholds and filtering. Review unfamiliar detections with TP/FP; this project has not independently validated accuracy across all these groups.

V3 also introduces 32 kHz audio input, a revised architecture and training procedure, and support for variable-duration input at the model level. This BirdNET-Pi integration continues using its configured analysis windows; it does not expose every feature of the upstream demo tools. The preview has no human-voice detection and limited handling of rain, wind and engine sounds, so it should not be treated as a validated bird/noise prefilter. [Preview features and limitations](https://github.com/birdnet-team/birdnet-V3.0-dev#about-this-release).

#### Integration and model selection

- New installations use **BirdNET+ V3.0 Developer Preview 3.1, Global 11K, FP16 pruned** by default.
- Previous BirdNET models remain available under **Tools → Settings**.
- Model switching restores the model's saved parameters and checks readiness of the current analysis process. If startup fails, the previous model and configuration are restored.
- V3 outputs are handled as probabilities without applying sigmoid again. Audio is prepared at 32 kHz.
- Tested optimisations include SoundFile/soxr audio loading, stereo-to-mono processing, selection of only the required highest-scoring predictions and short-lived TFLite output views.
- V3 inference thread count is configurable. Suitable settings depend on the device; fixed CPU frequencies used during development are not a universal default.

V3 is a **developer preview**. Sensitivity is fixed at 1.0 and the previous human-voice filter is unavailable. The current integration uses the V2 geographic model with scientific-name matching; species absent from V2 are not restricted by that filter. This is not the V3 geographic model. Some added species may lack a localised name.

### Manual TP/FP verification

Detections can be marked as:

- **TP / correct:** the identification is correct.
- **FP / false positive:** the identification is incorrect.
- **Unreviewed:** no manual assessment has been recorded.

Review marks can be changed; clicking the selected mark again removes it. Changes require authenticated POST requests with a session token. TP, FP, removal and rejection of unauthorised/invalid requests have been checked against a disposable PHP/SQLite fixture. Database initialisation and repeated review migrations preserved every detection and review in an offline development snapshot (79,341 detections and 4,050 reviews). A complete device upgrade still requires validation.

### Export from Tools

Open **Tools → System Controls**:

1. Select **Generate BirdDB_verified.txt**.
2. Wait for the completion message and exported record count.
3. Select **Download BirdDB_verified.txt**.

The export contains **all detections**, including TP, FP and unreviewed records. It adds `ReviewStatus` and `ReviewedAt` to the existing detection fields. Despite the filename, it is not a TP-only subset.

The existing `export_birddb_verified.py` is included **without changes**. The web integration provides authenticated launch/download, request verification, prevention of concurrent web exports and recovery of the previous output when export fails. Recording and analysis continue during export.

Export generation and downloading have been tested through the real web interface. The unchanged exporter currently uses fixed paths under `/home/pi/BirdNET-Pi`; the initial installation contract must account for this.

## Installation and model downloads

The installer will deploy this fork, its dependencies and services, initialise or migrate review storage, and install the export controls.

The V3 model binary will be downloaded **separately from the official source**, together with the corresponding labels. A manifest in the release will pin model versions, download locations and checksums. The installer will verify downloads before using them and reuse already valid files. It will not automatically substitute an untested latest model.

Previous models and the required geographic model must also be available for switching. After installation, inference runs locally without an internet connection. Installing or updating software and downloading missing models require network access.

The fresh installer refuses an existing application directory or configuration, uses this fork, requires user `pi`, and leaves reboot to the operator. Local tests cover checksum enforcement, reuse of valid files and preservation of a previous artifact after a failed download. A fresh hardware installation is pending; the existing development card remains available for listening.

## Updates from this fork

**Tools → System Controls → Update** will use:

`https://github.com/iiukolov-max/BirdNET-Pi_v3.git`

The installer/migration will configure the Git remote and update tracking. Update checks, the available-update indicator, enabled automatic updates and the running-version link must use the same source.

The prepared updater accepts this fork's `origin/main` only, refuses local tracked edits and diverged history, and uses a fast-forward update without `git reset --hard` or `git clean`. It creates private consistent SQLite/configuration/code backups before changing application code, preserves the selected model and existing audio, and checks inference readiness. An update failure is reported with the backup location; automatic recovery of the entire update is not yet implemented. Automatic updates remain controlled by the existing setting.

The update channel is implemented in the candidate, including the update counter and running-version link. Local Git/SQLite tests cover successful fast-forward updates, execution through a global symlink, refusal of edits/diverged history/untracked collisions/wrong origin, dependency/readiness failures, remote migration, and code-only recovery preserving newer detections. Service, dependency and model actions are simulated in those tests; a complete hardware upgrade remains untested. The development Pi still tracks the original repository and has not been updated with this candidate. See [updates and recovery](docs/UPDATES_AND_RECOVERY.md) for backup behaviour and limitations, and [model sources](docs/MODEL_SOURCES.md) for attribution and separate V3 terms.

## Raspberry Pi Zero 2 W

V3 testing on the development Zero 2 W used a profile **without graphics or camera**, including:

- `cma=0` in the kernel command line;
- `gpu_mem=16`;
- disabled graphics overlay and camera/display auto-detection.

The installer will offer this profile specifically for Zero 2 W, back up the boot configuration and explain the required reboot. After reboot, it must verify `CmaTotal=0`, available memory, model readiness and recording. Other Raspberry Pi models will not receive these boot settings automatically.

These settings are intended for deployments without graphics or camera. V3 remains demanding on a device with 512 MB RAM; the profile alone does not guarantee sustained real-time operation. The supported hardware/OS matrix will state which configurations were actually tested.

CPU frequency limits and disabling Wi-Fi/Bluetooth are not applied automatically by this release.

## Scope of the first release

The first release includes V3 integration, previous-model selection, manual TP/FP review, full detection export, tested processing optimisations, installation/update integration and documentation.

Hourly batch analysis and a bird/noise prefilter are research work for future releases. Neither is enabled in this release, and no filtering-based energy savings are claimed.

Code and model licensing/attribution notices must be retained. Model source and terms will be documented in the pinned artifact manifest and release documentation.

## Validation before publication

The completed export checks cover all-row semantics, missing review-table behaviour, authenticated HTTP generation/download, rejected unauthorised and invalid requests, lock behaviour, failed-export recovery and unchanged recording/analysis processes.

The complete release still requires comparison against this fork's current code, TP/FP interface/migration validation, fresh installation, updating an existing installation, model switching and rollback, model download verification, and sustained operation. Development measurements do not establish accuracy or performance on every supported board.

## V2.4 versus V3: measured power consumption

Measurements were taken on 4–5 October 2026 using a Raspberry Pi Zero 2 W and an external USB power meter. They describe the **whole assembly**, including the Sound Blaster Play! 3 USB sound card, microphone, USB hub and USB Ethernet adapter. Wi-Fi, Bluetooth and HDMI were disabled; the tested system used the headless/CMA-disabled profile. USB Ethernet remained connected for every comparison.

Timer values below are minutes:seconds. Current and energy readings were supplied by the operator. Average power is `mWh / 1000 × 3600 / elapsed_seconds`; average current is `mAh × 3600 / elapsed_seconds`.

| Mode | Duration | mAh | mWh | Average current | Average power |
|---|---:|---:|---:|---:|---:|
| V3, 1 inference thread, CPU 600–1000 MHz | 21:51 | 146 | 770 | 400.9 mA | 2.114 W |
| V3, 2 inference threads, CPU 600–1000 MHz | 22:30 | 153 | 811 | 408.0 mA | 2.163 W |
| V3, 4 inference threads, CPU 600 MHz | 19:16 | 129 | 678 | 401.7 mA | 2.111 W |
| WAV recording only, CPU 600 MHz | 19:21 | 71 | 372 | 220.2 mA | **1.153 W** |
| V2.4, standard interpreter, CPU 600 MHz | 16:51 | 69 | 365 | 245.7 mA | **1.300 W** |
| Optimised V3, 2 threads, CPU 600 MHz, accumulated backlog | 14:51 | 108 | 571 | 436.4 mA | **2.307 W** |
| Optimised V3, 4 threads, requested CPU 1000 MHz, accumulated backlog | 17:16 | 200 | 1065 | 695.0 mA | **3.701 W** |

In these measurements V2.4 consumed about **38.4% less power** than V3/4 threads/600 MHz, and added about **0.146 W** over recording alone. Optimised V3/2/600 consumed about 77.5% more than V2.4, but these tests had different workloads: processing a large backlog keeps inference busy, whereas a caught-up system can wait between files. The table therefore does **not** establish that an optimisation increased power consumption or that one thread count is universally more efficient. A repeated comparison on identical audio and workload is required.

At the end of the 4-thread/1000 MHz test, temperature reached **82.7 °C** and firmware reported frequency capping, with throttling recorded since boot. The sysfs frequency setting alone does not demonstrate an unrestricted physical clock. Initial 30-second files took about 10.9–11.5 seconds to analyse; later files averaged about **12.5 seconds**. Thermal behaviour is part of this measured result, not an excluded condition.

One subsequent test at **1 thread/800 MHz** processed its first 30-second file in 29.93 seconds; no USB power result was collected for that setting. A single file does not establish sustained throughput, and the margin for clearing a backlog was small.

These are short development measurements, not guaranteed battery life or a power specification for other Raspberry Pi models. CPU frequency limits were test settings. Quantities stated for FP16 models do not imply hardware FP16 computation on the Zero 2 W.

### Battery-life estimates

For an illustrative 80 Ah power bank rated at a 3.7 V cell voltage, nominal energy is 296 Wh. Assuming 80–90% usable energy, recording alone would give roughly **8.55–9.62 days**, and V2.4 roughly **7.59–8.54 days**. The actual usable energy has not been measured, and neither estimate is a completed field endurance test. A 10-day target would require about 0.987–1.110 W under those assumptions, below the measured recording-only baseline.

## Hourly batch analysis: evaluated, not implemented

The proposed mode records for an hour with V3 stopped, then starts V3 at maximum tested throughput and processes the entire queue, including audio recorded during processing. No audio is intentionally skipped.

With the measured maximum-mode power and observed throughput:

- An initial hour of audio would take roughly 25–26 minutes to process if no new recordings arrived.
- With recording continuing, clearing the entire growing queue is estimated to take **43–47 minutes** after the hour of accumulation.
- The full cycle would last about 103–107 minutes, with an estimated average power of **2.22–2.27 W**, excluding model startup/shutdown and frequency transitions.

This is a calculation from measurements, not a completed batch-cycle test. It offers little potential improvement over the measured V3/2/600 backlog workload and does not approach V2.4's 1.30 W. Longer accumulation intervals do not by themselves reduce the number of windows analysed. Waiting with a loaded V3 model has not been separately measured and cannot be assigned the recording-only power baseline.

At 48 kHz stereo PCM16, one hour of continuous WAV audio occupies approximately **691.2 MB** before headers. `AUDIOFMT=flac` configures extracted detection clips; it does not mean continuous StreamData recording is FLAC. Power consumption of continuous FLAC archiving has not been measured. Any future batch mode needs disk-space protection and confirmation that every queued file is processed.

## Recognition comparison and validation limits

A development comparison used 11 saved recordings, 249 seconds of audio and 88 three-second windows. V2.4 and V3 had different top-1 predictions in 51 windows and completely disjoint top-3 predictions in 39. Among 43 windows where at least one model had top-1 confidence of 0.6 or higher, top-1 differed in 9 windows and top-3 was disjoint in 2. No window had different top-1 predictions with confidence of at least 0.6 in both models.

These figures measure **prediction disagreement**, not which model is more accurate. Archive folder names were generated by an earlier model, not independent ground truth. Confidence values are not calibrated between versions; a larger value does not prove a better identification.

The revised audio preparation was checked for equivalence with the previous pipeline. V3 top-k/output-view optimisation and stereo preparation were also tested against the previous code. An isolated hour-long archive analysis completed 160 files without the earlier OOM failure; later paced pipeline checks included extracted FLAC/PNG files and temporary database output. These checks cover specific stages and conditions, not every live deployment, notification backend or hardware configuration.

## Bird/noise prefilter: future evaluation

A lightweight detector could evaluate all audio and send likely-bird and uncertain windows to V3. Candidate approaches include simple spectral triggers and compact INT8 binary models. No prefilter is currently enabled, and no energy reduction is claimed.

The agreed evaluation uses selected FLAC clips containing birds and retained WAV recordings reported by the operator to contain no birds. File-level labels do not establish the contents of every short window. Tests must measure bird recall, false alarms, processing cost and the proportion of windows that could be excluded. Missed quiet/short calls matter more than overall classification accuracy. Rejected windows should initially still pass through V3 and be sampled for manual listening.

Any decision to skip V3 for negative windows changes analysis coverage and must follow evaluation. Recording-only baseline power remains even if every unnecessary V3 invocation is eliminated.

## Optional operational telemetry

The development system has a bounded rotating log of CPU utilisation, temperature, frequency/capping flags, RAM/swap activity, analysis/recording processes and queue size/age. This can be included as an optional diagnostic component. It is **not a wattmeter**; USB power/energy comparisons require external measurement.

Model thread settings in a systemd drop-in persist across reboot. Frequency limits applied through sysfs during experiments do not necessarily persist. A readiness file is valid only when its model and PID match the active analysis process.

## Release-readiness status

V3 and the export controls have been exercised on the development Pi. The complete fork installer, updater, clean-install path, review migration and hardware matrix are still being prepared. This README deliberately records those remaining checks rather than describing an untested release as ready.

The original project description and documentation from Nachtzuster are retained below as an attributed upstream reference. Its installation/migration commands target the original project; they are not installation instructions for this V3 fork. The fork-specific installation command will be added after validation, and inherited links will be audited before publication.

---

<details>
<summary>Original Nachtzuster README — project description and upstream documentation</summary>

Source: [Nachtzuster/BirdNET-Pi README](https://github.com/Nachtzuster/BirdNET-Pi/blob/main/README.md), retrieved 5 October 2026. The following section is preserved from upstream. Use the fork-specific sections above for changes in this project.

<h1 align="center"><a href="https://github.com/mcguirepr89/BirdNET-Pi/blob/main/LICENSE">Review the license!!</a></h1>
<h1 align="center">You may not use BirdNET-Pi to develop a commercial product!!!!</h1>
<h1 align="center">
  BirdNET-Pi
</h1>
<p align="center">
A realtime acoustic bird classification system for the Raspberry Pi 5, 4B, 400, 3B+, and 0W2
</p>
<p align="center">
  <img src="https://user-images.githubusercontent.com/60325264/140656397-bf76bad4-f110-467c-897d-992ff0f96476.png" />
</p>
<p align="center">
Icon made by <a href="https://www.freepik.com" title="Freepik">Freepik</a> from <a href="https://www.flaticon.com/" title="Flaticon">www.flaticon.com</a>
</p>

## About this fork:
I've been building on [mcguirepr89's](https://github.com/mcguirepr89/BirdNET-Pi) most excellent work to further update and improve BirdNET-Pi. Maybe someone will find it useful.

Changes include:

 - Backup & Restore
 - Web ui is much more responsive
 - Daily charts now include all species, not just top/bottom 10
 - Bump apprise version, so more notification type are possible
 - Swipe events on Daily Charts (by @croisez)
 - Support for 'Species range model V2.4 - V2'
 - Bookworm and Trixie support
 - Experimental support for writing transient files to tmpfs
 - Rework analysis to consolidate analysis/server/extraction. Should make analysis more robust and slightly more efficient, especially on installations with a large number of recordings
 - Bump tflite_runtime to 2.17.1, it is faster
 - Rework daily_plot.py (chart_viewer) to run as a daemon to avoid the very expensive startup
 - Lots of fixes & cleanups

!! note: see 'Migrating' on how to migrate from mcguirepr89

## Introduction
BirdNET-Pi is built on the [BirdNET framework](https://github.com/kahst/BirdNET-Analyzer) by [**@kahst**](https://github.com/kahst) <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/"><img src="https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg"></a> using [pre-built TFLite binaries](https://github.com/PINTO0309/TensorflowLite-bin) by [**@PINTO0309**](https://github.com/PINTO0309) . It is able to recognize bird sounds from a USB microphone or sound card in realtime and share its data with the rest of the world.

Check out birds from around the world
- [BirdWeather](https://app.birdweather.com)<br>

## Features
* **24/7 recording and automatic identification** of bird songs, chirps, and peeps using BirdNET machine learning
* **Automatic extraction and cataloguing** of bird clips from full-length recordings
* **Tools to visualize your recorded bird data** and analyze trends
* **Live audio stream and spectrogram**
* **Automatic disk space management** that periodically purges old audio files
* [BirdWeather](https://app.birdweather.com) integration -- you can request a BirdWeather ID from BirdNET-Pi's "Tools" > "Settings" page
* Web interface access to all data and logs provided by [Caddy](https://caddyserver.com)
* [GoTTY](https://github.com/yudai/gotty) and [GoTTY x86](https://github.com/sorenisanerd/gotty) Web Terminal
* [Tiny File Manager](https://tinyfilemanager.github.io/)
* FTP server included
* SQLite3 Database
* [Adminer](https://www.adminer.org/) database maintenance
* [phpSysInfo](https://github.com/phpsysinfo/phpsysinfo)
* [Apprise Notifications](https://github.com/caronc/apprise) supporting 90+ notification platforms
* Localization supported

## Requirements
* A Raspberry Pi 5, Raspberry 4B, Raspberry Pi 400, Raspberry Pi 3B+, or Raspberry Pi 0W2 (The 3B+ and 0W2 must run on RaspiOS-ARM64-**Lite**)
* An SD Card with the **_64-bit version of RaspiOS_** installed (please use Trixie) -- Lite is recommended, but the installation works on RaspiOS-ARM64-Full as well. Downloads available within the [Raspberry Pi Imager](https://www.raspberrypi.com/software/).
* A USB Microphone or Sound Card

## Installation
[A comprehensive installation guide is available here](https://github.com/mcguirepr89/BirdNET-Pi/wiki/Installation-Guide). This guide is slightly out-dated: make sure to pick Bookworm, also the curl command is still pointing to mcguirepr89's repo.

Please note that installing BirdNET-Pi on top of other servers is not supported. If this is something that you require, please open a discussion for your idea and inquire about how to contribute to development.

[Raspberry Pi 3B[+] and 0W2 installation guide available here](https://github.com/mcguirepr89/BirdNET-Pi/wiki/RPi0W2-Installation-Guide)

The system can be installed with:
```
curl -s https://raw.githubusercontent.com/Nachtzuster/BirdNET-Pi/main/newinstaller.sh | bash
```
The installer takes care of any and all necessary updates, so you can run that as the very first command upon the first boot, if you'd like.

The installation creates a log in `$HOME/installation-$(date "+%F").txt`.
## Access
The BirdNET-Pi can be accessed from any web browser on the same network:
- http://birdnetpi.local OR your Pi's IP address
- Default Basic Authentication Username: birdnet
- Password is empty by default. Set this in "Tools" > "Settings" > "Advanced Settings"

Please take a look at the [wiki](https://github.com/mcguirepr89/BirdNET-Pi/wiki) and [discussions](https://github.com/mcguirepr89/BirdNET-Pi/discussions) for information on
- [BirdNET-Pi's Deep Convolutional Neural Network(s)](https://github.com/mcguirepr89/BirdNET-Pi/wiki/BirdNET-Pi:-some-theory-on-classification-&-some-practical-hints)
- [making your installation public](https://github.com/mcguirepr89/BirdNET-Pi/wiki/Sharing-Your-BirdNET-Pi)
- [backing up and restoring your database](https://github.com/mcguirepr89/BirdNET-Pi/wiki/Backup-and-Restore-the-Database)
- [adjusting your sound card settings](https://github.com/mcguirepr89/BirdNET-Pi/wiki/Adjusting-your-sound-card)
- [suggested USB microphones](https://github.com/mcguirepr89/BirdNET-Pi/discussions/39)
- [building your own microphone](https://github.com/DD4WH/SASS/wiki/Stereo--(Mono)-recording-low-noise-low-cost-system)
- [privacy concerns and options](https://github.com/mcguirepr89/BirdNET-Pi/discussions/166)
- [beta testing](https://github.com/mcguirepr89/BirdNET-Pi/discussions/11)
- [and more!](https://github.com/mcguirepr89/BirdNET-Pi/discussions)


## Updating 

Use the web interface and go to "Tools" > "System Controls" > "Update". If you encounter any issues with that, or suspect that the update did not work for some reason, please save its output and post it in an issue where we can help.

## Backup and Restore
Use the web interface and go to "Tools" > "System Controls" > "Backup" or "Restore". Backup/Restore is primary meant for migrating your data for one system to another. Since the time required to create or restore a backup depends on the size of the data set and the speed of the storage, this could take quite a while.

Alternatively, the backup script can be used directly. These examples assume the backup medium is mounted on `/mnt`

To backup:
```commandline
./scripts/backup_data.sh -a backup -f /mnt/birds/backup-2024-07-09.tar
```
To restore:
```commandline
./scripts/backup_data.sh -a restore -f /mnt/birds/backup-2024-07-09.tar
```

## x86_64 support
x86_64 support is mainly there for developers or otherwise more Linux savvy people.
That being said, some pointers:
- Use Debian 12 or 13
- The user needs passwordless sudo

For Proxmox, a user has reported adding this in their `cpu-models.conf`, in order for the custom TFLite build to work.
```
cpu-model: BirdNet
    flags +sse4.1
    reported-model host
```

## Uninstallation
```
/usr/local/bin/uninstall.sh && cd ~ && rm -drf BirdNET-Pi
```
## Migrating
Before switching, make sure your installation is fully up-to-date. Also make sure to have a backup, that is also the only way to get back to the original BirdNET-Pi.
Please note that upgrading your underlying OS to Bookworm is not going to work. Please stick to Bullseye. If you do want Bookworm, you need to start from a fresh install and copy back your data. (remember the backup!)

Run these commands to migrate to this repo:
```
git remote remove origin
git remote add origin https://github.com/Nachtzuster/BirdNET-Pi.git
./scripts/update_birdnet.sh
```
## Troubleshooting and Ideas
*Hint: A lot of weird problems can be solved by simply restarting the core services. Do this from the web interface "Tools" > "Services" > "Restart Core Services"
Having trouble or have an idea? *Submit an issue for trouble* and a *discussion for ideas*. Please do *not* submit an issue as a discussion -- the issue tracker solicits information that is needed for anyone to help -- discussions are *not for issues*.

PLEASE search the repo for your issue before creating a new one. This repo has nothing to do with the validity of the detection results, so please do not start any issues around "False positives."

## Sharing
Please join a Discussion!! and please join [BirdWeather!!](https://app.birdweather.com)
I hope that if you find BirdNET-Pi has been worth your time, you will share your setup, results, customizations, etc. [HERE](https://github.com/mcguirepr89/BirdNET-Pi/discussions/69) and will consider [making your installation public](https://github.com/mcguirepr89/BirdNET-Pi/wiki/Sharing-Your-BirdNET-Pi).

## Homeassistant addon

BirdNET-Pi can also be run as a [Homeassistant](https://www.home-assistant.io/) addon through docker.
For more information : https://github.com/alexbelgium/hassio-addons/blob/master/birdnet-pi/README.md

## Docker

BirdNET-Pi can also be run as as a docker container.
For more information : https://github.com/alexbelgium/hassio-addons/blob/master/birdnet-pi/README_standalone.md

## Cool Links

- [Marie Lelouche's <i>Out of Spaces</i>](https://www.lestanneries.fr/exposition/marie-lelouche-out-of-spaces/) using BirdNET-Pi in post-sculpture VR! [Press Kit](https://github.com/mcguirepr89/BirdNET-Pi-assets/blob/main/dp_out_of_spaces_marie_lelouche_digital_05_01_22.pdf)
- [Research on noded BirdNET-Pi networks for farming](https://github.com/mcguirepr89/BirdNET-Pi-assets/blob/main/G23_Report_ModelBasedSysEngineering_FarmMarkBirdDetector_V1__Copy_.pdf)
- [PixCams Build Guide](https://pixcams.com/building-a-birdnet-pi-real-time-acoustic-bird-id-station/)
- [Core-Electronics](https://core-electronics.com.au/projects/bird-calls-raspberry-pi) Build Article
- [RaspberryPi.com Blog Post](https://www.raspberrypi.com/news/classify-birds-acoustically-with-birdnet-pi/)
- [MagPi Issue 119 Showcase Article](https://magpi.raspberrypi.com/issues/119/pdf)


### Internationalization:
The bird names are in English by default, but other localized versions are available thanks to the wonderful efforts of [@patlevin](https://github.com/patlevin) and Wikipedia. Use the web interface's "Tools" > "Settings" and select your "Database Language" to have the detections in your language.

[Internationalization](docs/translations.md)


## Screenshots
![Overview](docs/overview.png)
![Spectrogram](docs/spectrogram.png)


## :thinking:
Are you a lucky ducky with a spare Raspberry Pi? [Try Folding@home!](https://foldingathome.org/)

</details>
