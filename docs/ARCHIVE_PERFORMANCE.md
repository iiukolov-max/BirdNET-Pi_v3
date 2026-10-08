# Manual archive performance on Zero 2 W

## Controlled repeat, final result

2026-10-08 13:29–13:35 MSK: fixed copies of MP3/15 s and FLAC/30 s, settings locked, microphone recording inactive in every telemetry sample. Three passes per sample/mode, first pass excluded. No clip extraction or database writes.

| Threads | MP3, 15 s | FLAC, 30 s | CPU seconds per file, mixed pair |
| --- | ---: | ---: | ---: |
| 2, first | 7.314 s | 16.462 s | 21.50 s |
| 4 | 7.444 s | 15.904 s | 37.39 s |
| 2, control | 7.489 s | 15.744 s | 21.39 s |

Four threads offered no consistent wall-time benefit and used approximately 74% more CPU time. Two threads are retained. Top-three labels and probabilities matched exactly on these samples. Observed temperature was 72.5–83.8°C, frequency 700–1000 MHz and analyzer RSS plus swap 498–502 MiB. Firmware reported 0x20002 during the four-thread phase: current and historical ARM frequency capping ([official bit definitions](https://www.raspberrypi.com/documentation/computers/os.html#get_throttled)). Thermal conditions were not fixed; this describes the present device, not an intrinsic thread-count limit. Inference accounted for approximately 95% of measured processing time. Cooling and reducing memory are candidates for future measurements, without a demonstrated benefit yet.

Storage estimates use current format, segment length and cleanup percentage, plus measured bytes per audio second matching that format/length. FLAC/30 s measured approximately 37,519 bytes/s (3.24 GB per recording day). Days refer to continuous recording until cleanup. Compression varies with audio content. Analysis ETA uses the current run's average per completed file; mixed durations/formats and detection extraction make it approximate. Preparation clears previous-run counters and hides stale ETA.

## Memory profiling, 2026-10-08

A separate three-process FLAC/30 s test compared baseline, deferred notification imports and baseline control. Warm times were 14.900/14.625/14.733 s; RSS plus swap after processing was 503.87/497.26/501.42 MiB. The measured saving is approximately 4–7 MiB; the small time difference does not establish a sustained speedup. Predictions, detections and decoded WAV hashes matched across all nine passes on this sample. Model initialization increased RSS plus swap from approximately 80 to 488 MiB; audio reading added approximately 5.5 MiB after decoding. Model allocation remains the dominant cost.

Reporting now loads notifications when Apprise is called. Requests is additionally imported only inside network functions; that additional change has a functional check but no independent paired speed measurement. Validation uses a notification stub and sends no messages. After deployment the real analyzer processed three files without errors and microphone recording remained paused. Cooling was not changed or tested; a physical change and separate comparison are needed to measure its benefit.

## Backend screening, 2026-10-08

Three isolated processes compared XNNPACK, optimized built-in TFLite kernels without default delegates, and XNNPACK control. Six fixed three-second windows from MP3/15 s and FLAC/30 s copies were processed three times; the first pass was excluded. Warm inference averages were 1.418/1.764/1.387 s per window; RSS plus swap was 481.35/294.51/482.13 MiB. Recording was inactive in all telemetry samples. Temperature was 74.1–81.7°C; thermal conditions were not fixed.

Disabling default delegates saved approximately 187 MiB but increased per-window time approximately 26%. Model readiness was faster (9.25 s versus 27.45–33.24 s), which does not offset repeated slower inference for the current large queue. XNNPACK remains the production default. The experimental resolver was confined to the test process; no model or backend settings were changed.

Input hashes and top-ten label order matched. No output crossed confidence 0.6. Maximum absolute probability difference was 1.073e-6; outputs were numerically close, not bit-identical between backends. The XNNPACK control matched the first XNNPACK outputs exactly. This screening excludes extraction/database work and does not independently establish recognition accuracy. The resolver disables default delegates as described in [official TensorFlow documentation](https://www.tensorflow.org/api_docs/python/tf/lite/experimental/OpResolverType).

## Isolated 700-output prototype, 2026-10-08

A separate experimental TFLite file sliced the final FP16 classifier weights and bias from 11,560 to 700 outputs. The original production file and configuration were unchanged and its hash was verified before/after testing. The 700 labels form a technical subset, not a Russian species checklist; the prototype is not included as a production model.

Full/reduced/full-control XNNPACK processes ran six fixed three-second audio windows three times. Warm inference was 1.388/1.306/1.433 s per window and RSS plus swap 474.03/329.90/473.68 MiB. This short trial showed approximately144MiB lower RSS plus swap and6–9% shorter inference time. Temperature was73.1–81.7°C and not controlled. Extraction, database work and geofiltering were excluded.

Retained probability vectors and1280-element embeddings matched bit-for-bit on all tested inputs; input hashes and top-ten order also matched. These limited samples are not independent accuracy validation. The full original model resumed after the trial; a verified regional class list and full-pipeline checks are required before production use of a regional variant.

## Full pipeline profiling, 2026-10-08

Three passes of fixed MP3/15 s and FLAC/30 s copies used the full V3, XNNPACK and two threads with recording paused. Excluding the first pass, total time was 7.480/14.940 s, inference 7.147/14.400 s, decoding 0.181/0.286 s and reading/resampling 0.115/0.214 s. Neither sample produced detections. Inference accounted for 95.5–96.4% of these file times; timings are not a mixed-queue throughput guarantee. Database operations used an isolated backup; synthetic detections separately exercised insertion and extraction.

A five-pass interleaved extraction comparison excluded the first pass and included parent plus child CPU time. One clip averaged 0.301 s with SoX versus 0.331 s with SoundFile (CPU 0.295/0.116 s); ten clips averaged 3.971/3.103 s (CPU 3.969/1.600 s). Native ten-clip times ranged from 2.162 to 5.201 s versus 3.949–3.987 s for SoX. PCM, frame counts, rate and subtype matched, while FLAC file sizes differed slightly. Lower native CPU did not establish a consistent latency improvement, so production extraction remains SoX. Swap/I/O remains an untested explanation for the variability. No memory policy was changed.

## Swap policy screening, 2026-10-08

A reversible 60/100/60 swappiness trial loaded full V3 in three independent processes, processing the same MP3/15 s and FLAC/30 s copies three times. Warm times excluding the first pass were MP3 7.242/7.735/7.098 s and FLAC 15.422/14.456/14.729 s. The candidate's combined pair time differed by approximately 0.25% from the average controls, within observed variation. Predictions, detections and WAV hashes matched across all 18 file passes. System-wide swap traffic increased at 100; these counters include model startup and zram, not only disk swap or inference. Temperature was not controlled. Original swappiness 60 was restored, with no persistent change.

During validation, the local Orange Pi integration's missing os import in the extended geographic worker was fixed. Both geographic branches now have regression coverage, and the successful trial loaded the real geographic and acoustic models three times. This fix is included in the local release delta.

## Earlier exploratory thread comparison, superseded for selection

The first comparison below was affected by recording restarting after concurrent settings changes during the four-thread stage. It is exploratory data, not a controlled thread-count comparison; use the controlled repeat above to select the thread count.

Measured 2026-10-08 on the Trixie test card with the V3 preview3.1 pruned model, two fixed 15-second MP3 copies and microphone recording paused. CPU policy remained ondemand 600–1000 MHz. These results do not describe recognition accuracy or electrical power consumption.

| Experiment | Warm average per 15-second file | CPU seconds per file |
| --- | ---: | ---: |
| Two threads, first run | 7.34 s | 13.41 s |
| Four threads | 12.99 s | 25.62 s |
| Two threads, control run | 8.91 s | 14.65 s |

Each thread mode processed both samples three times; the first pass was excluded from warm averages. Top-three species and probabilities matched exactly across all corresponding windows. These timings were confounded by concurrent recording and cannot establish a thread-count benefit. Temperature ranged from 62.8 to 79.5°C, observed frequencies from 700 to 1000 MHz, and the final firmware throttling status was 0x0. Frequency and thermal conditions were not fixed, and runtime varied.

Most time was spent in neural-network inference: 6.62 s of the first two-thread average of 7.34 s. Decoding took 0.24 s and reading/resampling 0.10 s. Top-k prediction selection and vector audio processing were already present. Larger model batches or multiple analyzer processes were not adopted: this experiment's analyzer RSS plus swap was approximately 493–495 MiB on a device with 462 MiB RAM.

Calling malloc_trim released about 5 MiB temporarily; the following files allocated most of it again. It did not improve speed and was not added to production.

An additional cache phase avoided reparsing the language JSON and V3 label CSV for every file. Warm total time was 8.70 s versus the preceding control's 8.91 s, but inference time also varied, so this is not a reliable overall speedup percentage. Time outside decoding, reading/resampling and analysis fell from roughly 0.70 to 0.04 s in these samples. Cached predictions remained equal. The cache was adopted with file-version invalidation; five isolated tests cover reuse and JSON/CSV, language/model and atomic replacement changes.

After deployment, observed real-queue files commonly took approximately 6.8–7.2 s, with occasional longer files. This is not a sustained throughput or worst-case guarantee. The benchmark did not extract clips or write detections to the database; files with detections can incur additional reporting work. Independent recognition validation, extensive audio coverage and a fresh-install/update test remain separate checks.
