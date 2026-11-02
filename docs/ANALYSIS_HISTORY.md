# Archive analysis history

Local and PC archive analysis keep durable per-recording results in the
`archive_analysis_results` table of `scripts/birds.db`. The existing
`archive_processed` completion ledger remains compatible with older code.
Successful results and detection counts commit in the same transaction as
completion. Failed attempts record an error and do not mark the file completed.
History remains available after the original audio is removed.

Each result contains the original filename, size and modification timestamp,
analysis time, local/remote backend, outcome, detection count, error and evidence
source. A count of -1 means unknown or failed, never zero. Local timing covers
the cycle through saving results; remote timing is the PC's reported analysis
time. This history covers archive analysis, not the separate continuous recorder.

On the Pi:

```sh
cd ~/BirdNET-Pi
birdnet/bin/python3 scripts/archive_analysis_history.py --limit 50
birdnet/bin/python3 scripts/archive_analysis_history.py --limit -1 --format csv > analysis-history.csv
```

`evidence=live` denotes a newly committed result. Recovered history must be
labelled `journal_recovered`, or `completion_only` when an older completion is
known but the outcome is unknown. Such recovery is not an original raw log.

Remote analysis removes an unchanged, unshared original only after a durable
zero-detection result. Positive, unknown and failed results retain their source.
Deletion errors are logged separately and do not invalidate committed results.
No calendar-based deletion rule is installed.
