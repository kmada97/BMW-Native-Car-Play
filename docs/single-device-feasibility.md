# Single-device feasibility — first milestone

2026-09-28. User owns neither an Android phone nor a Pi and wants to avoid buying an Android phone. As of the later 2026-09-28 purchase request, select Pi 4 Model B 4GB for bench work; this supersedes the earlier purchase hold. In-car compatibility remains unproven. The two-device architecture remains a reference, not a confirmed requirement or the current shopping instruction.

## Working vehicle profile until the car returns

User confirmed 2026-09-28: center-console USB and AUX sockets. Use 2014 BMW X3 xDrive35i (F25), original display/iDrive, and NBT as the working head-unit assumption. NBT is inferred from model/year and prior recorded photo context, not conclusively identified from TN/HN/MN software fields. Do not assume exact display resolution or build options.

For desk design, provisionally target an Apps-capable NBT over USB. Apps/6NR availability remains unverified; USB and AUX do not establish it. This assumption permits software/interface research now and must be tested before claiming in-car compatibility. AUX is the planned analog speaker input; concurrent Apps display/audio behavior remains untested.

No additional photos or vehicle interaction are required while the car is serviced. Prioritize USB transport, authentication runtime and board device-mode feasibility now. Defer vehicle menu/options checks and physical tests until it returns. No hardware purchase or compatibility guarantee follows from these assumptions.

## Success criterion

A single development device connects to the existing BMW USB port, authenticates using an available supported path, displays a minimal menu and receives knob/select/back events. No music, calls or maps are needed to pass this milestone. No such demonstration exists in this repository yet.

## Source audit actually performed

Read-only checkouts are in ignored local/research/. No upstream code copied into our tracked source, no APKs obtained, no car connection attempted.

- BclCarLink commit `7cfd959bba8a742345913c5ce6c5c179c351e189`: `app/src/main/java/io/bimmergestalt/bcl/android/BtConnection.kt` opens Android Bluetooth RFCOMM with the Serial Port UUID and feeds its streams into BCL transport/multiplexing. A search of app/src/main found no USB implementation. Its README describes USB/Bluetooth generally; that is not evidence of a ready USB implementation in this checkout. Bluetooth Apps availability on this 2014 car is unverified and must not be inferred from music Bluetooth support.
- IDriveConnectKitAndroid commit `4a567bc0557bf20a19c0fc03a39fcba69a333ea2`: `SecurityAccess.kt` discovers installed official packages and delegates challenge signing to their security service/module. This is Android-dependent code, not a demonstrated standalone Linux authentication implementation.
- Android Open Accessory documentation describes the host negotiation and device-side bulk endpoints. It is a transport reference, not proof that this BMW accepts a Pi. A Pi candidate must expose the correct USB device role and protocol, with compatible power wiring; an ordinary host-to-host USB cable is not a solution.

## Work order

1. When the car returns (not a prerequisite for desk research), collect vehicle evidence without disassembly: main iDrive menu, ConnectedDrive submenu/Connection Assistant, map-version screen if navigation is fitted, and center-console USB/AUX sockets. Check build/options for Apps/6NR when available. These can narrow compatibility but do not prove authentication.
2. Trace the actual BMW USB path in available implementation/documentation. Determine what the accessory negotiation, BCL transport and authentication each require; mark undocumented behavior explicitly.
3. Evaluate two single-board approaches separately: native Linux transport plus an available authentication implementation; or Android on a USB-device-capable board running the official app. For the latter, verify app installation/security-service operation, USB accessory support and Bluetooth audio receiver roles. A booting Android image is insufficient.
4. Use the selected Pi 4 4GB for Android bench experiments. Treat it as development hardware, not a validated BMW bridge.
5. Bench-test enumeration/transport, then test a minimal authenticated menu on the parked car. If neither approach has a viable authentication/transport path, reconsider a borrowed phone for diagnosis or the previously discussed MMI fallback with the user.

## Open dependencies

| Dependency | Evidence required | Current result |
| --- | --- | --- |
| BMW Apps support | Vehicle options/menu evidence, followed by successful session | Unknown |
| USB transport | Correct negotiation and bidirectional data on target board | Not implemented/tested |
| Authentication | Valid session using an available security implementation | Android dependency identified; Pi execution unproven |
| Factory UI/control | Render menu and receive real iDrive events | Not tested |
| iPhone audio | A2DP sink; later HFP bidirectional audio | Separate later test |

Sources:
- https://github.com/BimmerGestalt/BclCarLink/tree/7cfd959bba8a742345913c5ce6c5c179c351e189
- https://github.com/BimmerGestalt/IDriveConnectKitAndroid/tree/4a567bc0557bf20a19c0fc03a39fcba69a333ea2
- https://source.android.com/docs/core/interaction/accessories/aoa

## New source evidence: single-Pi Android candidate

Inspected Raspberry Vanilla `android-16.0` device tree at commit `b9539c016db0e82dcc3af7c37c15924a77fbf5c1`:

- `vendor.prop`: enables A2DP sink and AVRCP controller; chooses analog jack. This is stronger evidence than generic Android-phone behavior, which should not be applied to this board configuration.
- `overlay/BluetoothRpiOverlay/res/values/config.xml`: requests audio focus/AVRCP updates for the receiver.
- `device.mk`: includes the Android USB accessory feature declaration.
- `ramdisk/init.rpi4.usb.rc`: creates accessory.gs2.
- `usb/UsbGadgetUtils.cpp`: handles ACCESSORY and links accessory.gs2.
- General configuration enables HFP AG; this does NOT establish the HFP client role needed for iPhone calls. Automotive product configuration differs and has not been selected/tested.

This establishes a plausible software target, not a successful BMW session. Selected published bench image is KonstaKANG AOSP16-20260428 for Pi 4. Its exact equivalence to the inspected source revision is not established; first boot diagnostics must confirm runtime behavior.

IDriveConnectKitAndroid additionally has SecurityModuleManager, which loads the official installed app's security module via Android package context/class loader. This is a reason to keep Android on the Pi, not evidence we can simply run the module on native Linux.

Remaining gates: official app availability/installation on this image; security-module operation; actual AOA/BMW transport; Apps capability on car; Bluetooth media-session availability to AAIdrive; simultaneous USB data/power design; headless boot; call role/audio handling. These cannot be closed by source inspection alone.

Source: https://github.com/raspberry-vanilla/android_device_brcm_rpi4/tree/b9539c016db0e82dcc3af7c37c15924a77fbf5c1
