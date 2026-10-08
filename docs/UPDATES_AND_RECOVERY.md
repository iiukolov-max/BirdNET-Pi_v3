# Updates, fork migration and recovery

This candidate has been checked with local Git and SQLite fixtures. Privileged service changes, dependency installation and model loading were simulated in those tests. A full device upgrade and a fresh hardware installation remain untested. Keep an existing card available for playback; use a separate card for installation testing.

## Fresh installation versus migration

`newinstaller.sh` is for a new installation under the current regular user account. It refuses an existing application directory or configuration. It never replaces an existing installation or requests an automatic reboot.

An existing installation must first preserve and integrate its local modifications. The updater refuses modified tracked files, staged changes, diverged history and collisions with untracked files. It uses this fork's `origin/main`, including when the installed code originally came from a tag.

Once the candidate code is installed in a suitable isolated installation, preview the remote migration:

```bash
python3 /home/pi/BirdNET-Pi/scripts/migrate_fork.py
```

To apply that separate remote migration:

```bash
python3 /home/pi/BirdNET-Pi/scripts/migrate_fork.py --apply
```

It creates a private backup, preserves the previous origin as `upstream` (or an unused numbered name), and configures this fork as origin. It does not download application code, restart services or remove local edits. It is not a method for deploying this candidate into an old installation. If local edits remain, Update will still refuse them until they have been preserved and integrated.

## Update behaviour

Tools → System Controls → Update performs a fast-forward from origin/main. It does not run `git reset --hard` or `git clean`. Automatic updates remain controlled by the existing `AUTOMATIC_UPDATE` setting.

Before changing application code it saves:

- A consistent SQLite backup verified with `integrity_check`, including committed data in WAL.
- Configuration and existing model profiles.
- The committed code archive and original commit ID.
- Separate patches for working-tree and staged edits, useful for remote migration.

Backup directories use mode 0700 and files 0600. They contain private settings and must not be uploaded with release artifacts. Audio remains in its original location; these backups are **not full audio backups**.

The updater then verifies/downloads model artifacts, installs the additional dependencies, migrates review storage, updates labels, and restarts only the inference worker. It waits for that worker's model/PID readiness marker. It does not restart the recorder or alter CPU, radio or boot settings.

## Failure and recovery

A failed step exits with an error and the backup location. There is no automatic complete rollback. In particular, application code may already have advanced before a dependency or readiness error. Do not repeatedly press Update hoping to undo that state: an unchanged HEAD currently reports up to date rather than rerunning failed installation steps.

First preserve the latest database using the SQLite backup API. Do not copy only an active `birds.db` with a shell file copy: committed records can still reside in its WAL. Keep recording and all audio archives in place.

Prefer fixing the reported failing step and checking readiness. If code must be recovered, use the original commit in the backup metadata and restore application code separately from runtime data. A code-only restoration was checked on a fixture: detections added **after** the original backup survived, along with existing review marks and audio.

Before any real restoration, inspect the tracked files and local changes. Restoring tracked code can overwrite later code edits and change dependencies needed by the worker. Keep the current configuration, profiles, database, export and recordings out of that operation. The committed archive does not include untracked local scripts; preserve those separately. A fully automated device rollback is not provided by this candidate.

Never replace the current detection database with the pre-update snapshot merely to recover application code. That would discard detections/reviews recorded after the snapshot. Restore a database backup only for an actual database recovery, with a separate plan for newer records.

For returning to an older model while the web interface works, use Tools → Settings. Its model-switch transaction restores the prior model/configuration on startup failure; this is separate from recovering an entire software update.
