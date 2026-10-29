# BMW Startup Helper

The Pi's AAIdrive connection listener can stop before the BMW finishes attaching USB. This small Android app starts AAIdrive through its existing exported start receiver when the Pi detects the actual BMW USB accessory. It does not modify AAIdrive or My BMW.

## Behavior

- The user enables the helper once. It then starts a `connectedDevice` foreground service after `BOOT_COMPLETED`, with an ongoing status notification and Disable action.
- Polls `UsbManager.getAccessoryList()` every 10 seconds. It requires exact manufacturer `BMW Group` and model `BMW`.
- Sends the ordinary `me.hufman.androidautoidrive.CarConnectionListener_START` broadcast to AAIdrive's exported receiver at most five times, 10 seconds apart, per observed attachment. It stays quiet on that attachment after those requests.
- A protected USB-detached broadcast or a poll finding no BMW re-arms the next attachment. An ordinary app cannot inspect another app's running services, so the helper cannot stop retries based on verified AAIdrive music-service success. Sending a request does not establish success.
- Repeated starts of the existing helper service preserve the retry counter. A helper process restart loses that in-memory state and allows five requests again if the BMW remains attached.
- Uses elapsed time, not the Pi's unreliable offline calendar clock. No audio, Bluetooth pairing, USB ownership, settings, network, root, or AAIdrive process changes. It never force-stops another app or opens a USB stream.

The connected-device service requires a granted `BLUETOOTH_CONNECT` permission. The helper does not read Bluetooth devices or media; that permission satisfies the platform's service prerequisite without requesting BMW USB ownership. Notification permission makes status visible. It has no Internet permission. AAIdrive's existing battery-optimization exemption permits its normal receiver to start its own foreground service.

## Build

From the repository root:

```sh
python3 apps/bmw-startup-helper/build.py
```

The build uses the existing **project-local** JDK and Android tools under `local/car-start-helper/toolchain/`. Their verified versions, primary download URLs, publisher hashes and SHA256 values are in `toolchain-manifest.json`. No Gradle, external Java dependencies or global installation is needed. Archive layouts are:

```text
local/car-start-helper/toolchain/
  jdk/jdk-17.0.20.1+1/Contents/Home/
  sdk-platform/android-35/android.jar
  sdk-build-tools/android-15/
```

The script compiles/runs the pure Java retry-policy test, compiles Android sources, builds DEX/APK, signs with a local development key and verifies the signature. Build outputs and the signing key stay under ignored `local/car-start-helper/build/`. `BMW_HELPER_BUILD_DIR` optionally selects another build-output directory; the existing local signing key is reused. Preserve that key for compatible updates; it is not included in the published output folder.

The reviewed first APK is in `outputs/bmw-startup-helper/` with `SHA256SUMS` and a build-validation record. A rebuild can differ in hash due to archive/signing metadata. Publish a rebuilt APK only after checking its new hash and validation.

## Setup and validation

Root agent owns Pi access. Install only the reviewed APK on the explicitly selected Pi. Grant `BLUETOOTH_CONNECT` and `POST_NOTIFICATIONS`, then open the helper and press **Enable startup helper**. For local setup, launching its MainActivity with boolean extra `enable=true` performs that same action. Merely opening the app does not enable it.

Test with Android Home in the foreground and the BMW disconnected for more than 30 seconds, then attach BMW USB while retaining separate power. Inspect log tag `BMWStartupHelper`, AAIdrive's actual music-service connection, car menu and controls. Also test an actual cold boot and a detach lasting over 30 seconds. The initial build was compilation/test/signature verified; cold boot was not verified when it was prepared. A current successful session must not be recorded as cold-boot success.

Policy tests cover no requests without a BMW, suppression of duplicate callbacks, the five-request limit, remaining quiet on an unchanged attachment, and reset on both fast detach events and polled absence. On-device background delivery, service permission behavior and boot need integration verification. This helper does not address audio stutter or clock persistence.

## Disable or remove

Press **Disable startup helper** in the app or **Disable** in its notification. This clears the enabled preference and stops its watcher; subsequent boots do not start it. Uninstalling package `com.kalyan.bmwstartup` removes the helper entirely. Neither action stops AAIdrive or changes My BMW, audio or USB defaults.

## References

- [Android foreground-service types](https://developer.android.com/develop/background-work/services/fgs/service-types#connected-device)
- [Background service start exemptions](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start)
- [UsbManager API](https://developer.android.com/reference/android/hardware/usb/UsbManager)
- Local AAIdrive `CarConnectionListener.kt` and `MainService.kt` in `local/research/AAIdrive/`.
