# BMW Dashboard Probe 0.2

Software-only display and controller experiment for the existing Pi4, Android16, My BMW, AAIdrive1.4.4 and BMW USB connection. **0.2 is built and locally verified, not installed or car-tested.** The original0.1APK is preserved.

## What is established

On2026-10-14 the user manually opened SmartThings, confirmed rotary movement and pressing work, and supplied `IMG_3810.HEIC` showing the0.1 Pi-rendered dashboard on the factory screen. The photo shows a731×480 canvas, requested8fps limit, sampled RPC298ms and input→RPC425ms. These are internal timings, not physical display latency or achieved frame rate. Native BMW overlays and unused right-side space remain. Back/Menu and simultaneous music were not tested. SmartThings later disappeared; the intentional three-minute0.1 expiry is a plausible explanation, not yet confirmed by logs.

## Changes in0.2

- The Canvas adapts to the reported width/height using a uniform scale. Text, circles and controls are no longer horizontally squeezed from a fixed1120×480 design. The RHMI dimensions, placement and native BMW chrome are unchanged; this does **not** establish full-screen coverage or resolve overlays.
- Default rendering is on change. Idle dashboards no longer keep sending full JPEG frames. Input bursts retain each knob action and render their latest state without a frame backlog. Already queued input is processed before another image RPC; an image RPC already in flight still cannot be interrupted to process input.
- USB JPEG quality follows upstream AAIdrive's policy:40 during interaction, then one quality65 refinement after five seconds without input. `Display test` optionally cycles animation cap **off→2→5→8→12→off**; off is the default and normal operating mode.
- One explicitly armed session lasts15minutes including connection setup. It requests focus only once, pauses display traffic while unfocused, and never repeatedly takes focus back. The independent8second RPC watchdog remains.
- The Activity declares `singleTop`, consumes arm extras in both fresh and warm launches, and logs creation/warm-intent/arm consumption.0.1 already had `onNewIntent` in its cached compiled class but no explicit singleTop manifest setting; the exact cause of its observed warm-arm failure is not proven. The service now also drops its cached tunnel on host unbind, so a later warm arm waits for the next AAIdrive connection instead of consuming the arm against a stale port. Runtime warm-arm behavior for0.2 remains to be verified on the Pi.
- The Activity, service and session metrics identify version and a digest of all source/build input hashes. The APK embeds the source hash manifest; version-specific build metadata records exact output hash and local checks.

Navigation, music integration, calls and voice remain demo/unintegrated panels. This APK is **not** a CarPlay receiver. It does not authenticate or project iPhone apps.

```text
Pi dashboard state → Canvas → JPEG → existing BMW USB tunnel → RHMI image
Pi dashboard state ← iDrive rotation / press callbacks       ← factory controller
```

## Integration and bounded operation

Package: `com.kalyan.bmwdashboardprobe`, separate from AAIdrive. It reads the installed AAIdrive signed SmartThings RHMI template/certificate and image/text databases at runtime, without modifying or redistributing them. The fixed template menu label is **SmartThings**; the interior title is Dashboard Probe.

AAIdrive supplies the local tunnel using `io.bimmergestalt.carconnection.service` with `EXTRA_BRAND`, `EXTRA_HOST`, `EXTRA_PORT`, `EXTRA_INSTANCE_ID`. Only localhost is accepted. The app is inert unless explicitly armed and has no boot receiver. Disconnect/Stop/expiry closes only its independent transport. The Etch library's infinite default response waits are bounded by an independent watchdog that closes the transport; shutdown can itself take up to the library's four-second stop timeout.

Coordinator commands for the next already-planned Mac connection (not executed by this build task):

```sh
local/tools/platform-tools/adb -s 100000006f7bb3ac install -r outputs/bmw-dashboard-probe/bmw-dashboard-probe-0.2.apk
local/tools/platform-tools/adb -s 100000006f7bb3ac shell am start -W -n com.kalyan.bmwdashboardprobe/.MainActivity --ez arm true
```

