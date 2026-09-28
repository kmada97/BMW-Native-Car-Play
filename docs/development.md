# Development milestones

## 1. Prove the BMW endpoint

Run upstream AAIdrive unchanged before attempting a custom Android fork. Current upstream source has minSdk 23, compileSdk 35 and targetSdk 36 (inspected 2026-09-28); these are observations, not a pinned working toolchain. Official app authentication remains mandatory. Read upstream build files together with the developer guide, which may lag source. Record a commit SHA when beginning implementation. No Android build performed yet.

Exit: actual factory-screen menu and knob input. See vehicle-test.md.

## 2. Prove the iPhone endpoint on Linux

Use BlueZ plus an explicitly configured audio implementation. BlueALSA documents A2DP sink and HFP hands-free roles, but profile availability is not an end-to-end product. Choose one audio-stack owner to avoid competing PipeWire/BlueALSA profile registrations.

Test media reception/output first, then supported AVRCP metadata and play/pause/next. Add HFP calls separately: bidirectional sound, call answer/end, media duck/resume and echo assessment. Do not promise Siri activation or factory microphone relay before tests. Initial target is Raspberry Pi OS Lite 64-bit; exact package/setup commands will be selected against the installed version.

Exit: repeatable iPhone-to-Linux media and an independently tested call path. `scripts/bench_doctor.py` inventories prerequisites only; it installs nothing, changes no services and does not pair devices.

## 3. Join the endpoints

Start with a minimal Now Playing view and play/pause action. Implement a local authenticated bridge between Linux media service and Android BMW adapter. Define a versioned message schema, request IDs, stale-state handling, bounded reconnects and duplicate-command suppression before enabling controls. Pair explicitly; do not expose an unauthenticated LAN control port. No bridge or car-control service exists yet.

Exit: real iPhone music metadata on BMW display and verified iDrive command round-trip, with AUX audio and return to native BMW UI.

## 4. Extend only after the core works

Calls; destination sharing/native BMW navigation; optional notification access; then packaging. Bluetooth does not export arbitrary Apple Maps/Waze views. Navigation is a separate integration, not a free consequence of Bluetooth pairing.

## 5. Qualify vehicle installation

Verify cold starts, phone reconnects, warning/camera priority, volume, call echo, power loss, storage integrity, temperature and parked draw. Choose vehicle power and mounting after measurements. A desk Pi supply is not a vehicle installation solution.

## Primary references

- https://github.com/BimmerGestalt/AAIdrive
- https://bimmergestalt.github.io/AAIdrive/developers
- https://github.com/BimmerGestalt/BclCarLink
- https://github.com/arkq/bluez-alsa
- https://github.com/arkq/bluez-alsa/blob/master/doc/bluealsad.8.rst

Prior design context was reviewed from the earlier BMW project plan. This repository records the current custom-companion direction; older CarPlay/MMI recommendations are fallback research, not the selected implementation.
