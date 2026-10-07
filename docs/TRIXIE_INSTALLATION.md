# Raspberry Pi OS Lite 64-bit Trixie

This release was tested on Trixie. A separate clean installation and reboot test
on Raspberry Pi OS Lite 64-bit Bookworm remains required; Bookworm compatibility
is not verified by the Trixie results.

Install as user `pi`. Sudo can prompt for a password; the installer refreshes
authentication during package installation. Keep the installation terminal open.
The installer refuses to overwrite an existing BirdNET-Pi directory.

On Raspberry Pi Zero 2 W use `--zero2-headless`. This explicit profile disables
graphics/camera, sets `gpu_mem=16` and `cma=0`, backs up boot files and provisions
a 1 GiB disk-backed fallback swap file at `/var/lib/birdnet/swapfile`. It retains
existing swap, including Trixie's zram; disk swap has priority 10, below the
default zram priority 100. The analysis service waits for fallback swap at boot.
The file occupies 1 GiB of storage and swap activity writes to the SD card.

Trixie's zram-only configuration was insufficient for V3 on the test Zero 2 W,
including after `CmaTotal=0` was confirmed. The kernel killed the analyzer while
allocating its model. Disk-backed fallback is required for this profile.

After installation, reboot and verify:

```bash
grep -E 'MemTotal|CmaTotal' /proc/meminfo
sudo swapon --show
sudo systemctl status birdnet_analysis birdnet_recording
sudo python3 /home/pi/BirdNET-Pi/scripts/check_model_ready.py
```

`CmaTotal` must be zero for the selected headless profile. An active systemd
process alone does not prove successful inference; use the readiness check and
recent recording/analysis logs. See [boot, RTC and microphone logs](STARTUP_LOGGING.md).

Recording and live streaming use the same detected PulseAudio source when the
device is automatic. User audio services receive the user runtime directory and
D-Bus address, with user service startup ordering and lingering enabled so audio
does not depend on an interactive SSH login. An explicit direct hardware PCM
remains an operator selection and may require separate sharing configuration.
