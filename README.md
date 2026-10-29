# BMW Native Car Play

An experimental project bringing actual iPhone CarPlay to the factory screen and iDrive controls of a **2014 BMW X3 F25 (NBT / ID4)**. A Raspberry Pi 4 running Android acts as the receiver and bridges CarPlay video and controls through the existing BMW Apps USB connection, with audio through AUX.

The goal is to retain the original BMW display and controls, improve everyday reliability and responsiveness, and eventually consolidate the prototype into a custom compute-module carrier PCB. This is an independent project, unaffiliated with BMW or Apple, and is still under development.

## How it works

```text
iPhone -- wireless CarPlay --> Raspberry Pi 4 / Android
                                  |             ^
                           BMW Apps USB         | iDrive input
                                  v             |
                              BMW head unit / factory display

Pi analog audio ----------------> BMW AUX
```

The software integrates a pinned [xcertplay](https://github.com/shilapi/xcertplay) receiver with BMW image/input transport, alongside My BMW and [AAIdrive](https://github.com/BimmerGestalt/AAIdrive). It sends decoded CarPlay frames to the factory display and forwards rotary/press input to the receiver. This is a bridge through BMW Apps; it does not enable an OEM CarPlay firmware feature.

## Current status

Latest physical-test evidence: **October 15, 2026**. Repository publication: October 29, 2026.

- Actual iPhone CarPlay has been shown on the BMW factory screen, with Maps and music. The display/input route and iDrive rotary/press controls have been demonstrated.
- The installed usability build improved picture proportions and audio stutter. Lag, slow startup and intermittent stutter remain. Heat has been reported alongside stutter, but thermal throttling has not been established.
- Calls have incoming audio but no working return microphone. Calls/Siri and BMW hands-free routing remain unfinished.
- A newer refinement build passed 289 JVM tests in the prior local build. It adds HDMI-independent startup, avoids compressing unchanged frames, improves settled-frame quality and collects bounded runtime diagnostics. **It has not been installed or car-tested.**
- Sustained 10 FPS, then 16 FPS, are engineering targets, not achieved results. Ignition recovery and long-session reliability need further validation.

See [development notes](docs/development.md) for dated evidence, historical checkpoints and open questions. Older documents describe earlier stages and are superseded by the latest dated results.

## Repository contents

| Path | Purpose |
| --- | --- |
| [apps/bmw-carplay-receiver](apps/bmw-carplay-receiver/README.md) | Pinned receiver patch, build tooling, Pi setup and diagnostics |
| [apps/bmw-dashboard-probe](apps/bmw-dashboard-probe/README.md) | Original factory-screen image/input proof |
| [apps/bmw-startup-helper](apps/bmw-startup-helper/README.md) | BMW USB startup helper |
| [apps/bmw-carplay-auth](apps/bmw-carplay-auth/README.md) | Authentication protocol adapter and synthetic tests |
| [docs](docs/development.md) | Development history, wiring, setup and vehicle testing |
| `scripts/`, `tests/`, `config/` | Local preparation, diagnostics, tests and pinned asset metadata |

## Building and testing

Start with the [receiver build instructions](apps/bmw-carplay-receiver/README.md#rebuild-and-source). The build tooling expects locally provisioned Android/Java/Gradle/NDK tools; this is not yet a turnkey installer.

```sh
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s apps/bmw-carplay-auth/tests -v
# After provisioning the toolchain described in the receiver README:
python3 apps/bmw-carplay-receiver/build.py --apply-patch
```

The receiver patch targets upstream commit `8b01399a17ef8b3193931a2ff4ed93b410a73570`. Its GPLv3 license and third-party notices are retained in the relevant components. Generated APKs, source archives, device captures and local build tools are excluded from Git. References to `outputs/` in development notes describe local historical artifacts, not downloadable releases.

Authentication requires separately provisioned inputs; no accessory private keys, pairing data or credentials are included. The demonstrated experimental software identity may cease to be accepted. The authentication adapter alone does not create an accepted identity.

## PCB roadmap

The current prototype uses the existing Pi, USB power/data splitter and AUX connection. Future updates will track a dedicated non-Pi compute-module carrier board as the hardware design develops.

1. Measure and improve display latency, startup time, sustained audio and thermal behavior.
2. Resolve the call microphone/routing path and validate power-loss recovery.
3. Prove a candidate compute module can run the Android receiver, BMW USB connection and hardware video decoder.
4. Define power protection, USB, audio, wireless and connector interfaces; then develop schematics, layout, enclosure and a testable BOM.

**No module is selected and no PCB schematics, layout, Gerbers or fabrication release exist yet.** The [hardware proposal](docs/development.md#proposed-eventual-custom-module) records the current direction. PCB files and validation results will be added as they become available.

## Testing in the car

See [vehicle tests](docs/vehicle-test.md) and [power/data wiring](docs/power-data.md). Exercise this prototype while parked and preserve access to factory menus, warnings and camera functions. Keep VINs, phone identifiers, account information, keys and raw diagnostic dumps out of Git.
