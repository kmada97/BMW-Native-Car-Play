#!/usr/bin/env python3
"""Provision operator-selected authentication documents privately on the connected Pi.

No identity is bundled. Configuration and local key matching do not prove iPhone acceptance.
The app must provide its unexported authfiles ContentProvider. Leaves the receiver stopped.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
ADB = ROOT / 'local/tools/platform-tools/adb'
APP = 'com.kalyan.bmwcarplay'
PREF = 'shared_prefs/xcertplay_airplay.xml'


def configured_preferences(raw: bytes, hotspot_mode: str = 'LOCAL_ONLY_HOTSPOT') -> bytes:
    tree = ET.fromstring(raw) if raw.strip() else ET.Element('map')
    if tree.tag != 'map':
        raise ValueError('Unexpected Android preferences format')
    values = {
        'mfi_target': ('string', 'LOCAL_FILES'),
        'local_mfi_certificate_uri': ('string', f'content://{APP}.authfiles/authentication/certificate.p7b'),
        'local_mfi_private_key_uri': ('string', f'content://{APP}.authfiles/authentication/identity.pk8'),
        'wireless_enabled': ('boolean', 'true'),
        'wireless_hotspot_mode': ('string', hotspot_mode),
        'hevc_enabled': ('boolean', 'false'),
        'display_fps': ('int', '15'),
        'auto_start_on_boot': ('boolean', 'true'),
        'location_reporting_enabled': ('boolean', 'false'),
        'debug_logs_enabled': ('boolean', 'false'),
        'video_frame_logs_enabled': ('boolean', 'false'),
        'audio_packet_capture_enabled': ('boolean', 'false'),
    }
    for name, (kind, value) in values.items():
        for old in list(tree):
            if old.get('name') == name:
                tree.remove(old)
        node = ET.SubElement(tree, kind, {'name': name})
        if kind == 'string':
            node.text = value
        else:
            node.set('value', value)
    return ET.tostring(tree, encoding='utf-8', xml_declaration=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--certificate', required=True, type=Path)
    parser.add_argument('--private-key', required=True, type=Path)
    parser.add_argument('--certificate-sha256', required=True)
    parser.add_argument('--private-key-sha256', required=True)
    parser.add_argument('--hotspot-mode', choices=('WIFI_P2P', 'LOCAL_ONLY_HOTSPOT'), default='LOCAL_ONLY_HOTSPOT')
    args = parser.parse_args()
    documents = [('certificate.p7b', args.certificate, args.certificate_sha256, 65525),
                 ('identity.pk8', args.private_key, args.private_key_sha256, 16384)]
    loaded = []
    for name, path, expected, limit in documents:
        data = path.read_bytes()
        if not 1 <= len(data) <= limit or hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit(f'{name}: size/hash differs from the reviewed document')
        loaded.append((name, data))

    def adb(*words, data=None, check=True):
        return subprocess.run([str(ADB), '-s', args.serial, *words], input=data,
                              capture_output=True, check=check, timeout=30)

    device = adb('shell', 'getprop', 'ro.product.device').stdout.decode().strip()
    if device != 'rpi4':
        raise SystemExit('Explicitly selected device is not the expected Pi; nothing written')
    package = adb('shell', 'dumpsys', 'package', APP).stdout
    if (APP + '.authfiles').encode() not in package:
        raise SystemExit('Install the reviewed build with the private authentication provider first')
    adb('shell', 'am', 'force-stop', APP)
    # exec-out does not carry the remote exit status on this Android transport.
    old = adb('shell', '-T', 'run-as', APP, 'cat', PREF, check=False)
    raw = old.stdout if old.returncode == 0 else b''
    if old.returncode and b'No such file' not in old.stderr + old.stdout:
        raise SystemExit('Existing app preferences could not be read; refusing to replace them')
    updated = configured_preferences(raw, args.hotspot_mode)
    adb('shell', 'run-as', APP, 'mkdir', '-p', 'files/authentication', 'shared_prefs')
    for name, data in loaded:
        command = f'umask 077; cat > files/authentication/{name}'
        adb('shell', 'run-as', APP, 'sh', '-c', "'" + command + "'", data=data)
        remote = adb('exec-out', 'run-as', APP, 'cat', 'files/authentication/' + name).stdout
        if remote != data:
            raise SystemExit('Private document copy verification failed')
    if raw:
        adb('shell', 'run-as', APP, 'sh', '-c',
            "'umask 077; cat > files/authentication/preferences-before.xml'", data=raw)
    adb('shell', 'run-as', APP, 'sh', '-c',
        "'umask 077; cat > shared_prefs/xcertplay_airplay.xml'", data=updated)
    if adb('exec-out', 'run-as', APP, 'cat', PREF).stdout != updated:
        raise SystemExit('Preferences copy verification failed')
    for permission in ('BLUETOOTH_CONNECT', 'NEARBY_WIFI_DEVICES'):
        adb('shell', 'pm', 'grant', APP, 'android.permission.' + permission)
    print(json.dumps({'private_authentication_files_provisioned': True,
                      'receiver_stopped': True, 'iphone_authenticated': False,
                      'car_tested': False, 'boot_autostart_configured': True}))


if __name__ == '__main__':
    main()
