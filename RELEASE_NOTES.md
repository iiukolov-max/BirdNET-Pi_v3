# BirdNET-Pi V3 preview — release candidate

This fork adds local BirdNET+ V3 Preview recognition and manual verification while retaining the earlier BirdNET models in Settings. This is an installation/update preview: fresh hardware installation and a full device upgrade have not yet been tested.

## Included

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

Database initialisation and repeated migration preserved every row of an offline development snapshot: 79,341 detections and 4,050 reviews. Local tests cover model-download integrity and boot configuration transformations. An isolated PHP/SQLite server exercised TP, FP, mark removal and invalid/unauthorised requests.

Real local Git/SQLite fixtures exercised successful updates, global-symlink invocation, dirty/staged/diverged history, wrong origin, disabled auto updates, untracked collisions, dependency/readiness failures, remote migration and code-only recovery preserving newer detections. Privileged, dependency and model actions were simulated in these updater tests. Export launch/download was separately tested through the development device's existing web interface.

## Limits and existing data

The development device was not upgraded with this candidate; its current recordings and review work remain available. Backups made by the updater contain database/configuration/code, **not a full audio archive**. Entire-update automatic rollback is not implemented. See [updates and recovery](docs/UPDATES_AND_RECOVERY.md).

V3 has no human-voice detection and limited environmental-noise handling. The integration uses the V2 geographic model with scientific-name matching; species absent from that model are not restricted by the geographic filter. Independently validated recognition accuracy across animal groups is not provided.

Hourly batch operation and a bird/noise prefilter are future work. CPU frequency and radio settings are not automatically changed. A real fresh installation and complete device update still require a separate card/device.

The model has separate [sources and terms](docs/MODEL_SOURCES.md). Existing upstream source licensing and attribution are preserved.
