#!/usr/bin/env python3
"""Read-only Android/Pi inventory via an explicitly selected ADB device.

No pairing, installs, root, USB reconfiguration, car commands or authentication
attempts. Raw dumps may contain personal data; keep output under local/.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

PROPERTIES = {
    'model': 'ro.product.model',
    'android': 'ro.build.version.release',
    'sdk': 'ro.build.version.sdk',
    'build': 'ro.build.fingerprint',
    'abi': 'ro.product.cpu.abilist',
    'usb_config': 'sys.usb.config',
    'usb_state': 'sys.usb.state',
    'a2dp_sink': 'bluetooth.profile.a2dp.sink.enabled',
    'avrcp_controller': 'bluetooth.profile.avrcp.controller.enabled',
    'hfp_client': 'bluetooth.profile.hfp.hf.enabled',
}


def run(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=20)
        return {'ok': result.returncode == 0, 'code': result.returncode,
                'output': result.stdout.strip(), 'error': result.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {'ok': False, 'code': None, 'output': '', 'error': str(error)}


def assess(checks):
    """Report declarations only. Never promote declarations to working features."""
    features = checks.get('features', {})
    packages = checks.get('packages', {})
    package_names = [line.removeprefix('package:')
                     for line in packages.get('output', '').splitlines()]
    official = [name for name in package_names if name.startswith(
        ('de.bmw.connected.', 'de.mini.connected.', 'de.j29.connected.',
         'com.bmw.connected', 'com.mini.connected'))]
    return {
        'usb_accessory_declared': (
            'feature:android.hardware.usb.accessory' in features.get('output', '').splitlines()
            if features.get('ok') else None),
        'official_app_candidates': official if packages.get('ok') else None,
        'aaidrive_installed': ('me.hufman.androidautoidrive' in package_names
                              if packages.get('ok') else None),
        'authentication': 'NOT_TESTED', 'bmw_screen': 'NOT_TESTED',
        'iphone_audio': 'NOT_TESTED',
        'note': 'Properties and installed packages do not prove runtime compatibility.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    local_adb = Path(__file__).resolve().parents[1] / 'local/tools/platform-tools/adb'
    parser.add_argument('--adb', default=str(local_adb) if local_adb.exists() else 'adb',
                        help='ADB executable; defaults to staged tools, then PATH')
    parser.add_argument('--serial', required=True, help='Exact serial or address from adb devices')
    parser.add_argument('--details', action='store_true', help='Include private USB/media/audio dumps')
    args = parser.parse_args()
    base = [args.adb, '-s', args.serial]
    state = run(base + ['get-state'])
    if not state['ok'] or state['output'] != 'device':
        print(json.dumps({'status': 'device_unavailable', 'check': state}, indent=2))
        return 2
    checks = {name: run(base + ['shell', 'getprop', prop]) for name, prop in PROPERTIES.items()}
    checks['features'] = run(base + ['shell', 'pm', 'list', 'features'])
    checks['packages'] = run(base + ['shell', 'pm', 'list', 'packages'])
    if args.details:
        for service in ('usb', 'media_session', 'audio', 'bluetooth_manager'):
            checks['dump_' + service] = run(base + ['shell', 'dumpsys', service])
    report = {'status': 'inventory_complete' if all(c['ok'] for c in checks.values())
              else 'inventory_partial', 'checks': checks, 'assessment': assess(checks)}
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'inventory_complete' else 1


if __name__ == '__main__':
    sys.exit(main())
