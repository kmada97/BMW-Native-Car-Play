# Pi 4 first boot: single-device experiment

Prepared 2026-09-28. No hardware has been tested. This is a reproducible bench procedure, not a ready-to-install BMW system.

## Chosen first experiment

Run Android directly on a Pi 4 4GB. This keeps an Android environment for the official BMW authentication module and tests the Pi's built-in Bluetooth receiver support. It eliminates the separate Android phone if it succeeds. Linux audio remains a fallback bench experiment, not a simultaneous second OS.

Use KonstaKANG's **AOSP 16 Pi 4 image dated 2026-04-28**, linked in config/android-image.json. The author publishes a checksum and documents Pi 4 support, analog audio and USB-C data functions. The inspected Raspberry Vanilla Android 16 source additionally contains AOA gadget support, A2DP sink and AVRCP controller configuration. These source findings are not proof that the published binary implements every function correctly.

## Desk setup

1. Download the exact ZIP from https://konstakang.com/devices/rpi4/AOSP16/ (the normal image, not OTA or kernel add-on). Images are not mirrored in this repo.
2. Run `python3 scripts/verify_image.py /path/to/downloaded.zip` on the Mac. It must match before flashing.
3. Use Raspberry Pi Imager's custom-image option to write that image to the intended microSD. This erases that card; verify the selected storage device. No automatic disk-writing script is included.
4. Insert the card. Connect the Pi's micro-HDMI to an existing TV/monitor, plus a USB mouse/keyboard. These are for desk setup, not an added vehicle display.
5. Power the Pi from the official Pi 4 15W wall supply. Connect Wi-Fi or Ethernet. Select the analog jack for output in Raspberry Pi settings. Start at low volume with a desk speaker/headphones.
6. Pair the iPhone in Android Bluetooth settings. Test whether the iPhone offers the Pi as a media destination and whether playback reaches the analog jack. Record pass/fail. Test pause/next/metadata separately; do not infer these from audible sound.
7. Enable developer options/ADB only for the bench. Install Android SDK Platform Tools on the Mac from https://developer.android.com/tools/releases/platform-tools. Use the build's documented network ADB option on a trusted local network so the USB-C port can remain powered. Authorize the Mac as prompted. Do not expose ADB to the internet; disable it after diagnostics.
8. Run `adb devices`. Select the exact device identifier, then:

```sh
mkdir -p local
python3 scripts/android_probe.py --serial YOUR_DEVICE_ID > local/android-baseline.json
python3 scripts/android_probe.py --serial YOUR_DEVICE_ID --details > local/android-details.json
```

Replace YOUR_DEVICE_ID with the observed identifier, not a guessed address. Reports can contain device identifiers/media metadata; local/ is ignored by Git.

## BMW apps on the Pi

- Install the current official My BMW app through a legitimate supported distribution path and AAIdrive from its upstream release/store. The Android image does not include a working BMW app/authentication guarantee.
- If the official app needs Google services, the image author's page documents an optional GApps installation that includes a factory reset. Resolve this before configuring accounts or saving work. Do not assume device certification/app compatibility will work and do not source old BMW APKs from random mirrors.
- Run the probe again to inventory apps. Package presence is not authentication success; the report deliberately leaves authentication NOT_TESTED.
- In AAIdrive, inspect whether the Bluetooth receiver produces a browsable/controllable Android media session. If it does not, a custom adapter between Android's Bluetooth session and AAIdrive is still needed. No such adapter is implemented here.

## USB and power gate — before connecting the car

The Pi's USB-C port is also its power input and its USB gadget data port. Its USB-A ports are host ports. Do not connect a host-to-host USB-A cable to the car or assume BMW USB supplies Pi operating current.

Bench power above deliberately uses the wall supply and network diagnostics. Simultaneous USB-C data and adequate independent power requires a specifically verified power/data arrangement with protection against backfeeding. We have not selected or validated that arrangement. Do not improvise a Y cable or bare GPIO power connection. A plain USB-A-to-C data cable is a later component, not a complete power solution.

Android accessory support must be observed in a live USB session before the BMW connection test. Generic USB Ethernet/MTP enumeration alone does not pass this gate.

## When the car returns

Use the working NBT/Apps assumption for planning, then test: official-app session, AAIdrive menu, knob/back/select, AUX plus app UI, original menus, camera/PDC and restart behavior. If Apps is unavailable or authentication fails, the factory-USB screen route remains blocked even if Bluetooth audio works. No firmware flashing/coding is part of this procedure.

## Later features

Calls require HFP hands-free/client role, microphone input, two-way routing and echo handling. Source enables HFP audio-gateway in its general configuration; that is the opposite role from what an iPhone receiver needs. Calls are therefore not assumed ready. Maps and notifications also remain separate work. Headless Android boot without the desk monitor, reconnect automation, heat, shutdown and parked current must be qualified before permanent use.

## Rollback

Keep each OS on its own card if experimenting with Linux. Shut down before changing cards. No vehicle software is modified by this preparation. Forget the Pi in iPhone Bluetooth settings to undo bench pairing.
