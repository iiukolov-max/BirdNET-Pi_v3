"""Integration test against a disposable PHP server and generated SQLite fixture."""
import json
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request


def main():
    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix='birdnet-review-http-') as directory:
        fixture = Path(directory)
        (fixture / 'scripts').mkdir()
        shutil.copy2(root / 'scripts/play.php', fixture / 'play.php')
        (fixture / 'scripts/common.php').write_text('''<?php
session_start();
$_SESSION['review_csrf'] = str_repeat('a', 64);
function get_home() { return '/fixture'; }
function get_user() { return 'fixture'; }
function get_config() { return []; }
function ensure_authenticated($message='') {
  if (($_SERVER['HTTP_X_TEST_AUTH'] ?? '') !== 'yes') { http_response_code(401); die('Authentication required'); }
}
function ensure_db_ok($statement) { if (!$statement) { http_response_code(500); die('Database error'); } }
''')
        database = fixture / 'scripts/birds.db'
        connection = sqlite3.connect(database)
        connection.executescript("CREATE TABLE detections (File_Name TEXT); INSERT INTO detections VALUES ('bird.wav');"
                                 "CREATE TABLE detection_reviews (file_path TEXT PRIMARY KEY, review_status TEXT NOT NULL, reviewed_at TEXT NOT NULL);")
        connection.commit()
        connection.close()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        server = subprocess.Popen(['php', '-S', '127.0.0.1:' + str(port), '-t', str(fixture)],
                                  cwd=fixture, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            url = 'http://127.0.0.1:' + str(port) + '/play.php'

            def request(fields=None, authenticated=True, query=''):
                headers = {'X-Test-Auth': 'yes'} if authenticated else {}
                data = urllib.parse.urlencode(fields).encode() if fields is not None else None
                try:
                    with urllib.request.urlopen(urllib.request.Request(url + query, data=data, headers=headers), timeout=5) as response:
                        return response.status, response.read().decode()
                except urllib.error.HTTPError as error:
                    return error.code, error.read().decode()

            for _ in range(50):
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=.1):
                        break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Fixture PHP server failed to start')
            assert request(query='?reviewfile=bird.wav&status=correct')[0] == 405
            fields = {'reviewfile': 'date/species/bird.wav', 'status': 'correct', 'csrf': 'a' * 64}
            assert request(fields, authenticated=False)[0] == 401
            assert request(dict(fields, csrf='wrong'))[0] == 403
            for status in ('correct', 'false_positive', 'unreviewed'):
                assert request(dict(fields, status=status)) == (200, 'OK')
                connection = sqlite3.connect(database)
                try:
                    actual = connection.execute('SELECT review_status FROM detection_reviews').fetchall()
                    assert actual == ([] if status == 'unreviewed' else [(status,)])
                    assert connection.execute('SELECT * FROM detections').fetchall() == [('bird.wav',)]
                finally:
                    connection.close()
            assert 'invalid status' in request(dict(fields, status='other'))[1]
            assert request(dict(fields, reviewfile='../bird.wav'))[1] == 'Error'
        finally:
            server.terminate()
            server.wait(timeout=10)
    print(json.dumps({'passed': True, 'checks': ['TP', 'FP', 'remove review', 'preserve detections', '401', '403', '405', 'invalid status', 'unsafe path'],
                      'scope': 'Disposable fixture server and database; no live user data'}))


if __name__ == '__main__':
    main()
