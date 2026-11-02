# Batch analysis on a computer

Only V3 Preview3.1 is supported. Choosing CPU or CUDA changes the inference
backend, not the model version. Other models require a separate adapter.

The computer receives source recordings over HTTP on the local network and
returns BirdNET V3 Preview 3.1 predictions. Raspberry Pi applies its own settings,
geographic filter, species lists and thresholds, then saves detections and audio
through the usual interface. The archive batch size is configurable and defaults
to 10 files.

## Data retention

- **Computer:** JSON predictions are stored in `--cache`, keyed by the audio
  SHA256, model version, prediction count and window overlap. Source audio is
  processed in memory and is not accumulated on the computer.
- **Pi:** successful completion, detection counts and detections commit together
  in SQLite. Confirmed zero-result, unchanged, unshared archive originals may be
  removed after that commit. Positive, unknown and failed results retain their
  source. See [analysis history](../docs/ANALYSIS_HISTORY.md). Normal archive
  cleanup still applies when storage reaches its configured limit.
- Resubmitting audio uses the computer's cache. Reimporting results does not add
  duplicate detections. Import is cancelled if the source fingerprint changed.
- If the connection fails, the client retries the current batch. Restarting a
  job excludes files whose results have already been imported.

## Windows package and desktop shortcut

Windows x64 and Python 3.10 x64 are required. Extract the package to a permanent
directory, keeping `pc_analysis` and `scripts` next to each other. In PowerShell,
from `pc_analysis`, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup-Service.ps1 -PiAddress 192.168.0.105 -Backend cuda
powershell -NoProfile -ExecutionPolicy Bypass -File .\New-Shortcut.ps1
```

For CPU inference, replace `cuda` with `cpu`. Setup creates a separate environment,
installs dependencies and downloads the model and labels with size/SHA256 checks.
CUDA requires a compatible NVIDIA driver; CPU inference does not need a GPU.
Model weights and the environment are downloaded during setup and are not
included in the ZIP. A clean installation of the portable package on another
computer has not been separately verified; inference and LAN communication were
tested on the development computer.

After rebooting, click **BirdNET Analysis** to start the service in the background.
The shortcut does not register automatic startup at Windows sign-in. To start
without waiting for Enter:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Service.ps1 -NoWait
```

Port 8766 must be reachable from the Pi. Setup does not change Windows Firewall
rules automatically.

## Manual Windows startup

CPU inference was tested with Python 3.10.1 x64 and TensorFlow 2.8.0. Dependencies
for a separate environment are listed in `requirements.txt`; a clean installation
of that environment has not been separately verified.

Use the original model and label CSV listed in `../model/v3-manifest.json`. The
service checks both SHA256 values at startup. The model includes all 11,560
output classes and does not require a GPU for CPU inference.

From the repository root:

```powershell
python pc_analysis/server.py --model "C:/BirdNET-models/BirdNET+_V3.0-preview3.1_Global_11K_FP16_pruned.tflite" --labels "C:/BirdNET-models/BirdNET+_V3.0-preview3.1_Global_11K_Labels.csv" --cache "C:/BirdNET-data/cache" --threads 4 --bind 0.0.0.0 --allow-client 192.168.0.105 --advertise-ip 192.168.0.145
```

The examples use `192.168.0.105` for the Pi and `192.168.0.145` for the computer.
Replace them with your own addresses. The API accepts requests only from the
explicitly allowed Pi and the computer itself. Allow access from the Pi to TCP
port 8766 in Windows Firewall. A shortcut created by the setup scripts starts
the selected service in the background and displays the computer's current IP.

An optional SSH fallback is available when a direct LAN connection is unavailable:

```powershell
python pc_analysis/connect.py --host pi@192.168.0.105 --host-key "SHA256:VERIFIED_SSH_FINGERPRINT"
```

The password is entered interactively and kept in memory. `connect.py` reconnects
after an SSH interruption; Ctrl+C closes the tunnel. The tunnel exposes loopback
port 8766 on the Pi. The client uses it only when the computer's IP matches the
address selected in Settings. Direct LAN communication does not require SSH or
an SSH password.

