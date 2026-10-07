"""Run the actual updater against local Git/SQLite fixtures; privileged actions are stubbed."""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SOURCE / 'scripts'))
from migrate_fork import migrate, FORK


def command(*args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()


def git(root, *args):
    return command('git', '-C', str(root), *args)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o755)


def rows(path, table):
    connection = sqlite3.connect(path)
    try:
        return connection.execute('SELECT * FROM ' + table + ' ORDER BY rowid').fetchall()
    finally:
        connection.close()


def fixture(base):
    base.mkdir(parents=True)
    remote, seed, root = base / 'remote.git', base / 'seed', base / 'installation'
    command('git', 'init', '--bare', str(remote))
    command('git', 'init', '-b', 'main', str(seed))
    git(seed, 'config', 'user.name', 'Fixture')
    git(seed, 'config', 'user.email', 'fixture@example.invalid')
    for name in ('update_birdnet.sh', 'backup_before_update.py', 'migrate_review_db.py'):
        write(seed / 'scripts' / name, (SOURCE / 'scripts' / name).read_text())
    write(seed / 'scripts/download_v3.py', 'print("Fixture model verified")\n')
    write(seed / 'scripts/check_model_ready.py', 'import os,sys; sys.exit(1 if os.environ.get("BIRDNET_TEST_FAIL") == "ready" else 0)\n')
    write(seed / 'scripts/install_language_label.sh', '#!/bin/sh\nexit 0\n')
    write(seed / 'scripts/install_startup_logging.sh', '#!/bin/sh\nexit 0\n')
    write(seed / 'scripts/install_audio_runtime.sh', '#!/bin/sh\nexit 0\n')
    write(seed / '.gitignore', 'scripts/birds.db*\n.model-profiles.json\nbirdnet.conf\nBirdSongs/\nbirdnet/\n.release-update.lock\n')
    write(seed / 'version.txt', 'old\n')
    git(seed, 'add', '.')
    git(seed, 'commit', '-m', 'Initial fixture')
    old = git(seed, 'rev-parse', 'HEAD')
    git(seed, 'remote', 'add', 'origin', str(remote))
    git(seed, 'push', 'origin', 'main')
    command('git', 'clone', '--branch', 'main', str(remote), str(root))
    git(root, 'config', 'user.name', 'Fixture')
    git(root, 'config', 'user.email', 'fixture@example.invalid')
    git(root, 'remote', 'set-url', 'origin', FORK)
    # Use the official-looking origin but route Git's transport to a local bare repo.
    git(root, 'config', 'url.' + remote.as_uri() + '.insteadOf', FORK)
    write(seed / 'version.txt', 'new\n')
    git(seed, 'add', 'version.txt')
    git(seed, 'commit', '-m', 'New fixture release')
    git(seed, 'push', 'origin', 'main')
    database = root / 'scripts/birds.db'
    connection = sqlite3.connect(database)
    connection.executescript("PRAGMA journal_mode=WAL; CREATE TABLE detections (File_Name TEXT); INSERT INTO detections VALUES ('bird.wav');"
                             "CREATE TABLE detection_reviews (file_path TEXT PRIMARY KEY, review_status TEXT NOT NULL, reviewed_at TEXT NOT NULL);"
                             "INSERT INTO detection_reviews VALUES ('day/bird.wav', 'correct', 'fixture-time');")
    connection.commit()
    # Keep this connection open, exercising backup of an active WAL database.
    write(root / 'birdnet.conf', 'BIRDNET_USER=fixture\nAUTOMATIC_UPDATE=0\nMODEL=fixture-model\n')
    write(root / '.model-profiles.json', '{"fixture-model":{"CONFIDENCE":"0.6"}}\n')
    write(root / 'BirdSongs/record.wav', 'fixture audio\n')
    write(root / 'birdnet/bin/python3', '#!/bin/sh\n[ "${BIRDNET_TEST_FAIL:-}" != pip ]\n')
    stub = base / 'bin'
    write(stub / 'sudo', '''#!/bin/sh
if [ "$1" = -u ]; then shift 2; exec "$@"; fi
case "$1" in
  install) exit 0 ;;
  tee) cat >/dev/null; exit 0 ;;
  systemctl) printf '%s\n' "$*" >> "$BIRDNET_TEST_SERVICE_LOG"; exit 0 ;;
  *) exec "$@" ;;
esac
''')
    env = dict(os.environ, PATH=str(stub) + ':' + os.environ['PATH'],
               BIRDNET_CONFIG=str(root / 'birdnet.conf'), BIRDNET_TEST_SERVICE_LOG=str(base / 'services.log'))
    return root, old, connection, env


