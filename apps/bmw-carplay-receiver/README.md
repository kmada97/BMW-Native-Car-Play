# BMW live CarPlay receiver

> 2026-10-15 user result: the installed269-test image looks much better and audio stutter is much improved. Lag/long startup remain; Pi/case feels hot when stutter recurs, but throttling is unmeasured. Calls provide incoming audio with no working microphone. The289-test refinement build is ready; it is not installed. See ../../docs/development.md for the current evidence and future non-Pi module proposal.


> Latest status —2026-10-14:269-test usability update installed (`outputs/bmw-carplay-usability/`), then paused at the user’s request and Pi power-off requested. Actual phone/SPS1008×400 squarepixels and1006×400 bridge verified. Corrected physical aspect, reserved right options space, and asynchronous one-image replies. New BMW acceptance remains untested; severe in-car audio stutter is unresolved. Earlier242-test desk passes below do not establish car usability. Temporary diagnostic logging is stopped; restart it only when resuming.


An actual xcertplay receiver integrated with the BMW RHMI image/input transport. It replaces the probe's mock dashboard with decoded receiver video. Actual iPhone authentication and CarPlay video have now been verified on the physical Pi. The user has confirmed actual CarPlay on the BMW; responsiveness, startup and call microphone support remain incomplete.

## What is built

- Separate Android package `com.kalyan.bmwcarplay`; AAIdrive and My BMW are preserved.
- MediaCodec → persistent EGL surface → bounded JPEG capture → latest-frame BMW sender. Capture continues without an Activity preview, and stale frames from stopped sessions are rejected.
- Current selected wide-ID4 profile negotiates1008×400 square-pixel phone video into a1006×400 BMW content rectangle. Native header/clock, left controls and an80px right options allowance remain outside it. Reported dimensions take precedence; the profile is explicit because this car omits dimensions. It does not remove native BMW chrome.
- BMW rotary/press → the receiver's existing AirPlay knob HID. Only live sessions accept phone inputs. OEM Back/Menu are not intercepted.
- Focus requested once after a live receiver frame is ready, never repeatedly after leaving the app. Live receiver sessions continue until stopped or disconnected; only the synthetic decoder test retains the 15-minute bound.
- Local H264 fixture for checking decoder/capture, labeled **LOCAL VIDEO TEST / NO PHONE** in every frame. It has no phone audio or authentication and never masquerades as a live session.
- One launcher with live receiver, local video test, authentication settings and stop controls. Live receiver startup is blocked until software authentication inputs are configured; configuration alone does not prove acceptance.

## Status and limits

**Latest evidence (2026-10-15):** user confirms installed269-test build looks much better and audio stutter is much improved. Lag/startup remain slow. Calls have output but no microphone. Known Pi4 simulated input was incorrectly advertised; prepared289-test build gates that capability and capture, without claiming to select the iPhone's BMW hands-free route. It also adds headless initial startup, identical-pixel JPEG suppression, one settled Q65 frame after1.2seconds, and bounded automatic health/startup traces. Full APK/source and build evidence: `outputs/bmw-carplay-refinement/`. This version is built and signature-verified, not installed or car-tested. Prior results below are historical.

The automatic traces are app-private and numeric metadata only. Read `files/bmw-health/` and `files/bmw-startup/` with `collect_runtime_health.py --serial SERIAL --output LOCAL_DIR`; no playback, pairing or settings change. Missing thermal data is unavailable, not a zero temperature or proof of healthy cooling.

**Historical242-test installed update (2026-10-14):** user/photos confirm real CarPlay on the BMW, including Maps and music, but identify partial-width rendering, BMW clock/navigation overlays, sluggish controls and recurrent music stutter. The current242-test build and full source are in `outputs/bmw-carplay-performance/`; `pi-verification.json` identifies its exact hash and evidence. All earlier results below describe earlier builds.

The new layout reserves194px at the left and80px at the top of the selected1280×480 profile, giving1081×400 clear content. Preference `bmw_bridge/wide_id4_display_profile` is explicitly selected; missing dimension fallbacks are logged separately from actual capabilities. Normal app coordinates replace negative padding, and geometry is reapplied when BMW focus returns. Phone geometry is persisted for the next connection and independent of the HDMI preview.

Phone knob commands now enqueue before any blocking image RPC; native acknowledgments precede subsequent frames, and list recenter calls coalesce. Capture retains the final dirty frame until due, adapts JPEG quality/cadence to measured transfer time, reuses readback memory and avoids new readbacks while an encoded frame is pending. Audio retains one codec input until accepted, drains output during idle/backpressure, releases codec buffers before audio writes and uses guarded audio-thread priority. Counters contain timing/counts only.

On the actual Pi, both phone authentication stages, wide live video and armed1081×400 frames passed. A40.8-second same-track audio sample had zero queue/codec drops, zero underruns, zero logged HAL/ALSA drops and zero IPv6 UDP error deltas. The500ms music buffer remains. This is Mac-connected evidence; the new BMW geometry, physical responsiveness, sustained in-car music/navigation and audible quality remain pending.

