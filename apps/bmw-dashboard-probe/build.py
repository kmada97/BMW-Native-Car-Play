#!/usr/bin/env python3
"""Build the isolated probe. No install, ADB, AAIdrive changes, or global toolchain changes."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import zipfile

root = Path(__file__).resolve().parent
workspace = root.parents[1]
output = workspace / "outputs/bmw-dashboard-probe"
build = workspace / "local/dashboard-probe"
deps = build / "deps"
toolchain = workspace / "local/car-start-helper/toolchain"
jdk = toolchain / "jdk/jdk-17.0.20.1+1/Contents/Home"
bt = toolchain / "sdk-build-tools/android-15"
android = toolchain / "sdk-platform/android-35/android.jar"
env = dict(os.environ, JAVA_HOME=str(jdk))
env["PATH"] = str(jdk / "bin") + os.pathsep + env.get("PATH", "")

def run(*args):
    subprocess.run([str(x) for x in args], check=True, env=env, cwd=root, timeout=120)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

output.mkdir(parents=True, exist_ok=True)
manifest = ET.parse(root / "AndroidManifest.xml").getroot()
version = manifest.attrib["{http://schemas.android.com/apk/res/android}versionName"]
version_code = int(manifest.attrib["{http://schemas.android.com/apk/res/android}versionCode"])
# Preserve provenance of the shipped 0.1 rather than silently replacing its metadata.
previous = output / "build-result.json"
if previous.exists():
    old = json.loads(previous.read_text())
    old_version = old.get("version", "0.1")
    archived = output / f"build-result-{old_version}.json"
    if not archived.exists(): archived.write_bytes(previous.read_bytes())
deps.mkdir(parents=True, exist_ok=True)
dependencies = json.loads((root / "dependencies.json").read_text())
jars = []
for name, info in dependencies.items():
    path = deps / name
    if not path.exists():
        path.write_bytes(urllib.request.urlopen(info["url"], timeout=45).read())
    if digest(path) != info["sha256"]:
        raise SystemExit(f"Dependency checksum mismatch: {name}")
    if name.endswith(".aar"):
        target = deps / name.replace(".aar", ".jar")
        with zipfile.ZipFile(path) as z:
            target.write_bytes(z.read("classes.jar"))
        jars.append(target)
    else:
        jars.append(path)

for name in ("classes", "dex", "generated", "tests"):
    path = build / name
    if path.exists(): shutil.rmtree(path)
    path.mkdir()

test_sources = [root / "src/com/kalyan/bmwdashboardprobe/ProbeState.java",
                root / "src/com/kalyan/bmwdashboardprobe/TemplateLayout.java",
                root / "src/com/kalyan/bmwdashboardprobe/ProbeGuard.java",
                root / "src/com/kalyan/bmwdashboardprobe/FrameSchedule.java",
                root / "src/com/kalyan/bmwdashboardprobe/DashboardLayout.java",
                root / "test/FrameScheduleTest.java",
                root / "test/EtchWatchdogTest.java",
                root / "test/ProbeTest.java"]
run(jdk / "bin/javac", "-cp", os.pathsep.join(str(p) for p in jars), "-d", build / "tests", *test_sources)
run(jdk / "bin/java", "-cp", build / "tests", "ProbeTest", workspace / "local/downloads/aaidrive-1.4.4.apk")
run(jdk / "bin/java", "-cp", build / "tests", "FrameScheduleTest")
subprocess.run([str(jdk / "bin/java"), "-cp", os.pathsep.join([str(build / "tests")] + [str(p) for p in jars]),
                "EtchWatchdogTest"], check=True, env=env, cwd=root, timeout=15)

run(bt / "aapt2", "link", "-I", android, "--manifest", root / "AndroidManifest.xml",
    "--java", build / "generated", "-o", build / "base.apk")
source_files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix in (".java", ".xml", ".json", ".py"))
source_hashes = {str(p.relative_to(root)): digest(p) for p in source_files}
source_digest = hashlib.sha256(json.dumps(source_hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
identity = build / "generated/com/kalyan/bmwdashboardprobe/BuildIdentity.java"
identity.parent.mkdir(parents=True, exist_ok=True)
identity.write_text('package com.kalyan.bmwdashboardprobe;\npublic final class BuildIdentity {\n'
                    f'    public static final String VERSION = "{version}";\n'
                    f'    public static final String SOURCE_SHA256 = "{source_digest}";\n'
                    '}\n')
sources = sorted((root / "src").rglob("*.java")) + sorted((build / "generated").rglob("*.java"))
run(jdk / "bin/javac", "-source", "8", "-target", "8", "-bootclasspath", str(bt / "core-lambda-stubs.jar") + os.pathsep + str(android),
    "-cp", os.pathsep.join(str(p) for p in jars), "-d", build / "classes", *sources)
run(jdk / "bin/jar", "cf", build / "classes.jar", "-C", build / "classes", ".")
run(bt / "d8", "--lib", android, "--min-api", "26", "--output", build / "dex", build / "classes.jar", *jars)
with zipfile.ZipFile(build / "base.apk", "a") as z:
    for dex in (build / "dex").glob("*.dex"): z.write(dex, dex.name)
    for license in (root / "licenses").glob("*"): z.write(license, "assets/licenses/" + license.name)
    z.write(root / "dependencies.json", "assets/dependencies.json")
    z.writestr("assets/source-hashes.json", json.dumps(source_hashes, indent=2)+"\n")
run(bt / "zipalign", "-f", "4", build / "base.apk", build / "aligned.apk")
key = build / "probe-local-debug.jks"
if not key.exists():
    run(jdk / "bin/keytool", "-genkeypair", "-keystore", key, "-storepass", "android",
        "-keypass", "android", "-alias", "probe", "-dname", "CN=BMW Dashboard Probe Local Development",
        "-keyalg", "RSA", "-keysize", "2048", "-validity", "3650", "-noprompt")
    key.chmod(0o600)
apk = output / f"bmw-dashboard-probe-{version}.apk"
run(bt / "apksigner", "sign", "--ks", key, "--ks-pass", "pass:android", "--key-pass", "pass:android",
    "--out", apk, build / "aligned.apk")
run(bt / "apksigner", "verify", "--verbose", apk)
result = {"version": version,"version_code": version_code,"built_at_utc": datetime.now(timezone.utc).isoformat(),
          "source_sha256": source_digest,"source_hashes": source_hashes,"apk": str(apk), "sha256": digest(apk), "bytes": apk.stat().st_size,
          "frame_schedule_and_layout_tests": "passed", "template_and_input_tests": "passed", "signature_verified": True,
          "silent_peer_etch_watchdog_test": "passed", "async_stop_test": "passed",
          "device_tested": False, "car_tested": False,
          "dependencies": dependencies}
(output / "build-result.json").write_text(json.dumps(result, indent=2) + "\n")
(output / f"build-result-{version}.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k:v for k,v in result.items() if k not in ("dependencies","source_hashes")}, indent=2))
