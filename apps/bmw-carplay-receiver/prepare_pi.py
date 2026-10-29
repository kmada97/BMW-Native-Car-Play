#!/usr/bin/env python3
"""One connected-Pi preparation pass: install, exercise local decoder, collect its result.

Requires an explicitly selected ADB serial. Never changes AAIdrive/My BMW, Wi-Fi, Bluetooth,
phone authentication, OS settings or firmware. Only our own previous probe is stopped.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
ADB = ROOT / 'local/tools/platform-tools/adb'
APP = 'com.kalyan.bmwcarplay'
ACTIVITY = APP + '/com.shilapi.xcertplay.bmw.BmwCheckpointActivity'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', required=True, help='Explicit Pi ADB serial; never the default device')
    parser.add_argument('--allow-emulator', action='store_true', help='Local software validation only')
    args = parser.parse_args()
    def adb(*words, timeout=30):
        return subprocess.check_output([str(ADB), '-s', args.serial, *words], timeout=timeout)
    model = adb('shell', 'getprop', 'ro.product.model').decode().strip()
    device = adb('shell', 'getprop', 'ro.product.device').decode().strip()
    if args.serial.startswith('emulator-'):
        if not args.allow_emulator: raise SystemExit('Emulator requires --allow-emulator')
    elif 'rpi4' not in device.lower() and 'raspberry pi 4' not in model.lower():
        raise SystemExit(f'Selected device is not the Pi 4 (model={model!r}, device={device!r}); no install performed')
    if adb('shell', 'getprop', 'sys.boot_completed').strip() != b'1':
        raise SystemExit('Selected device has not finished booting')
    output = ROOT / 'outputs/bmw-carplay-receiver'
    build = json.loads((output / 'build-result.json').read_text())
    apk = output / 'bmw-carplay-receiver-checkpoint-1.apk'
    if hashlib.sha256(apk.read_bytes()).hexdigest() != build['apk_sha256']:
        raise SystemExit('APK checksum differs from reviewed build')
    result_dir = ROOT / 'local/receiver-checkpoint' / time.strftime('%Y%m%d-%H%M%S')
    result_dir.mkdir(parents=True, exist_ok=True)
    print('Installing the combined receiver checkpoint…', flush=True)
    adb('install', '-r', str(apk), timeout=180)
    adb('shell', 'am', 'force-stop', 'com.kalyan.bmwdashboardprobe')
    adb('shell', 'am', 'force-stop', APP)
    marker_ms = int(float(adb('shell', 'cat', '/proc/uptime').decode().split()[0]) * 1000)
    adb('shell', 'am', 'start', '-W', '-n', ACTIVITY, '--es', 'mode', 'decoder-test')
    deadline = time.monotonic() + 35
    first = None
    report = None
    while time.monotonic() < deadline:
        try:
            report = json.loads(adb('exec-out', 'run-as', APP, 'cat', 'files/bmw-decoder-test/result.json', timeout=5))
            if report.get('source') != 'DECODER_TEST' or report.get('captured_at_ms', 0) < marker_ms:
                time.sleep(1); continue
            if first is None: first = report
            if report['sequence'] >= first['sequence'] + 3:
                break
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
            pass
        time.sleep(1)
    else:
        raise SystemExit('Local decoder checkpoint did not produce advancing frames; do not move to car testing yet')
    jpg = adb('exec-out', 'run-as', APP, 'cat', 'files/bmw-decoder-test/latest.jpg')
    if not jpg.startswith(b'\xff\xd8') or len(jpg) < 1000:
        raise SystemExit('Decoder result is not a valid-sized JPEG; do not proceed')
    (result_dir / 'decoded-frame.jpg').write_bytes(jpg)
    verification = {'model': model, 'device': device, 'emulator': args.serial.startswith('emulator-'),
        'apk_sha256': build['apk_sha256'], 'first_frame': first, 'last_frame': report,
        'local_decode_capture_passed': True, 'iphone_authenticated': False, 'car_tested': False}
    (result_dir / 'result.json').write_text(json.dumps(verification, indent=2) + '\n')
    print(f'Local decode/capture is advancing. Evidence: {result_dir}', flush=True)
    print('This proves the local video path only. It does not establish iPhone authentication or BMW performance.', flush=True)

if __name__ == '__main__': main()