def run(root, env, *args):
    script = root / 'scripts/update_birdnet.sh'
    if env.get('BIRDNET_TEST_SYMLINK'):
        script = root.parent / 'global-bin/update_birdnet.sh'
        script.parent.mkdir()
        script.symlink_to(root / 'scripts/update_birdnet.sh')
    return subprocess.run(['bash', str(script), *args],
                          env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def main():
    completed = []
    with tempfile.TemporaryDirectory(prefix='birdnet-update-fixtures-') as directory:
        base = Path(directory)
        for scenario in ('success', 'symlink-success', 'dirty', 'staged', 'diverged', 'wrong-origin', 'auto-disabled', 'collision', 'pip-failure', 'ready-failure'):
            root, old, connection, env = fixture(base / scenario)
            try:
                database = root / 'scripts/birds.db'
                initial = {name: rows(database, name) for name in ('detections', 'detection_reviews')}
                saved = {path: (root / path).read_bytes() for path in ('birdnet.conf', '.model-profiles.json', 'BirdSongs/record.wav')}
                if scenario == 'symlink-success': env['BIRDNET_TEST_SYMLINK'] = '1'
                if scenario in ('dirty', 'staged'):
                    write(root / 'version.txt', 'local edit\n')
                    if scenario == 'staged': git(root, 'add', 'version.txt')
                elif scenario == 'diverged':
                    write(root / 'local.txt', 'local commit\n')
                    git(root, 'add', 'local.txt'); git(root, 'commit', '-m', 'Local divergence')
                elif scenario == 'wrong-origin':
                    git(root, 'remote', 'set-url', 'origin', 'https://github.com/Nachtzuster/BirdNET-Pi.git')
                elif scenario in ('pip-failure', 'ready-failure'):
                    env['BIRDNET_TEST_FAIL'] = 'pip' if scenario == 'pip-failure' else 'ready'
                elif scenario == 'collision':
                    seed = base / scenario / 'seed'
                    write(seed / 'collision.txt', 'upstream addition\n')
                    git(seed, 'add', 'collision.txt'); git(seed, 'commit', '-m', 'Collision fixture'); git(seed, 'push', 'origin', 'main')
                    write(root / 'collision.txt', 'private untracked file\n')
                before_head = git(root, 'rev-parse', 'HEAD')
                result = run(root, env, *(['-a'] if scenario == 'auto-disabled' else []))
                if scenario in ('success', 'symlink-success', 'auto-disabled'):
                    assert result.returncode == 0, (scenario, result.stdout)
                else:
                    assert result.returncode != 0, (scenario, result.stdout)
                for name, expected in initial.items(): assert rows(database, name) == expected, scenario
                for path, expected in saved.items(): assert (root / path).read_bytes() == expected, scenario
                if scenario not in ('success', 'symlink-success', 'pip-failure', 'ready-failure'):
                    assert git(root, 'rev-parse', 'HEAD') == before_head, scenario
                if scenario in ('dirty', 'staged'): assert (root / 'version.txt').read_text() == 'local edit\n'
                if scenario == 'collision': assert (root / 'collision.txt').read_text() == 'private untracked file\n'
                if scenario in ('success', 'symlink-success', 'pip-failure', 'ready-failure', 'collision'):
                    backups = list((root.parent / 'birdnet-backups').glob('update-*'))
                    assert len(backups) == 1
                    backup = backups[0]
                    assert json.loads((backup / 'metadata.json').read_text())['commit'] == old
                    for name, expected in initial.items(): assert rows(backup / 'birds.db', name) == expected
                    assert backup.stat().st_mode & 0o777 == 0o700
                    assert (backup / 'birdnet.conf').stat().st_mode & 0o777 == 0o600
                if scenario in ('success', 'symlink-success'):
                    assert (root / 'version.txt').read_text() == 'new\n'
                    assert 'restart birdnet_analysis.service' in Path(env['BIRDNET_TEST_SERVICE_LOG']).read_text()
                if scenario == 'pip-failure': assert not Path(env['BIRDNET_TEST_SERVICE_LOG']).exists()
                if scenario == 'ready-failure':
                    assert 'Update failed' in result.stdout
                    # Restore application code only; newer detections must survive.
                    connection.execute("INSERT INTO detections VALUES ('new-after-backup.wav')"); connection.commit()
                    git(root, 'restore', '--source=' + old, '--staged', '--worktree', '--', '.')
                    assert (root / 'version.txt').read_text() == 'old\n'
                    assert rows(database, 'detections') == [('bird.wav',), ('new-after-backup.wav',)]
                    assert rows(database, 'detection_reviews') == initial['detection_reviews']
                completed.append(scenario)
            finally:
                connection.close()
        root, old, connection, env = fixture(base / 'migration')
        try:
            git(root, 'remote', 'set-url', 'origin', 'https://github.com/Nachtzuster/BirdNET-Pi.git')
            git(root, 'remote', 'add', 'upstream', 'https://example.invalid/existing-upstream')
            write(root / 'version.txt', 'local edit to preserve\n')
            result = migrate(root, root / 'birdnet.conf', root.parent / 'migration-backups')
            assert result['preserved_remote'] == 'upstream-original-1'
            assert git(root, 'config', '--get', 'remote.origin.url') == FORK
            assert git(root, 'remote', 'get-url', 'upstream-original-1') == 'https://github.com/Nachtzuster/BirdNET-Pi.git'
            assert (root / 'version.txt').read_text() == 'local edit to preserve\n'
            assert 'local edit to preserve' in (Path(result['backup']) / 'working-tree.patch').read_text()
            assert git(root, 'rev-parse', 'HEAD') == old
            assert migrate(root, root / 'birdnet.conf', root.parent / 'migration-backups')['changed'] is False
            completed += ['migration preserves old remote and local edits', 'migration idempotence', 'code-only recovery preserves newer detections']
        finally:
            connection.close()
    print(json.dumps({'passed': True, 'checks': completed,
                      'scope': 'Real local Git and SQLite; sudo/systemd/dependency/model steps stubbed. No hardware update or live data changes.'}))


if __name__ == '__main__':
    main()
