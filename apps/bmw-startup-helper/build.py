#!/usr/bin/env python3
"""Build with the project-local pinned JDK and Android tools; does not install."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import zipfile

root = Path(__file__).resolve().parent
workspace = root.parents[1]
toolchain = workspace / "local/car-start-helper/toolchain"
jdk = toolchain / "jdk/jdk-17.0.20.1+1/Contents/Home"
bt = toolchain / "sdk-build-tools/android-15"
android = toolchain / "sdk-platform/android-35/android.jar"
out = Path(os.environ.get("BMW_HELPER_BUILD_DIR", str(workspace / "local/car-start-helper/build"))).resolve()
out.mkdir(exist_ok=True)
env = dict(os.environ, JAVA_HOME=str(jdk))
env["PATH"] = str(jdk / "bin") + os.pathsep + env.get("PATH", "")

def run(*args):
    subprocess.run([str(x) for x in args], check=True, env=env, cwd=root)

for name in ("aapt2", "d8", "apksigner", "zipalign"):
    (bt / name).chmod(0o755)
for directory in ("classes", "test", "dex", "generated"):
    (out / directory).mkdir(exist_ok=True)

run(jdk / "bin/javac", "-d", out / "test",
    root / "src/com/kalyan/bmwstartup/RetryPolicy.java", root / "test/RetryPolicyTest.java")
run(jdk / "bin/java", "-cp", out / "test", "RetryPolicyTest")
run(bt / "aapt2", "link", "-I", android, "--manifest", root / "AndroidManifest.xml",
    "--java", out / "generated", "-o", out / "base.apk")
sources = sorted((root / "src").rglob("*.java")) + sorted((out / "generated").rglob("*.java"))
run(jdk / "bin/javac", "-source", "8", "-target", "8", "-bootclasspath", android,
    "-d", out / "classes", *sources)
run(jdk / "bin/jar", "cf", out / "classes.jar", "-C", out / "classes", ".")
run(bt / "d8", "--lib", android, "--min-api", "26", "--output", out / "dex", out / "classes.jar")
with zipfile.ZipFile(out / "base.apk", "a") as z:
    for dex in (out / "dex").glob("*.dex"):
        z.write(dex, dex.name)
run(bt / "zipalign", "-f", "4", out / "base.apk", out / "aligned.apk")
key = workspace / "local/car-start-helper/build/local-debug.jks"
key.parent.mkdir(parents=True, exist_ok=True)
if not key.exists():
    run(jdk / "bin/keytool", "-genkeypair", "-keystore", key, "-storepass", "android",
        "-keypass", "android", "-alias", "localdebug", "-dname", "CN=BMW Startup Local Development",
        "-keyalg", "RSA", "-keysize", "2048", "-validity", "3650", "-noprompt")
    key.chmod(0o600)
apk = out / "bmw-startup-helper-0.1.apk"
run(bt / "apksigner", "sign", "--ks", key, "--ks-pass", "pass:android", "--key-pass",
    "pass:android", "--out", apk, out / "aligned.apk")
run(bt / "apksigner", "verify", "--verbose", apk)
result = {"apk": str(apk), "sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
          "bytes": apk.stat().st_size, "policy_tests": "passed", "device_tested": False}
(out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
