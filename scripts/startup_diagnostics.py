#!/usr/bin/env python3
"""Record boot, service startup and kernel-detected RTC information without changing clocks."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess


def read(path):
    try:
        return Path(path).read_text().strip()
    except (OSError, UnicodeError):
        return None


def command(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=8)
        return {"exit_code": result.returncode, "output": result.stdout.strip(),
                "error": result.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"exit_code": None, "error": str(error)}


def properties(args):
    result = command(args)
    if result.get("exit_code") != 0:
        return {"query_error": result}
    return dict(line.split("=", 1) for line in result["output"].splitlines() if "=" in line)


def snapshot():
    now = dt.datetime.now(dt.timezone.utc)
    uptime = float(Path("/proc/uptime").read_text().split()[0])
    rtc_devices = []
    for device in sorted(Path("/sys/class/rtc").glob("rtc*")):
        driver_path = device / "device/driver"
        rtc_devices.append({"device": "/dev/" + device.name,
                            "name": read(device / "name"),
                            "driver": driver_path.resolve().name if driver_path.exists() else None,
                            "date": read(device / "date"), "time": read(device / "time"),
                            "since_epoch": read(device / "since_epoch"),
                            "hctosys": read(device / "hctosys")})
    services = {}
    for unit in ("birdnet_analysis.service", "birdnet_recording.service", "caddy.service"):
        state = properties(["systemctl", "show", unit, "--no-pager",
                            "-p", "LoadState", "-p", "ActiveState", "-p", "SubState",
                            "-p", "Result", "-p", "NRestarts", "-p", "ExecMainStartTimestamp",
                            "-p", "ExecMainStartTimestampMonotonic", "-p", "ActiveEnterTimestampMonotonic"])
        # Monotonic values remain meaningful when NTP corrects the wall clock.
        for source, destination in (("ExecMainStartTimestampMonotonic", "process_start_seconds_after_boot"),
                                    ("ActiveEnterTimestampMonotonic", "active_seconds_after_boot")):
            value = state.get(source, "")
            if value.isdigit() and int(value):
                state[destination] = int(value) / 1_000_000
        services[unit] = state
    return {"schema_version": 1, "event": "time_and_rtc_snapshot",
            "observed_at_utc": now.isoformat(), "observed_at_local": now.astimezone().isoformat(),
            "boot_id": read("/proc/sys/kernel/random/boot_id"),
            "uptime_seconds": uptime,
            "boot_time_utc_estimate": (now - dt.timedelta(seconds=uptime)).isoformat(),
            "clock": properties(["timedatectl", "show", "-p", "Timezone", "-p", "NTPSynchronized",
                                 "-p", "NTP", "-p", "LocalRTC"]),
            "rtc_detected_by_kernel": bool(rtc_devices), "rtc_devices": rtc_devices,
            "rtc_read": command(["hwclock", "--show"]) if rtc_devices else None,
            "services": services}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-file", type=Path, help="Append one JSON record; omit to print only")
    args = parser.parse_args()
    record = snapshot()
    line = json.dumps(record, ensure_ascii=False)
    if args.log_file:
        args.log_file.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(args.log_file, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o640)
        with os.fdopen(descriptor, "a", encoding="utf-8") as output:
            output.write(line + "\n")
    print(line, flush=True)


if __name__ == "__main__":
    main()
