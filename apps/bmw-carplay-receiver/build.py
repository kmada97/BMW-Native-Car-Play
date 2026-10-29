#!/usr/bin/env python3
"""Build the pinned BMW receiver fork; no ADB, installation, or credentials enrollment."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from prepare_dependencies import prepare

ROOT = Path(__file__).resolve().parents[2]
APP = Path(__file__).resolve().parent
PIN = '8b01399a17ef8b3193931a2ff4ed93b410a73570'
URL = 'https://github.com/shilapi/xcertplay.git'
CHECKOUT = ROOT / 'local/research/xcertplay-client'
OUT = ROOT / 'outputs/bmw-carplay-receiver'
TOOLCHAIN = ROOT / 'local/receiver-toolchain'

def run(args, **kw):
    return subprocess.run([str(v) for v in args], check=True, **kw)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source_files():
    raw = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=CHECKOUT)
    return sorted({name.decode() for name in raw.split(b'\0') if name})

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply-patch', action='store_true', help='Apply packaged patch to a clean pinned checkout')
    parser.add_argument('--package-only', action='store_true', help='Package existing successful build without rebuilding')
    parser.add_argument('--output-dir', type=Path, default=OUT, help='Keep an independently verifiable build in this directory')
    parser.add_argument('--artifact-name', default='bmw-carplay-receiver-checkpoint-1', help='APK/source filename stem')
    args = parser.parse_args()
    if not args.artifact_name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in args.artifact_name):
        raise SystemExit('Artifact name must contain only letters, numbers, hyphens and underscores')
    output_dir = args.output_dir.resolve()
    if not CHECKOUT.exists():
        run(['git', 'clone', URL, CHECKOUT])
        run(['git', 'checkout', '--detach', PIN], cwd=CHECKOUT)
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=CHECKOUT).decode().strip() != PIN:
        raise SystemExit('Checkout base differs from pinned source; refusing to overwrite it')
    if args.apply_patch:
        patch = APP / 'xcertplay-bmw.patch'
        applied = subprocess.run(['git', 'apply', '--reverse', '--check', str(patch)], cwd=CHECKOUT,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        if not applied:
            run(['git', 'apply', '--check', patch], cwd=CHECKOUT)
            run(['git', 'apply', patch], cwd=CHECKOUT)
    dependencies = prepare(CHECKOUT)
    files = source_files()
    hashes = {name: digest(CHECKOUT / name) for name in files if (CHECKOUT / name).is_file()}
    source_sha = hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assets = CHECKOUT / 'common/src/main/assets/bmw-build'
    identity = {'upstream_url': URL, 'upstream_commit': PIN, 'version': '1.4.0-bmw.1',
                'source_sha256': source_sha, 'source_hashes': hashes}
    identity_path = assets / 'source.json'
    if args.package_only and json.loads(identity_path.read_text()) != identity:
        raise SystemExit('Source changed since build; rebuild before packaging')
    identity_path.write_text(json.dumps(identity, indent=2) + '\n')
    env = dict(os.environ)
    # Provisioned official tools are task-local. Caller may override standard runtime locations.
    java = env.get('JAVA_HOME') or str(next((TOOLCHAIN / 'unpacked/jdk25').glob('*/Contents/Home')))
    env.update(JAVA_HOME=java, ANDROID_HOME=str(TOOLCHAIN / 'sdk'), ANDROID_SDK_ROOT=str(TOOLCHAIN / 'sdk'),
        GRADLE_USER_HOME=str(TOOLCHAIN / 'gradle-home'),
        ANDROID_KEYSTORE_PATH=str(TOOLCHAIN / 'bmw-receiver-debug.jks'),
        ANDROID_KEYSTORE_PASSWORD='android', ANDROID_KEY_PASSWORD='android', ANDROID_KEY_ALIAS='receiver')
    gradle = TOOLCHAIN / 'unpacked/gradle/gradle-9.5.0/bin/gradle'
    if not args.package_only:
        ndk = TOOLCHAIN / 'sdk/ndk/28.2.13676358/toolchains/llvm/prebuilt/darwin-x86_64'
        native = CHECKOUT / 'shared/build/bmwNative/arm64-v8a/libxcertplay_i2c.so'
        native.parent.mkdir(parents=True, exist_ok=True)
        run([ndk / 'bin/clang', '--target=aarch64-linux-android28', '--sysroot=' + str(ndk / 'sysroot'),
             '-fPIC', '-shared', '-O2', '-fstack-protector-strong', '-D_FORTIFY_SOURCE=2',
             '-Wl,-z,max-page-size=16384', '-Wl,-z,relro', '-Wl,-z,now', '-Wl,-soname,libxcertplay_i2c.so',
             CHECKOUT / 'shared/src/main/jni/linux_i2c_jni.c', '-o', native], env=env)
        run([gradle, '--no-daemon', '-PbmwNativePrebuilt=true', ':mobile:assembleDebug', ':common:testDebugUnitTest', ':shared:testDebugUnitTest'], cwd=CHECKOUT, env=env)
    apk = CHECKOUT / 'mobile/build/outputs/apk/debug/mobile-debug.apk'
    current_hashes = {name: digest(CHECKOUT / name) for name in source_files() if (CHECKOUT / name).is_file()}
    if current_hashes != hashes:
        raise SystemExit('Source changed during build; rebuild before publishing a checkpoint')
    signer = TOOLCHAIN / 'sdk/build-tools/36.0.0/apksigner'
    run([signer, 'verify', '--verbose', apk], env=env)
    with zipfile.ZipFile(apk) as built:
        if json.loads(built.read('assets/bmw-build/source.json')) != identity:
            raise SystemExit('Embedded source identity does not match current sources')
    totals = {'tests': 0, 'failures': 0, 'errors': 0, 'skipped': 0}
    reports = []
    for module in ('common', 'shared'):
        module_reports = sorted((CHECKOUT / module / 'build/test-results/testDebugUnitTest').glob('TEST-*.xml'))
        if not module_reports: raise SystemExit(f'No unit test reports for {module}')
        for report in module_reports:
            element = ET.parse(report).getroot()
            for key in totals: totals[key] += int(element.get(key, 0))
            reports.append({'module': module, 'suite': element.get('name'),
                **{key: int(element.get(key, 0)) for key in totals}})
    if totals['failures'] or totals['errors']: raise SystemExit('Tests failed; no checkpoint APK published')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_apk = output_dir / (args.artifact_name + '.apk')
    shutil.copy2(apk, output_apk)
    source_zip = output_dir / (args.artifact_name + '-source.zip')
    with zipfile.ZipFile(source_zip, 'w', zipfile.ZIP_DEFLATED) as archive:
        packaged = set(files)
        for base in (CHECKOUT / 'common/libs', assets):
            packaged.update(str(p.relative_to(CHECKOUT)) for p in base.rglob('*') if p.is_file())
        for name in sorted(packaged):
            path = CHECKOUT / name
            if path.is_file(): archive.write(path, 'bmw-carplay-receiver/' + name)
    result = {'built_at_utc': datetime.now(timezone.utc).isoformat(), **identity,
        'apk': str(output_apk), 'apk_sha256': digest(output_apk), 'bytes': output_apk.stat().st_size,
        'source_zip_sha256': digest(source_zip), 'signature_verified': True,
        'unit_tests': totals, 'test_suites': reports, 'dependencies': dependencies,
        'iphone_authenticated': False, 'car_tested': False, 'pi_installed': False}
    (output_dir / 'build-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('source_hashes', 'test_suites', 'dependencies')}, indent=2))

if __name__ == '__main__': main()
