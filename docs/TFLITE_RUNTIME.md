# TFLite runtime for Raspberry Pi OS

The optional optimized runtime is distributed separately in
[birdnet-tflite-runtime v2.17.1.post3](https://github.com/iiukolov-max/birdnet-tflite-runtime/releases/tag/v2.17.1.post3).
Preview 10 selects a checksum-pinned native wheel from its runtime matrix:

| Raspberry Pi OS | Architecture | Python | NumPy | Native wheel |
| --- | --- | --- | --- | --- |
| Bookworm | ARM64 | 3.11 | 1.x or 2.x | cp311-cp311-linux_aarch64 |
| Trixie | ARM64 | 3.13 | 2.x | cp313-cp313-linux_aarch64 |

The qualified board remains Raspberry Pi Zero 2 W. These are Linux ARM64 wheels,
not universal or 32-bit packages. A different Python version, OS or board is not
automatically qualified. Unsupported targets keep their existing runtime.

Bookworm is validated using Debian Bookworm userspace, glibc 2.36 and Python 3.11
running on a real ARM64 Zero 2 W whose host OS is Trixie. NumPy 1.26.4 and 2.3.3
are checked. This validates the native component, not a fresh Bookworm SD-card
installation, its audio stack or the complete application. See the runtime
release's validation report for model and cache results.

The installer verifies downloads, compares model outputs, creates the weight
cache locally, and checks the canonical import before removing the old native
library. Do not reuse another device's cache. The full V3 model and native
FlexErf/FlexRFFT support are retained. Older application releases, including
Preview 9, keep their original pinned runtime; installing Preview 10 or updating
to its source is required to use the new matrix automatically.

No system Python or glibc upgrade is needed for the Bookworm wheel. Keep package
installation inside the application's virtual environment. Do not install a
Trixie wheel on Bookworm or rename its Python tag.
