# First vehicle test — parked, no disassembly

> 2026-10-15 user result: the installed269-test image looks much better and audio stutter is much improved. Lag/long startup remain; Pi/case feels hot when stutter recurs, but throttling is unmeasured. Calls provide incoming audio with no working microphone. The289-test refinement build is ready; it is not installed. See docs/development.md for the current evidence and future non-Pi module proposal.


> Latest status —2026-10-14:269-test usability update installed (`outputs/bmw-carplay-usability/`), then paused at the user’s request and Pi power-off requested. Actual phone/SPS1008×400 squarepixels and1006×400 bridge verified. Corrected physical aspect, reserved right options space, and asynchronous one-image replies. New BMW acceptance remains untested; severe in-car audio stutter is unresolved. Earlier242-test desk passes below do not establish car usability. Temporary diagnostic logging is stopped; restart it only when resuming.


Current target is the Pi 4 running Android 16, with My BMW 6.9.2 and AAIdrive 1.4.4 installed. Desk USB ADB and neutral AOA accessory-mode enumeration via the 8086 splitter and Vilros wall supply passed on 2026-10-13. The user explicitly requests one combined parked-car session, with final wiring and one results report. This supersedes the separate Mac-first Anker power gate. Earlier music-bridge results below are historical; they do not establish live CarPlay on the BMW.

## Current combined check — 2026-10-14

Latest user report: the Pi eventually lost power with the car and loaded normally afterward. This is one reported successful power-loss boot; automatic phone/BMW reconnection and the updated screen/control/audio result are not yet separately confirmed. No additional restart is requested.

Real CarPlay reached the BMW after the startup fix, confirmed by user and Maps/music photos. The user then reported narrow rendering, overlapping BMW clock/left navigation, sluggish response and recurring music stutter. Those are the current acceptance issues.

The242-test update is installed on the Mac-connected Pi, phone reconnected and live display armed. Leave power/AUX connected, move only USB2 DATA back to BMW, then check together: CarPlay uses the wide clear area below/right of native overlays; rotary/click responds better; music remains smooth while navigation is visible. Open SmartThings if not already focused. No restart, pairing reset or app download is required. A successful Mac audio sample does not substitute for this in-car result.

## Live receiver attempt — 2026-10-14

The phone-to-Pi wireless CarPlay session works, independently of the Pi-to-BMW USB link. The first car attempt enumerated USB accessory mode but showed generic BMW Connected install guidance; My BMW's connection service never started. User reported severe audio stutter. Data was returned to Mac while power stayed on, preserving the logs.

A startup fix is installed (222 passing unit tests), and the music buffer is set to 500ms after a 20.4-second playback measurement with zero track underruns and no logged HAL transfer skips. This does not yet prove an audible fix or BMW screen operation. The next car session should keep Pi power on, move only splitter DATA from Mac to BMW, keep AUX connected and iPhone Wi-Fi/Bluetooth on, then check the actual CarPlay screen, knob and music together. Allow My BMW to open the USB tunnel; do not download the obsolete app suggested by the generic car prompt. No repeated power cycles are part of this test.

The 2026-10-13 parked test established BMW USB accessory transport, AAIdrive authentication to BMW ID4++, visible Google/Audioplayer entries, and iDrive interaction events. AAIdrive needed a temporary startup retry; unattended startup is not verified. Initial music metadata and track controls failed because the Pi's AVRCP connection lacked remote target capabilities. A paired Bluetooth reset restored Android metadata and a verified Pi-to-iPhone next-track command at19:33 CDT; the final BMW recheck now passes song information and next-track control by user report. At19:41 CDT the user reported everything tested working except artwork and paused the project. Audio works in that session; earlier intermittent stutter still needs sustained validation. Keep photos and private identifiers in ignored `local/`.

## Preparation

