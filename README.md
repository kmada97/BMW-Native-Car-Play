# BMW iPhone Companion

Experimental single-device iPhone companion for a 2014 BMW X3 F25. Keep the factory display and iDrive controls; use the owner's confirmed center-console USB/AUX and minimize physical changes. Actual Apple CarPlay is not required.

**Current decision (2026-09-28): buy a Raspberry Pi 4 Model B, 4GB, as a development board.** First candidate is Android running directly on the Pi, with the official BMW app and AAIdrive for the BMW endpoint. Source inspection found Android USB accessory support plus Bluetooth A2DP sink/AVRCP controller configuration. No end-to-end prototype has been validated.

```text
iPhone --Bluetooth--> Pi 4 running Android --analog audio--> BMW AUX
                              |
                         USB accessory
                              |
                       BMW NBT (assumed)
```

This is a target architecture. BMW app authentication, USB/power integration, media-session bridging and headless operation remain untested. Calls, navigation and notifications are later milestones. The previous separate Android-phone/Linux-hub design is superseded as the first experiment.

## Start

**Pre-arrival preparation:** [arrival checklist](docs/arrival.md) lists staged Mac tools, the verified AAIdrive APK, exact first-session commands and hardware-only gates. Android image retrieval is still incomplete: the host showed a completed browser transfer, but no saved ZIP was available to verify.

1. [Exact hardware list](docs/hardware.md).
2. [Pi first boot](docs/pi-first-boot.md): image verification, setup and runtime checks.
3. [Source findings and unresolved dependencies](docs/single-device-feasibility.md).
4. [Vehicle test](docs/vehicle-test.md), when the serviced car returns.
5. [Development milestones](docs/development.md).

## Tools prepared

- `python3 scripts/check_prearrival.py`: check staged downloads; fails on missing/mismatched files.
- `python3 scripts/verify_image.py /path/to/image.zip`: verify the pinned publisher hash; no disk writing.
- `python3 scripts/android_probe.py --serial DEVICE_ID`: read-only inventory of an explicitly selected ADB device. Add `--details` for private runtime dumps and save under ignored `local/`.
- `python3 scripts/bench_doctor.py`: Linux prerequisite inventory for an optional separate Linux experiment, not Android setup.
- `python3 -m unittest discover -s tests -v`: diagnostic failure/assessment tests.

**Validation:** five diagnostic tests pass locally on macOS. No image has been booted, BMW app authenticated, Bluetooth audio played, or vehicle hardware connected by this project. Presence of packages/properties is never reported as proof of a working car connection.

No extra photos are required during desk preparation. Assume NBT and provisionally target Apps capability until the car returns. Physical USB/AUX ports do not prove Apps/6NR availability.

Keep VIN, phone identifiers, keys, account data and diagnostic dumps out of Git. Preserve original vehicle menus/warnings/camera functions and test them before road use.
