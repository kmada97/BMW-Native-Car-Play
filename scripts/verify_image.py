#!/usr/bin/env python3
"""Verify the publisher's pinned ZIP hash before manual imaging; writes nothing."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('image', type=Path)
args = parser.parse_args()
manifest = json.loads((Path(__file__).resolve().parents[1] / 'config/android-image.json').read_text())
try:
    with args.image.open('rb') as image:
        actual = hashlib.file_digest(image, 'sha256').hexdigest()
except OSError as error:
    parser.exit(2, f'{error}\n')
if actual != manifest['sha256']:
    parser.exit(1, f'HASH MISMATCH. Do not flash. Expected {manifest["sha256"]}; got {actual}\n')
print('Hash matches pinned publisher value. This verifies file integrity, not BMW compatibility.')
