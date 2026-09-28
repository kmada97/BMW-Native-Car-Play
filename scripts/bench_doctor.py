#!/usr/bin/env python3
"""Read-only Linux bench inventory. Never pairs devices or changes services."""
import json
import platform
import shutil
import subprocess


def probe(command):
    executable = shutil.which(command[0])
    if not executable:
        return {"status": "missing", "command": command[0]}
    try:
        result = subprocess.run(
            [executable, *command[1:]], capture_output=True, text=True,
            timeout=8, check=False,
        )
        return {"status": "ok" if result.returncode == 0 else "error",
                "exit_code": result.returncode,
                "output": (result.stdout + result.stderr).strip()[:4000]}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"status": "error", "output": str(error)}


def main():
    system = platform.system()
    report = {"system": system, "architecture": platform.machine(),
              "scope": "Prerequisite inventory only; no hardware compatibility claim."}
    if system != "Linux":
        report["status"] = "unsupported_host"
        report["next_step"] = "Run on the Linux bench host/Pi, not the development Mac."
        print(json.dumps(report, indent=2))
        return 2
    report["checks"] = {
        "bluez": probe(["bluetoothctl", "--version"]),
        "bluetooth_service": probe(["systemctl", "is-active", "bluetooth"]),
        "radio_blocks": probe(["rfkill", "--output", "TYPE,SOFT,HARD"]),
        "alsa_playback": probe(["aplay", "-l"]),
        "alsa_capture": probe(["arecord", "-l"]),
        "bluealsa": probe(["bluealsad", "--version"]),
    }
    report["status"] = "inventory_complete"
    report["next_step"] = "Review missing tools/devices before choosing an audio stack."
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
