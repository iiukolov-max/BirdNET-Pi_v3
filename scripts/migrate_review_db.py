#!/usr/bin/env python3
"""Add review storage without deleting or relabelling existing detections."""
import argparse
import datetime
import json
from pathlib import Path
import sqlite3
import uuid


def migrate(database, backup_directory):
    if not database.is_file():
        raise FileNotFoundError('Detection database must exist before migration')
    connection = sqlite3.connect(database, timeout=60)
    try:
        if connection.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='detections'").fetchone()[0] != 1:
            raise RuntimeError('Missing detections table; refusing to initialise over unknown data')
        backup_directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        backup = backup_directory / ('birds-' + stamp + '-' + uuid.uuid4().hex[:8] + '.db')
        saved = sqlite3.connect(backup)
        try:
            connection.backup(saved, pages=256, sleep=0.01)
            if saved.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('Backup integrity check failed')
        finally:
            saved.close()
        connection.execute('BEGIN IMMEDIATE')
        connection.execute("""CREATE TABLE IF NOT EXISTS detection_reviews (
            file_path TEXT PRIMARY KEY,
            review_status TEXT NOT NULL CHECK (review_status IN ('correct','false_positive')),
            reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        connection.execute('CREATE INDEX IF NOT EXISTS idx_detection_reviews_status ON detection_reviews(review_status)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_detection_reviews_reviewed_at ON detection_reviews(reviewed_at)')
        result = {'backup': str(backup), 'detections': connection.execute('SELECT count(*) FROM detections').fetchone()[0],
                  'reviews': connection.execute('SELECT count(*) FROM detection_reviews').fetchone()[0]}
        connection.commit()
        return result
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == '__main__':
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', type=Path, default=root / 'scripts/birds.db')
    parser.add_argument('--backup-directory', type=Path, default=root.parent / 'birdnet-backups/review-migrations')
    args = parser.parse_args()
    print(json.dumps(migrate(args.database, args.backup_directory)))
