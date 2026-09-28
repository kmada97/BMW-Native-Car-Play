#!/usr/bin/env python3
"""Check staged downloads without installing software or writing any disks."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_file(path, expected):
    try:
        with path.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        return 'OK' if actual == expected else 'HASH_MISMATCH'
    except FileNotFoundError:
        return 'MISSING'


def main():
    assets = json.loads((ROOT / 'config/prearrival-assets.json').read_text())['assets']
    image = json.loads((ROOT / 'config/android-image.json').read_text())
    assets.append({'file': image['image'], 'sha256': image['sha256']})
    results = {asset['file']: check_file(ROOT / 'local/downloads' / asset['file'],
                                       asset['sha256']) for asset in assets}
    print(json.dumps({'files': results, 'hardware_validation': 'NOT_TESTED'}, indent=2))
    return 0 if all(value == 'OK' for value in results.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
