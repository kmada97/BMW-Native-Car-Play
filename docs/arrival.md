# Arrival checklist

Prepared 2026-09-28. This is an experimental bench kit. No Pi or car tests have passed yet.

## Already on this Mac

- Android platform tools 37.0.1: `local/tools/platform-tools/adb` (version command passed).
- Raspberry Pi Imager 2.0.11.1: `local/tools/Raspberry Pi Imager.app` (release hash, macOS code signature and version command checked).
- AAIdrive 1.4.4, no maps/no analytics: `local/downloads/aaidrive-1.4.4.apk` (matches GitHub release digest). Start with music/control; maps are a separate milestone.
- Download receipts: `config/prearrival-assets.json`. Binaries and diagnostic reports stay in ignored `local/`, not GitHub.

Run `python3 scripts/check_prearrival.py` to check all staged download hashes. A missing image is a failure, never silently treated as ready. The Google tools ZIP hash is a local receipt from its official HTTPS download, not a separately published checksum.

## Android image download still incomplete

The official Filen link showed a completed 795.79 MB transfer in the in-app browser, but no saved ZIP could be located for checksum verification. Chrome fallback was unavailable. The image is therefore **not staged or verified**. Download the pinned image from [the publisher](https://konstakang.com/devices/rpi4/AOSP16/) into `local/downloads/`, then run the checker before flashing. No SD card has been written.

## First desk session

1. Follow [first boot](pi-first-boot.md). Use a TV/monitor, mouse/keyboard, kit supply and microSD reader. Verify the exact Android ZIP before manually selecting the microSD in Imager.
2. Boot, select analog output, pair the iPhone and test music through headphones/speakers. Record sound, title, play/pause and next separately.
3. Enable the image's documented network ADB setting on the local trusted network. Connect to its observed address with `local/tools/platform-tools/adb connect ADDRESS`, then `local/tools/platform-tools/adb devices`.
4. Use the exact returned ID in `python3 scripts/android_probe.py --serial DEVICE_ID --details > local/android-baseline.json`. The script now automatically uses the staged ADB.
5. Install the staged app with `local/tools/platform-tools/adb -s DEVICE_ID install local/downloads/aaidrive-1.4.4.apk`. No device is auto-selected and no install has been attempted yet.
6. Install official My BMW through its supported distribution. Google services/app compatibility is still a device-dependent gate; do this before adding accounts if GApps installation requires resetting Android.
7. In AAIdrive's music app list, look for Bluetooth. Source defaults hide `com.android.bluetooth`; swiping a row toggles hidden status. Unhide it if present, refresh discovery and inspect the live session. This is a hypothesis to test, not evidence that iPhone controls work.
8. Repeat after reboot, then without HDMI, and after iPhone disconnect/reconnect. Disable network debugging after testing.

## Record actual results

Copy this table to `local/results.md`; keep every result NOT_TESTED until observed.

| Gate | Initial result | Evidence needed |
|---|---|---|
| Android boot / analog output | NOT_TESTED | Stable desktop and local audio |
| iPhone receiver | NOT_TESTED | iPhone music audible at Pi jack |
| Bluetooth media session | NOT_TESTED | Live metadata and play/pause/next control |
| Official BMW app | NOT_TESTED | Installs and runs; authentication checked separately |
| USB accessory | NOT_TESTED | Live AOA enumeration, not MTP/Ethernet alone |
| BMW Apps | NOT_TESTED | Authenticated session and AAIdrive menu |
| AUX with Apps screen | NOT_TESTED | Audio stays audible while app screen is open |
| Factory controls | NOT_TESTED | Knob/back/select, stock menus, camera/PDC |
| Reconnect/headless/power | NOT_TESTED | Repeated boots, temperatures and parked-current checks |

## Hardware still needed for USB testing

The kit supply handles desk audio testing. USB data plus external power needs a splitter; see [power/data candidate](power-data.md). Do not assume the car USB powers the Pi. No automotive supply or splitter has been purchased or validated by this project.

Calls, iPhone notification access and navigation are not included in this first milestone. Bluetooth audio alone does not expose the entire iPhone to Android. If the car lacks Apps or rejects authentication, more Pi code will not by itself enable the factory display.

## Source evidence

- [AAIdrive release](https://github.com/BimmerGestalt/AAIdrive/releases/tag/1.4.4).
- [Inspected default hidden apps](https://github.com/BimmerGestalt/AAIdrive/blob/3e934194941ea372a1b53be52ffc4f0d003896cd/app/src/main/java/me/hufman/androidautoidrive/AppSettings.kt).
- [Inspected music-list swipe behavior](https://github.com/BimmerGestalt/AAIdrive/blob/3e934194941ea372a1b53be52ffc4f0d003896cd/app/src/main/java/me/hufman/androidautoidrive/phoneui/fragments/MusicAppsListFragment.kt).

Source HEAD and release APK are distinct artifacts; verify this behavior in the installed release.
