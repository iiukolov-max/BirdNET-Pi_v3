#!/usr/bin/env python3
"""Read retained audio diagnostics by boot, including compressed rotations."""
import argparse
import datetime as dt
import gzip
import json
from pathlib import Path
import subprocess
import sys


def load(path, include_test_events=False):
    records = []
    for source in [*path.parent.glob(path.name + '.*'), path]:
        if not source.is_file():
            continue
        try:
            with (gzip.open if source.suffix == '.gz' else open)(source, 'rt', encoding='utf-8') as stream:
                for line in stream:
                    try:
                        row = json.loads(line)
                        if isinstance(row, dict) and row.get('boot_id') and row.get('time'):
                            dt.datetime.fromisoformat(row['time'])
                            records.append(row)
                    except (ValueError, TypeError):
                        pass
        except (OSError, UnicodeError, EOFError) as error:
            print(f'{source.name}: {error}', file=sys.stderr)
    if not include_test_events:
        identities, first_times = set(), set()
        for row in records:
            if row.get('event') != 'diagnostic_test_records_excluded':
                continue
            for item in row.get('test_processes', []):
                if isinstance(item, dict) and isinstance(item.get('pid'), int):
                    identities.add((item.get('boot_id'), item['pid']))
            for item in row.get('test_first_times', []):
                if isinstance(item, dict):
                    first_times.add((item.get('boot_id'), item.get('time')))
        def synthetic(row):
            if row.get('source') != 'prepare_microphone':
                return False
            if row.get('event') == 'repeated':
                return (row.get('boot_id'), row.get('first_time')) in first_times
            return (row.get('boot_id'), row.get('pid')) in identities
        records = [row for row in records if not synthetic(row)]
    return sorted(records, key=lambda r: (r['boot_id'], r.get('uptime_seconds', 0), r['time']))


def summaries(records, active=False, current_boot=None, uptime=None):
    boots = {}
    for row in records:
        boot = boots.setdefault(row['boot_id'], {'boot_id': row['boot_id'], 'first_time': row['time'],
                    'last_time': row['time'], 'card': 'unknown', 'segments': 0,
                    'quiet_segments': 0.0, 'repeats': {}, 'events': []})
        boot['last_time'] = row['time']
        event = row['event']
        if event in ('microphone_selected', 'sound_card_added'):
            boot['card'] = 'found'
        elif event in ('microphone_not_found', 'microphone_configured_device_missing', 'sound_card_removed'):
            boot['card'] = 'not found'
        if event == 'repeated':
            name = row.get('of', '?')
            boot['repeats'][name] = boot['repeats'].get(name, 0) + row.get('count', 0)
        if event == 'heartbeat':
            boot['segments'] += row.get('segments', 0)
            boot['quiet_segments'] += row.get('segments', 0) * row.get('quiet_fraction', 0)
        if event in ('archive_started', 'heartbeat'):
            if boot.get('expected_heartbeat') is not None and row.get('uptime_seconds', 0) - boot['expected_heartbeat'] > 2 * boot.get('interval', 900):
                boot['heartbeat_gap'] = True
            boot['expected_heartbeat'] = row.get('uptime_seconds', 0)
            boot['interval'] = row.get('interval_seconds', 900)
        if event == 'archive_stopped':
            boot['expected_heartbeat'] = None
            boot['stop_reason'] = row.get('reason')
        boot['events'].append(row)
    for boot in boots.values():
        if not boot['segments'] and any(r['event'] == 'archive_segment_completed' for r in boot['events']):
            boot['segments'] = 1
            boot['segments_pending_summary'] = True
        if (active and boot['boot_id'] == current_boot and uptime is not None
                and boot.get('expected_heartbeat') is not None
                and uptime - boot['expected_heartbeat'] > 2 * boot.get('interval', 900)):
            boot['heartbeat_gap'] = True
        boot['quiet_fraction'] = boot['quiet_segments'] / boot['segments'] if boot['segments'] else None
    return sorted(boots.values(), key=lambda b: b['first_time'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log-file', type=Path, default=Path('/var/log/birdnet/audio.jsonl'))
    parser.add_argument('--boot', help='Boot ID or unique prefix')
    parser.add_argument('--since', help='Local ISO timestamp or date')
    parser.add_argument('--json', action='store_true', help='Selected raw JSON records')
    parser.add_argument('--include-test-events', action='store_true', help='Audit known synthetic events retained in the original log')
    args = parser.parse_args()
    records = load(args.log_file, include_test_events=args.include_test_events)
    if args.boot:
        matches = {r['boot_id'] for r in records if r['boot_id'].startswith(args.boot)}
        if len(matches) > 1:
            parser.error('ambiguous boot prefix')
        records = [r for r in records if r['boot_id'] in matches]
    if args.since:
        try:
            since = dt.datetime.fromisoformat(args.since)
            if since.tzinfo is None:
                since = since.astimezone()
        except ValueError:
            parser.error('invalid --since ISO timestamp')
        records = [r for r in records if dt.datetime.fromisoformat(r['time']) >= since]
    if args.json:
        for row in records:
            print(json.dumps(row, ensure_ascii=False))
        return
    active = False
    try:
        active = subprocess.run(['systemctl', 'is-active', '--quiet', 'birdnet_recording.service'], timeout=2).returncode == 0
        current = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        uptime = float(Path('/proc/uptime').read_text().split()[0])
    except (OSError, ValueError, subprocess.TimeoutExpired):
        current, uptime = None, None
    for boot in summaries(records, active, current, uptime):
        quiet = f"{boot['quiet_fraction']:.1%}" if boot['quiet_fraction'] is not None else 'unknown'
        print(f"Boot {boot['boot_id'][:8]} {boot['first_time']} — {boot['last_time']}: "
              f"card {boot['card']}; segments confirmed {boot['segments']}; quiet {quiet}")
        for name, count in boot['repeats'].items():
            print(f'  {name}: repeated {count} times')
        if boot.get('stop_reason'):
            print('  Stopped: ' + boot['stop_reason'])
        if boot.get('heartbeat_gap'):
            print('  WARNING: heartbeat missing for more than two intervals')
    if not records:
        print('No retained audio diagnostics.')


if __name__ == '__main__':
    main()
