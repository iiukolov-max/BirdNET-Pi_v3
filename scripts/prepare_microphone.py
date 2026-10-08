#!/usr/bin/env python3
"""Find an ALSA capture device and maximise capture controls; stdout is the PCM name."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time


def run(args, timeout=10):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, "", str(error)


def log(event, **fields):
    print(json.dumps({"event": event, **fields}, ensure_ascii=False), file=sys.stderr, flush=True)


def needs_pulse(device):
    return device.strip() in ('','default','auto','pulse') or device.strip().startswith('pulse:')


def ensure_pulse():
    code,_,_=run(['pulseaudio','--check'])
    if code:
        code,_,error=run(['pulseaudio','--start'])
        if code:raise RuntimeError('PulseAudio could not start: '+error.strip())


def release_idle_pulse_source(card):
    """Leave a shared audio server running; suspend only an unused matching source."""
    code,output,_=run(['pactl','--format=json','list','sources'])
    if code:return
    matching=[s for s in json.loads(output) if str(s.get('properties',{}).get('alsa.card'))==str(card['number'])]
    code,output,error=run(['pactl','--format=json','list','source-outputs'])
    if code:raise RuntimeError('Cannot check PulseAudio capture users: '+error.strip())
    clients=json.loads(output)
    for source in matching:
        if any(str(c.get('source'))==str(source.get('index')) for c in clients):
            raise RuntimeError('Direct ALSA device has active PulseAudio users; use pulse or shared dsnoop')
        code,_,error=run(['pactl','suspend-source',source['name'],'1'])
        if code:raise RuntimeError('Cannot release idle PulseAudio source: '+error.strip())


def capture_devices(output):
    return [{"number": int(number), "id": identifier, "device": int(device), "description": description}
            for number, identifier, description, device in
            re.findall(r"^card (\d+): ([^ ]+) \[([^\n]+?)\], device (\d+):", output, re.M)]


def maximise_capture(card):
    code, output, error = run(["amixer", "-c", card, "scontrols"])
    if code:
        log("microphone_mixer_error", card=card, error=error.strip())
        return
    changed = []
    for name, index in re.findall(r"^Simple mixer control '(.*)',(\d+)$", output, re.M):
        control = name + "," + index
        code, details, error = run(["amixer", "-c", card, "sget", control])
        if code:
            log("microphone_control_error", control=control, error=error.strip())
            continue
        match = re.search(r"^\s*Capabilities: (.*)$", details, re.M)
        capabilities = set(match.group(1).split()) if match else set()
        settings = []
        if "cvolume" in capabilities:
            settings.append("100%")
        if "cswitch" in capabilities:
            settings.append("cap")
        if not settings:
            continue  # Never adjust playback volume or unrelated controls.
        code, result, error = run(["amixer", "-c", card, "sset", control, "capture", *settings])
        log("microphone_capture_control", card=card, control=control,
            requested=settings, success=code == 0, result=result.strip(), error=error.strip())
        if code == 0:
            changed.append(control)
    if not changed:
        log("microphone_no_adjustable_capture_controls", card=card)


def select_pulse_source(card):
    source = None
    for attempt in range(3):
        code, output, error = run(["pactl", "--format=json", "list", "sources"], timeout=30)
        if code == 0:
            try:
                sources = json.loads(output)
                source = next((item["name"] for item in sources if item["name"].startswith("alsa_input.")
                               and str(item.get("properties", {}).get("alsa.card")) == str(card["number"])), None)
            except (ValueError, KeyError, TypeError):
                source = None
        if source:
            break
        if attempt < 2:
            time.sleep(1)
    if code:
        log("microphone_pulse_error", error=error.strip())
        return False
    if source is None:
        log("microphone_pulse_source_missing", card=card["id"])
        return False
    for args in (["pactl", "set-default-source", source], ["pactl", "suspend-source", source, "0"], ["pactl", "set-source-mute", source, "0"]):
        code, _, error = run(args)
        if code:
            log("microphone_pulse_error", error=error.strip())
            return False
    log("microphone_pulse_source", source=source)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="default")
    parser.add_argument("--pulse", action="store_true", help="Use shared PulseAudio capture for auto-selected hardware")
    args = parser.parse_args()
    configured = args.device.strip()
    if args.pulse and needs_pulse(configured):ensure_pulse()
    devices=[]
    for attempt in range(5):
        code, listing, error = run(["arecord", "-l"])
        devices = capture_devices(listing)
        if devices:break
        if attempt<4:time.sleep(1)
    if not devices:
        log("microphone_not_found", error=error.strip())
        return 1
    if configured in ("", "default", "auto"):
        devices.sort(key=lambda item: ("usb" not in str(Path(
            "/sys/class/sound/card" + str(item["number"])).resolve()).lower(), item["number"], item["device"]))
        selected = devices[0]
        pcm = "plughw:CARD={id},DEV={device}".format(**selected)
        if args.pulse:
            if not select_pulse_source(selected):
                return 1
            pcm = "pulse"
    else:
        match = re.fullmatch(r"(?:plug)?hw:(?:CARD=)?([^,]+)(?:,(?:DEV=)?(\d+))?", configured)
        if not match:
            log("microphone_custom_pcm", device=configured,
                message="Custom ALSA PCM retained; hardware gain cannot be determined automatically")
            print(configured)
            return 0
        selected = next((item for item in devices if match.group(1) in
                         (item["id"], str(item["number"])) and item["device"] == int(match.group(2) or 0)), None)
        if selected is None:
            log("microphone_configured_device_missing", device=configured, available=devices)
            return 1
        pcm = configured
        release_idle_pulse_source(selected)
    log("microphone_selected", pcm=pcm, hardware=selected, available=devices)
    maximise_capture(selected["id"])
    print(pcm, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
