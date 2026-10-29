#!/usr/bin/env python3
"""Collect bounded, app-private startup/thermal/media metadata without changing playback."""
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ADB = ROOT / 'local/tools/platform-tools/adb'
APP = 'com.kalyan.bmwcarplay'
FILES = ('bmw-health/health.2.jsonl', 'bmw-health/health.1.jsonl', 'bmw-health/health.jsonl',
         'bmw-startup/stages.previous.jsonl', 'bmw-startup/stages.jsonl')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9._:-]+', args.serial): parser.error('Invalid explicit serial')
    def adb(*words):
        return subprocess.run([str(ADB), '-s', args.serial, *words], capture_output=True, timeout=12)
    if adb('get-state').stdout.strip() != b'device': raise SystemExit('Pi unavailable')
    args.output.mkdir(parents=True, exist_ok=True)
    report = {'files': {}, 'evidence': 'metadata_only_no_audio_payloads_or_identifiers'}
    for name in FILES:
        result = adb('exec-out', 'run-as', APP, 'cat', 'files/' + name)
        if result.returncode:
            report['files'][name] = 'unavailable'
            continue
        if len(result.stdout) > 512 * 1024: raise SystemExit('Unexpectedly large diagnostic file')
        target = args.output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(result.stdout)
        # A write in progress or power loss may leave an incomplete final line.
        records = []
        for line in result.stdout.splitlines():
            try:
                record = json.loads(line)
                if isinstance(record, dict): records.append(record)
            except (ValueError, UnicodeDecodeError): pass
        report['files'][name] = {'bytes': len(result.stdout), 'complete_records': len(records)}
    (args.output / 'collection.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
