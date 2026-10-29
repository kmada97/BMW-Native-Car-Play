#!/usr/bin/env python3
"""Prepare pinned BMW transport jars without a second, obsolete crypto implementation."""
from pathlib import Path
import hashlib
import json
import sys
import urllib.request
import zipfile

PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_CHECKOUT = PROJECT / 'local/research/xcertplay-client'
NAMES = ('idriveconnectkit-jvm-0.8.jar', 'idriveconnectkit-etch-0.8.jar',
         'etch-runtime-0.8.jar', 'IDriveConnectKitAndroid-0.7.aar')

def prepare(checkout=DEFAULT_CHECKOUT):
    manifest = json.loads((PROJECT / 'apps/bmw-dashboard-probe/dependencies.json').read_text())
    cache = PROJECT / 'local/dashboard-probe/deps'
    dest = checkout / 'common/libs'
    dest.mkdir(parents=True, exist_ok=True)
    records = {}
    for name in NAMES:
        source = cache / name
        info = manifest[name]
        if not source.exists():
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(urllib.request.urlopen(info['url'], timeout=60).read())
        if hashlib.sha256(source.read_bytes()).hexdigest() != info['sha256']:
            raise ValueError(f'Dependency checksum mismatch: {name}')
        if name.endswith('.aar'):
            import io
            target = dest / 'IDriveConnectKitAndroid-0.7-bmw.jar'
            with zipfile.ZipFile(source) as aar, zipfile.ZipFile(io.BytesIO(aar.read('classes.jar'))) as jar:
                with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as out:
                    for entry in sorted(jar.namelist()):
                        # BMW transport uses BmwCertificates with BC1.79. The old helpers reference
                        # removed PEMReader/PEMWriter APIs and are unused by SecurityAccess.
                        if any(part in entry for part in ('CertMangling', 'PrivateKeyHandling', 'CarAppAssetResources')):
                            continue
                        item = zipfile.ZipInfo(entry, (1980, 1, 1, 0, 0, 0))
                        item.compress_type = zipfile.ZIP_DEFLATED
                        out.writestr(item, jar.read(entry))
        else:
            target = dest / name
            target.write_bytes(source.read_bytes())
        records[target.name] = {'upstream': info, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
    assets = checkout / 'common/src/main/assets/bmw-build'
    assets.mkdir(parents=True, exist_ok=True)
    (assets / 'dependencies.json').write_text(json.dumps(records, indent=2) + '\n')
    licenses = assets / 'licenses'
    licenses.mkdir(exist_ok=True)
    for source in (PROJECT / 'apps/bmw-dashboard-probe/licenses').iterdir():
        # Keep upstream notices even where the runtime is supplied through a newer Maven artifact.
        (licenses / source.name).write_bytes(source.read_bytes())
    return records

if __name__ == '__main__':
    prepare(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_CHECKOUT)
