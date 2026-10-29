#!/usr/bin/env python3
"""Read a small, allowlisted view of AAIdrive's cached car capabilities.

Uses the Pi's already-available su command only to read AAIdrive's cache. Does
not connect to the car, change USB mode, discover other devices, or write to
Android/the head unit. Never prints or saves the complete cached document.
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path


CAPABILITIES_PATH = (
    '/data/user/0/me.hufman.androidautoidrive/cache/car_capabilities.json'
)
ALLOWED_KEYS = (
    'hmi.type', 'hmi.version', 'hmi.display-width', 'hmi.display-height',
    'hmi.role', 'vehicle.type', 'navi', 'tts',
)
MAX_CACHE_BYTES = 262144


def extract_capabilities(raw):
    """Drop identifiers/locations and reject unbounded or structured values."""
    if len(raw.encode('utf-8')) > MAX_CACHE_BYTES:
        raise ValueError('Capability cache exceeds size limit')
    document = json.loads(raw)
    if not isinstance(document, dict):
        raise ValueError('Expected an object in capability cache')
    result = {}
    for key in ALLOWED_KEYS:
        value = document.get(key)
        if isinstance(value, float) and not math.isfinite(value):
            continue
        if isinstance(value, (str, int, float, bool)):
            if len(str(value)) <= 256:
                result[key] = value
    return result


def adb_read(adb, serial, arguments):
    return subprocess.run(
        [adb, '-s', serial] + arguments, capture_output=True,
        text=True, timeout=20, check=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    staged = Path(__file__).resolve().parents[1] / 'local/tools/platform-tools/adb'
    parser.add_argument('--adb', default=str(staged))
    parser.add_argument('--serial', required=True)
    parser.add_argument('--output', type=Path,
                        help='Optional destination for the filtered JSON report')
    args = parser.parse_args()
    status = 'device_unavailable'
    capabilities = {}
    exit_code = 2
    try:
        state = adb_read(args.adb, args.serial, ['get-state'])
        if state.returncode == 0 and state.stdout.strip() == 'device':
            cached = adb_read(args.adb, args.serial,
                              ['exec-out', 'su', '0', 'cat', CAPABILITIES_PATH])
            if cached.returncode == 0:
                capabilities = extract_capabilities(cached.stdout)
                status = 'cache_read' if capabilities else 'cache_has_no_allowed_fields'
                exit_code = 0 if capabilities else 3
            else:
                status, exit_code = 'capability_cache_unavailable', 3
    except (OSError, subprocess.TimeoutExpired):
        status, exit_code = 'adb_read_failed', 2
    except (ValueError, UnicodeError):
        status, exit_code = 'invalid_capability_cache', 4

    report = {
        'status': status,
        'source': 'AAIdrive cached capabilities; may describe a prior session',
        'capabilities': capabilities,
        'missing_fields': [key for key in ALLOWED_KEYS if key not in capabilities],
        'limits': [
            'HMI profile/version does not conclusively identify hardware or I-level.',
            'No vulnerability applicability or live display performance is established.',
            'No cached VIN, phone identifiers or location fields are included.',
        ],
    }
    output = json.dumps(report, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output)
    sys.stdout.write(output)
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