## Raspberry Pi settings

In **Tools → Settings → Advanced Settings**, open **Where to analyze recordings**:

1. Select the local BirdNET-Pi option for the default local mode.
2. Select the remote computer option, enter its IPv4 address and archive batch
   size, then save. The service must be running, and BirdNET V3 must be selected.

Connectivity is checked before switching to remote analysis. If that check
fails, the current analysis continues. Switching an active archive job restarts
it with the new backend, excluding files whose results were already imported.
Normal mode sends recordings individually; the batch size applies to archives.

Configuration keys: `ANALYSIS_BACKEND=local|remote`,
`REMOTE_ANALYSIS_IP=192.168.0.145`, `REMOTE_ANALYSIS_BATCH=10`. Missing keys default
to local analysis. The earlier experimental `60-remote.conf` override using
`BIRDNET_REMOTE_URL/BATCH` no longer selects the backend; remove that override
when migrating to this version.

To return to Pi analysis, select local mode in Settings. Previously imported
results are retained. Reduce the batch size for large files: the limits are
16 MiB per recording, 256 MiB per HTTP batch and 120 seconds per recording.

## API and diagnostics

- `GET /health`: readiness, model/label checksums, processed-file count and cache
  hits.
- `POST /v1/analyze`: a ZIP containing `manifest.json` and binary audio files.
  The ZIP is not extracted to disk. The JSON response contains window predictions
  tied to each source SHA256. One corrupt recording does not discard results
  for other files in the batch.
- The Pi client command `archive_remote.py probe --limit 3` checks communication
  and filtering without writing to the production database. Run it with the
  Pi's BirdNET Python environment.

## NVIDIA GPU

GPU inference was tested on an RTX 2060 with 6 GB VRAM, driver 581.80, ONNX Runtime
GPU 1.23.2, CUDA 12.9 and cuDNN 9.10.2.21. GPU dependencies use a separate Python
environment; the TensorFlow CPU environment is retained for switching back.
Dependencies are listed in `requirements-gpu.txt`.

The service uses the official
`BirdNET+_V3.0-preview3.1_Global_11K_FP16_pruned.onnx` file from
https://zenodo.org/records/20703646 with SHA256
`69cfc8db3ebec163feb6329e546eb56e1aadac2a309f1ee99aecfabd1aa9bd24`.
The checksum is verified at startup. To use it instead of the CPU service:

```powershell
python pc_analysis/gpu.py --model "C:/BirdNET-models/BirdNET+_V3.0-preview3.1_Global_11K_FP16_pruned.onnx" --labels "C:/BirdNET-models/BirdNET+_V3.0-preview3.1_Global_11K_Labels.csv" --cache "C:/BirdNET-data/gpu-cache" --port 8766 --bind 0.0.0.0 --allow-client 192.168.0.105 --advertise-ip 192.168.0.145
```

GPU and CPU caches are separate. Check `/health` for `backend=onnx-cuda`. If CUDA
cannot initialize, the GPU service fails startup instead of silently switching
to CPU. Tensor-shape bookkeeping operations may still run on the CPU.

In a comparison of 10 recordings and 19 windows, detections at a 0.6 threshold
matched. Probabilities were not bit-identical: the maximum observed difference
was about 0.002, and some low-confidence predictions changed order. This does
not guarantee identical decisions for every recording near the threshold.
Archive retention follows the rules described above.

Performance depends on the CPU and audio content. Allow for small floating-point
differences when comparing backends; check detections near the chosen threshold
before relying on a new backend.

## Full recordings

When positive Extraction Length and Recording Length are equal, the Pi retains
full audio without repeated trimming. Detection paths use hardlinks that survive
deletion of the original path. If another format is required, the recording is
encoded once. Shorter Extraction Length retains the existing clip-extraction
behavior. Previously generated clips are not rewritten.
