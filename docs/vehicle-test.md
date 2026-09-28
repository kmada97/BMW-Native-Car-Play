# First vehicle test — parked, no disassembly

Current target is the Pi running Android; references to an Android phone below describe the optional original baseline and can be performed with the Pi only after its USB/power arrangement is verified. No separate phone purchase is planned.

All results currently **NOT TESTED**. Fill in observations, not assumptions. Keep photos and private identifiers in ignored `local/`.

## Preparation

- Record Android model/OS, official BMW app version, AAIdrive release version and cable used.
- Install the official app from its legitimate store and AAIdrive from its upstream releases/store. Avoid random old APK mirrors.
- Record iDrive menu and navigation map-version text; check build/options for BMW Apps/6NR. Existing TN/HN/MN software fields do not conclusively identify the head unit.
- Check whether ConnectedDrive has Connection Assistant and whether Media lists AUX; locate physical USB/AUX sockets.

## Procedure

1. With the vehicle parked, use its normal infotainment power mode and connect the Android phone to the factory data USB port.
2. Follow the official app and upstream AAIdrive connection guidance. Record whether BMW app authentication/connection actually succeeds.
3. Open an AAIdrive menu on the factory display. Test knob rotation, selection and Back.
4. Return to normal BMW menus and inspect original vehicle information/settings.
5. If AUX exists, select it and observe whether the app screen can remain usable. This coexistence is a dependency of the proposed audio design.
6. Unplug/replug the phone and repeat after a normal vehicle restart. Record recovery behavior.
7. Before later road use, verify equipped parking sensors/cameras and normal warning behavior in a controlled stationary test. Do not create faults to provoke warnings.

## Decision

Pass the initial gate only when a menu renders and iDrive input works through an authenticated USB connection. Missing app capability or failed authentication is a stop for dedicated purchases, not evidence that buying a subscription or coding the vehicle will fix it.

| Observation | Result |
| --- | --- |
| Head unit and Apps capability evidence | NOT TESTED |
| Official app USB connection | NOT TESTED |
| AAIdrive screen | NOT TESTED |
| Knob/select/back | NOT TESTED |
| AUX socket and simultaneous app UI | NOT TESTED |
| Original menus and equipped camera/PDC | NOT TESTED |
| Disconnect/restart recovery | NOT TESTED |

Reference: https://github.com/BimmerGestalt/AAIdrive
