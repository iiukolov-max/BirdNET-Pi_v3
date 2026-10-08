#!/usr/bin/env python3
"""Show recorded boot snapshots without taking a new sample or changing clocks."""
import argparse
import datetime as dt
import gzip
import json
import os
from pathlib import Path
import sys


def load_records(path):
    records = {}
    invalid = 0
    paths = sorted(path.parent.glob(path.name + '.*')) + [path]
    for source in paths:
        if not source.is_file():
            continue
        opener = gzip.open if source.suffix == '.gz' else open
        try:
            with opener(source, 'rt', encoding='utf-8') as stream:
                for line in stream:
                    try:
                        record = json.loads(line)
                        if not isinstance(record, dict) or not record.get('boot_id'):
                            raise ValueError('missing boot ID')
                        key = record['boot_id']
                        if key not in records or record.get('observed_at_utc', '') > records[key].get('observed_at_utc', ''):
                            records[key] = record
                    except (ValueError, TypeError):
                        invalid += 1
        except (OSError, UnicodeError, EOFError) as error:
            print(f'Не удалось прочитать {source.name}: {error}', file=sys.stderr)
    return sorted(records.values(), key=lambda r: r.get('observed_at_utc', '')), invalid


def publish_history(log_file, output_file):
    records, _ = load_records(log_file)
    rows = [{'time': r.get('observed_at_local'),
             'rtc': r.get('rtc_detected_by_kernel') if isinstance(r.get('rtc_detected_by_kernel'), bool) else None}
            for r in records[-5:][::-1]]
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_file.with_name('.' + output_file.name + '.tmp')
    temporary.write_text(json.dumps(rows), encoding='utf-8')
    os.chmod(temporary, 0o644)
    os.replace(temporary, output_file)


def timestamp(value):
    try:
        return dt.datetime.fromisoformat(value).strftime('%Y-%m-%d %H:%M:%S %z')
    except (ValueError, TypeError):
        return 'нет данных'


def render(record):
    lines = [f"Запуск {str(record.get('boot_id', '?'))[:8]}",
             f"  Системное время при проверке: {timestamp(record.get('observed_at_local'))}"]
    boot = record.get('boot_time_utc_estimate')
    try:
        zone = dt.datetime.fromisoformat(record['observed_at_local']).tzinfo
        boot = dt.datetime.fromisoformat(boot).astimezone(zone).isoformat()
    except (KeyError, ValueError, TypeError):
        pass
    lines.append(f'  Включение: {timestamp(boot)} (оценка по системным часам)')
    devices = record.get('rtc_devices') or []
    if not record.get('rtc_detected_by_kernel'):
        lines.append('  RTC: не обнаружены; время RTC недоступно')
    elif not devices:
        lines.append('  RTC: обнаружены; данные устройства отсутствуют')
    for device in devices:
        value = 'нет данных'
        try:
            value = dt.datetime.fromtimestamp(int(device['since_epoch']), dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        except (KeyError, ValueError, TypeError, OverflowError, OSError):
            if device.get('date') and device.get('time'):
                value = f"{device['date']} {device['time']} (часы RTC)"
        lines.append(f"  RTC {device.get('device', '?')} ({device.get('name') or 'без имени'}): {value}")
        lines.append('    Источник системного времени при загрузке: ' + ('да' if str(device.get('hctosys')) == '1' else 'нет/не подтверждён'))
    reading = record.get('rtc_read') or {}
    if reading.get('error') or reading.get('exit_code') not in (None, 0):
        lines.append('  Чтение RTC: ошибка — ' + (reading.get('error') or 'hwclock не смог прочитать часы'))
    elif reading.get('output'):
        lines.append('  hwclock: ' + reading['output'])
    clock = record.get('clock') or {}
    sync = {'yes': 'да', 'no': 'нет'}.get(clock.get('NTPSynchronized'), 'нет данных')
    lines.append(f"  Часовой пояс: {clock.get('Timezone', 'нет данных')}; синхронизация NTP: {sync}")
    for unit, name in (('birdnet_recording.service', 'Запись'), ('birdnet_analysis.service', 'Анализ'), ('caddy.service', 'Веб-сервер')):
        service = (record.get('services') or {}).get(unit, {})
        elapsed = service.get('process_start_seconds_after_boot')
        timing = f'через {elapsed:.1f} с' if isinstance(elapsed, (int, float)) else 'время запуска отсутствует'
        state = {'active': 'работает', 'inactive': 'остановлен', 'failed': 'ошибка'}.get(service.get('ActiveState'), service.get('ActiveState', 'нет данных'))
        lines.append(f"  {name}: {state}, {timing}; перезапусков: {service.get('NRestarts', '?')}")
    return '\n'.join(lines)


def render_compact(record):
    try:
        system_time = dt.datetime.fromisoformat(record['observed_at_local']).isoformat(timespec='seconds')
    except (KeyError, ValueError, TypeError):
        system_time = 'unavailable'
    uptime = record.get('uptime_seconds')
    uptime = f'{int(uptime)}s' if isinstance(uptime, (int, float)) else 'unavailable'
    reading = record.get('rtc_read') or {}
    rtc = reading.get('output') if reading.get('exit_code') == 0 else None
    rtc = ' '.join(rtc.splitlines()) if rtc else 'unavailable (hwclock read failed)'
    clock = record.get('clock') or {}
    values = [clock.get(key) or 'unavailable' for key in ('NTPSynchronized', 'TimeUSec', 'RTCTimeUSec')]
    return '\n'.join(['----- boot -----',
                      f"ts_sys={system_time} host={record.get('hostname') or 'unavailable'} uptime={uptime}",
                      f'rtc={rtc}', 'timedatectl: ' + ' '.join(values)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log-file', type=Path, default=Path('/var/log/birdnet/startup.jsonl'))
    parser.add_argument('--last', type=int, default=10, help='Number of most recent boots (default: 10)')
    parser.add_argument('--all', action='store_true', help='Show all retained boots, including rotated logs')
    parser.add_argument('--verbose', action='store_true', help='Show detailed RTC and service diagnostics')
    parser.add_argument('--publish-json', type=Path, help='Export only the five latest boot dates and RTC presence')
    args = parser.parse_args()
    if args.last < 1:
        parser.error('--last must be positive')
    if args.publish_json:
        publish_history(args.log_file, args.publish_json)
        return
    records, invalid = load_records(args.log_file)
    if invalid:
        print(f'Пропущено повреждённых записей: {invalid}', file=sys.stderr)
    if not records:
        print('Записей о запуске пока нет. Снимок сохраняется один раз, примерно через 15 секунд после включения.')
        return
    renderer = render if args.verbose else render_compact
    print('\n\n'.join(renderer(r) for r in (records if args.all else records[-args.last:])))
    if args.verbose:
        print('\nЭто сохранённые снимки после включения, а не текущее состояние. RTC и системные часы прочитаны последовательно.')


if __name__ == '__main__':
    main()
