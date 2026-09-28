# Single-device feasibility — first milestone

2026-09-28. User owns neither an Android phone nor a Pi and wants to avoid buying an Android phone. Hold dedicated hardware purchases while evaluating this path. The two-device architecture remains a reference, not a confirmed requirement or the current shopping instruction.

## Success criterion

A single development device connects to the existing BMW USB port, authenticates using an available supported path, displays a minimal menu and receives knob/select/back events. No music, calls or maps are needed to pass this milestone. No such demonstration exists in this repository yet.

## Source audit actually performed

Read-only checkouts are in ignored local/research/. No upstream code copied into our tracked source, no APKs obtained, no car connection attempted.

- BclCarLink commit `7cfd959bba8a742345913c5ce6c5c179c351e189`: `app/src/main/java/io/bimmergestalt/bcl/android/BtConnection.kt` opens Android Bluetooth RFCOMM with the Serial Port UUID and feeds its streams into BCL transport/multiplexing. A search of app/src/main found no USB implementation. Its README describes USB/Bluetooth generally; that is not evidence of a ready USB implementation in this checkout. Bluetooth Apps availability on this 2014 car is unverified and must not be inferred from music Bluetooth support.
- IDriveConnectKitAndroid commit `4a567bc0557bf20a19c0fc03a39fcba69a333ea2`: `SecurityAccess.kt` discovers installed official packages and delegates challenge signing to their security service/module. This is Android-dependent code, not a demonstrated standalone Linux authentication implementation.
- Android Open Accessory documentation describes the host negotiation and device-side bulk endpoints. It is a transport reference, not proof that this BMW accepts a Pi. A Pi candidate must expose the correct USB device role and protocol, with compatible power wiring; an ordinary host-to-host USB cable is not a solution.

## Work order

1. Collect vehicle evidence without disassembly: main iDrive menu, ConnectedDrive submenu/Connection Assistant, map-version screen if navigation is fitted, and center-console USB/AUX sockets. Check build/options for Apps/6NR when available. These can narrow compatibility but do not prove authentication.
2. Trace the actual BMW USB path in available implementation/documentation. Determine what the accessory negotiation, BCL transport and authentication each require; mark undocumented behavior explicitly.
3. Evaluate two single-board approaches separately: native Linux transport plus an available authentication implementation; or Android on a USB-device-capable board running the official app. For the latter, verify app installation/security-service operation, USB accessory support and Bluetooth audio receiver roles. A booting Android image is insufficient.
4. Select hardware only after a plausible complete interface path is documented. Pi 4 remains a Linux audio bench candidate, not an approved single-box BMW bridge.
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