An upgrade can use the same signing certificate and package as0.1. Verify the live service's version/source identity and armed state before deployment; do not infer those from Activity launch success alone. Collect existing metrics in the same connection. No repeated cable exchanges or new user micro-tests are needed to finish local development.

To stop/disarm while Mac-connected:

```sh
local/tools/platform-tools/adb -s 100000006f7bb3ac shell am startservice -n com.kalyan.bmwdashboardprobe/.DashboardService -a com.kalyan.bmwdashboardprobe.STOP
```

## Measurements

Private JSONL: `files/metrics/session-*.jsonl`, collectable through development APK `run-as`. Each session logs version/source identity, reported capabilities/margins, focus callbacks and errors. Each sent frame logs JPEG bytes/quality, revision, included input count, rendering/encoding time and synchronous image RPC completion. Input logs separate callback-to-worker delay from callback-to-frame-RPC completion.

`rpc_ms` measures synchronous image-set RPC duration. `callback_to_rpc_complete_ms` starts when the Pi receives the newest input included in that frame. Neither proves when pixels appear on the screen. Burst input may share one updated image; all state changes still apply. The displayed frame cap is optional animation pacing, not achieved FPS. Displayed timing describes the last completed send and does not trigger further frames by itself.

## Build and checks

Run `python3 apps/bmw-dashboard-probe/build.py` from the workspace. Uses existing project-local JDK17/Android35 tools and SHA256-pinned dependencies; no ADB. Cache and separate development signing key are under ignored `local/dashboard-probe/`.

Deliverables:

- `outputs/bmw-dashboard-probe/bmw-dashboard-probe-0.2.apk`
- `outputs/bmw-dashboard-probe/build-result-0.2.json` and current `build-result.json`
- Preserved0.1APK and `build-result-0.1.json`

Build checks:

- Actual AAIdrive1.4.4 template ids: state19, image132/model531, list133/model532, actions362/363, focus6; XML external entities rejected.
- Knob wraparound, detail transitions, input marker and optional animation on/off cycle.
- Idle frame suppression, queued-input priority, input burst coalescing, dirty updates bypassing animation pacing, interaction quality extension, exactly one settled refinement, stale captured revision preservation, slow-RPC pacing without animation backlog.
- Responsive geometry at731×480,1120×480,640×360,200×200,2048×1024; all panels and controls bounded by reported canvas using uniform scale.
- Real Etch loopback peer accepts connection without replying: independent200ms watchdog unblocks authentication. Final0.2 build observed210ms; assertion bound2.5s. Explicit Stop remains nonblocking, cancellation idempotent, later RPCs rejected.
- Java compilation, D8, alignment and APKv2/v3 signature verification.

After build,0.2 embedded source hashes and identity were checked against current sources; compiled manifest version2/0.2 and `launchMode=singleTop` inspected; original0.1SHA256 preserved; signing certificate matches0.1. No Android/device runtime, optical layout or car performance verification was performed for0.2.

## Open-source provenance

Display/input design follows AAIdrive `FullImageView`, `FrameUpdater` and `MapApp` (Walter Huf, MIT). Adaptive JPEG values and five-second window follow `DynamicScreenCaptureConfig` in `MapAppMode.kt`. The probe uses direct Canvas because no navigation engine or Android virtual display is needed for transport testing. IDriveConnectKit0.8 and IDriveConnectKitAndroid0.7 are MIT; Kotlin1.9.20 and Apache Etch are Apache2.0; Bouncy Castle1.46 uses its permissive license. Exact pinned dependencies are in `dependencies.json`, notices in `licenses/` and the APK.

Sources: [AAIdrive](https://github.com/BimmerGestalt/AAIdrive), [IDriveConnectKit](https://github.com/BimmerGestalt/IDriveConnectKit), [IDriveConnectKitAndroid](https://github.com/BimmerGestalt/IDriveConnectKitAndroid), [Apache Etch](https://github.com/apache/etch).
