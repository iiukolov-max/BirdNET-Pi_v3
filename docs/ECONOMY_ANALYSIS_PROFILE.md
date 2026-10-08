# Frozen Economy analysis profile — 2026-10-08

This profile was frozen at the project owner's request after tests on Raspberry Pi Zero 2 W. It is a post-Preview-3 source change; the published `v3-preview.3` tag has not been moved.

| Parameter | Frozen value |
| --- | --- |
| Acoustic model | Full BirdNET+ V3 preview3.1 Global 11K FP16 pruned |
| Geographic model on the tested device | V3.0.4 |
| V3 inference threads | 2, explicitly set in the archive service |
| BLAS/OMP/MKL threads | 1 each |
| Analysis CPU affinity | All available CPUs; CPU0–3 on the tested Zero 2 W |
| Analysis governor | ondemand, where supported |
| Frequency limits | Original hardware limits; 600–1000 MHz on the tested device |
| Reduce frequency | Temperature ≥78°C or current firmware frequency/throttle limitation |
| Recover one frequency step | 30 consecutive seconds at temperature ≤76°C |
| Recording profile | One recording CPU, lowest available frequency; CPU0/600 MHz on the tested device |
| Service scheduling | Nice 10, CPUWeight 10, IOWeight 10, idle I/O class |
| Swap policy on the tested device | Original swappiness 60; unchanged |

The controller uses supported frequencies within the saved original limits rather than setting every supported board to 1000 MHz. Normal restores the saved original CPU policy. Fresh-install mode remains Normal; existing model and optional-service preferences are preserved.

Microphone recording pauses during archive analysis and resumes after the manual run stops. Booting in Economy starts recording with automatic/manual analysis off. The frozen CPU profile does not change this behavior.

## Measurements and limits

A paired copy test ran two/three/two inference threads on four identical 30-second FLAC copies, twice per mode. Second-pass means were 13.943/12.375/15.400 seconds. Decoded PCM, top-ten prediction order/probabilities and detection lists matched exactly across the eight corresponding passes. These copies produced no detections. Thermal conditions and frequency caps differed between modes, so these are not an isolated percentage comparison.

A subsequent live three-thread run under the old thermal recovery rule processed 25 files in 407.204 seconds (16.288 seconds/file), without processing failures. The cap eventually reached 600 MHz. Three threads were not retained.

The final live two-thread run with recovery at 76°C processed **23 confirmed full 30-second FLAC files**, averaging **16.290 seconds/file**; the final ten averaged **17.191 seconds/file**. Processing failures were zero. The project owner requested freezing the current parameters, and the test was stopped gracefully with pending recordings retained. Microphone recording resumed on CPU0/600 MHz. Firmware flags were 0x0 at the final check, and no firmware limitation was observed in the sampled telemetry. The complete source model SHA-256 remained `f4af6290690e0031cd785d4c810167af83467ce1426f4eba249ca994681000db`.

The earlier 18.1-second result involved a different queue. These tests do not prove that all of the difference was caused by CPU policy. They identify a mechanism by which Economy can remain at a reduced cap: the earlier 74°C recovery threshold was hard to reach during sustained analysis. The fixed 76°C threshold retains the 78°C reduction threshold and a 30-second recovery delay. Short temperature excursions can still delay recovery. Sustained performance below 16 seconds/file has not been established without additional cooling.

Ten CPU-policy regression checks passed, including recovery from the lowest frequency at a safe warm temperature. Four installation-path checks, generated systemd-unit validation and recording-mode installer shell validation passed. The installer uses LF line endings and generates the archive unit for the installation owner/path.

For reference: [Raspberry Pi thermal management](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#frequency-management-and-thermal-control). Physical cooling and overclocking were not changed during these measurements.