The initial build passed 193 JVM tests and APK signature verification. On 2026-10-14, the APK was installed on the connected Pi. Its `c2.v4l2.avc.decoder` decoded the synthetic H264 fixture into advancing 731×480 JPEGs; root visually checked orientation, colors, lettering and fit. Same-process warm stop/restart passed, and the local test was then stopped. Earlier isolated Android16 emulator checks also passed. Final build and runtime evidence are under `outputs/bmw-carplay-receiver/` and ignored `local/receiver-checkpoint/`. These checks prove the Pi decoder/capture path, not live iPhone reception, BMW transfer performance or physical input latency.

**Live result (2026-10-14):** the final reconnect build passed 213 tests. A pinned, public MacPlay software identity passed certificate/key consistency and ECDSA checks, was stored only in app-private files, and was accepted by the real iPhone in both Bluetooth bootstrap and Wi-Fi tunnel authentication. Pair-verify, SETUP/RECORD, handoff and actual H264 decoding followed. The real CarPlay home screen was visually verified on the Pi. See [evidence and provenance](../../docs/development.md).

Pi configuration uses `LOCAL_ONLY_HOTSPOT` because this Android image lacks WifiP2pManager. The code accepts a usable hotspot IP when Android hides the MAC. The selectable `BmwHomeActivity` HOME target is configured for automatic startup. Actual reboot recovery passed without a manual app launch or another phone reconnection: both authentication stages, live H264 decoding and the 731×480 BMW frame path returned automatically. The bridge reports streamReady=true and remains armed. The combined physical car session remains to be validated. The shared identity is experimental and may cease to be accepted; no private key is embedded in the APK or source archive.

BMW screen/iDrive round-trip, AUX playback from this receiver, ignition auto-open, full-panel OEM use and calls/Siri microphone remain unverified. The existing music bridge remains available. AUX establishes output only.

**First-car follow-up (2026-10-14):** the BMW enumerated USB accessory mode, but My BMW did not start its connection service. The retained log showed competing HOME/BOOT navigation during its USB Activity startup. The installed 222-test build removes the duplicate boot launch when this app is HOME and defers automatic HOME/checkpoint navigation until resumed and window-focused. This addresses the observed race; BMW tunnel recovery still needs a car test. An actual Mac-connected reboot of this new build skipped the duplicate BOOT launch and automatically restored authenticated live phone video, armed 731×480 capture, and the saved 500ms buffer. See `startup-audio-verification.json` in the live output directory.

The existing main-media buffer preference is now 500ms. A same-track 20.4-second playback measurement showed a 24,000-frame stereo buffer, zero underruns and no logged HAL transfer skips; the previous 8,196-frame track accumulated underruns. This is a short software measurement, not confirmation of smooth audible AUX output. The trial also restarted the receiver. Keep Wi-Fi enabled for wireless CarPlay.

The live APK and complete modified source are in `outputs/bmw-carplay-live/`. Build separately from the original decoder checkpoint with:

```sh
python3 apps/bmw-carplay-receiver/build.py --output-dir outputs/bmw-carplay-live --artifact-name bmw-carplay-receiver-live
```

`configure_pi_receiver.py` installs operator-selected authentication files into private app storage, verifies supplied hashes, and sets the receiver preferences without exposing key bytes. It preserves existing preferences and leaves the app stopped. Use the real receiver launch path after provisioning; the older preparation script below is only the historical decoder check.

## One connected-Pi preparation pass

Once the Pi is explicitly connected to the Mac, the agent can run:

```sh
python3 apps/bmw-carplay-receiver/prepare_pi.py --serial PI_SERIAL
```

This checks the target, validates the built APK checksum, installs it, stops only our older dashboard probe, launches the local decoder check and automatically collects advancing-frame evidence. It does not change Wi-Fi, Bluetooth, AAIdrive/My BMW, phone settings or firmware. It is not a live phone acceptance test. Do not send the user to the car solely because this script passes; batch the next car session around a genuinely ready authenticated receiver.

## Rebuild and source

Upstream: [xcertplay](https://github.com/shilapi/xcertplay), pinned to `8b01399a17ef8b3193931a2ff4ed93b410a73570`, GPLv3. The complete modified source ZIP accompanies the APK. `xcertplay-bmw.patch` is the reproducible change against that pin; third-party license notices are included in the source and app assets.

Task-local tools: Java25, Gradle9.5, AndroidSDK37.0/BuildTools36, NDK28.2.13676358. The local build script invokes the pinned NDK clang directly for the unchanged I2C JNI source because ndk-build rejects spaces in this project path; the checkpoint APK targets ARM64. The normal upstream native-build path remains available for checkouts without spaces.

```sh
python3 apps/bmw-carplay-receiver/build.py --apply-patch
```

The build checks the base revision and pinned BMW dependencies, compiles, runs common/shared unit tests, checks the APK signature and embedded source hashes, and packages the APK plus full source. Development signing credentials are local build-only credentials, not MFi/CarPlay identities. No installation is part of the build command.

BMW transport uses BouncyCastle1.79 for certificate-chain assembly instead of importing the probe's obsolete1.46 provider into the receiver. The removed legacy helper is replaced by a tested equivalent; this handles BMW Apps authentication and does **not** solve Apple's receiver authentication.
