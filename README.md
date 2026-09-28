# BMW iPhone Companion

An experimental iPhone companion for a 2014 BMW X3 F25, retaining the factory screen and iDrive controls with minimal physical changes. Actual Apple CarPlay is not required.

**Status:** planning and bench diagnostics only. No BMW connection, Bluetooth audio or in-car integration has been validated. Current first milestone: investigate a single-device BMW USB/authentication path before buying hardware; see [single-device feasibility](docs/single-device-feasibility.md). A borrowed Android remains an optional baseline if one becomes available.

Working vehicle profile: 2014 F25, assumed NBT; center-console USB and AUX confirmed by owner. Proceed with desk research while the car is serviced; Apps support and physical behavior will be tested when it returns.

## Earlier two-device reference architecture

```text
iPhone --Bluetooth--> Linux hub --analog audio--> BMW AUX (if equipped)
                            |
                       local network
                            |
                      Android bridge --USB--> BMW Connected Apps
```

Android provides the established BMW app authentication/transport path. Linux receives iPhone media and investigates hands-free calling. Two devices are a prototype arrangement; consolidation is a later research task. The Android device does not replace the user's everyday iPhone.

## Start here

1. [Single-device feasibility](docs/single-device-feasibility.md): current work order and source findings.
2. [Hardware list](docs/hardware.md): what to borrow first and what to buy later.
3. [Vehicle compatibility test](docs/vehicle-test.md): first go/no-go milestone.
4. [Development plan](docs/development.md): software milestones and sources.
5. On an existing Linux machine or future Pi, run `python3 scripts/bench_doctor.py` for read-only prerequisite diagnostics. A successful report does not validate Bluetooth profiles or car compatibility.

## Boundaries

- Preserve original vehicle menus, warnings, camera and parking functions; explicitly test them.
- No dashboard disassembly, coding changes or firmware flashing in the first milestone.
- No arbitrary iPhone screen mirroring: Bluetooth media/control is a narrower interface.
- Factory microphone reuse, AUX plus Connected Apps coexistence and call echo cancellation remain open.
- Keep VIN, paired-device identifiers, credentials and private diagnostic logs out of Git.