- Record Android model/OS, official BMW app version, AAIdrive release version and cable used.
- My BMW was installed from Google Play and signed in; the user unlocked its PIN screen after the latest reboot. AAIdrive reports ready to connect and waiting for the car. Both apps have Bluetooth/notification permissions and are exempted from device-idle battery restrictions. The media notification listener is enabled; this does not enable message forwarding.
- Default unlocked USB mode is File Transfer (MTP), with ADB enabled. Wi-Fi is OFF and Bluetooth ON. User confirms the USB-A-to-USB-C data cable and extra USB-C-to-USB-C Anker power cable are on hand. Keep the short splitter-to-Pi cable in place.
- Bring the Mac and working desk data cable for the end-of-test diagnostic collection and normal shutdown. The initial hookup goes directly to BMW USB; no separate Mac power check is required. Connect only one data host at a time.
- This Pi has no confirmed battery-backed clock. With Wi-Fi off, the latest reboot reset time to the image's April 28 build date. Time persistence remains unfinished; record it as a possible login/service issue if encountered rather than adding a separate prerequisite to this combined test. Do not assume cloud login/navigation works offline.
- Record iDrive menu and navigation map-version text; check build/options for BMW Apps/6NR. Existing TN/HN/MN software fields do not conclusively identify the head unit.
- Connection Assistant, AUX and physical USB/AUX sockets are confirmed. AAIdrive reports BMW ID4++ and successfully authenticates; a formal vehicle-options lookup has not been performed.

## Procedure

1. Pi was shut down cleanly on 2026-10-13. In the parked car, keep the exposed splitter insulated from metal. Connect all final wiring: Anker USB-C → splitter POWER; splitter DATA POWER → Pi USB-C; factory BMW USB-A → splitter USB2 DATA using the A-to-C data cable; Pi 3.5mm → BMW AUX. Apply Anker power from the powered 12V socket last. Allow about 2–3 minutes to boot.
2. Select Raspberry Pi 4 as the iPhone Bluetooth audio output and play music. In iDrive select AUX, then inspect ConnectedDrive / Connection Assistant for connection or new AAIdrive/Audioplayer entries. The BMW Apps label is not clickable. A missing Apps screen does not prevent checking AUX audio independently.
3. In any new app screen, test knob rotation, selection and Back, plus track controls if offered. Check that AUX music continues while the app UI is visible. Listen for about a minute and note any stutter/restarts. Return to original BMW menus and check ordinary controls still work. Include equipped camera/PDC only through its normal stationary controls; do not move the car or create faults just to test them.
4. Keep Anker power connected and reconnect only BMW USB once. Allow 30–60 seconds and observe whether the app returns. This checks USB recovery without an abrupt Pi power cut. Full ignition recovery and unattended power handling remain separate engineering checks until normal shutdown is arranged.
5. Send one combined result: Apps screen appeared? Knob/select/back worked? AUX audio and app screen coexisted, with or without stutter? USB reconnect recovered? If no Apps entry appears, include one Connection Assistant photo and which other tests worked. Do not require separate assistant replies between these checks.
6. At the end, keep Anker power on, replace only BMW data with the Mac data cable, collect available diagnostics together and shut Android down normally before removing power. This is end-of-session cleanup, not a prerequisite power gate. Ignition-aware automatic shutdown is not implemented.

## Decision

Pass the initial gate only when a menu renders and iDrive input works through an authenticated USB connection. Missing app capability or failed authentication is a stop for dedicated purchases, not evidence that buying a subscription or coding the vehicle will fix it.

| Observation | Result |
| --- | --- |
| Head unit and Apps capability evidence | AAIdrive identifies BMW ID4++; authenticated session established |
| Official app USB connection | BMW accessory attached; MyBMW transport/security module works |
| AAIdrive screen | Google/Audioplayer visible; final post-idle connection works with startup helper installed |
| Knob/select/back | Source selection and track-button events reach AAIdrive; full Back/menu check not reported |
| Song information and next track | PASS in final BMW recheck after paired Bluetooth reset; artwork absent |
| AUX socket and simultaneous app UI | Working in latest user test; prior intermittent stutter still needs longer validation |
| Original menus and equipped camera/PDC | NOT TESTED |
| Disconnect/restart recovery | Final connection succeeded after Home idle with helper installed; cold boot/ignition recovery untested |

Reference: https://github.com/BimmerGestalt/AAIdrive
