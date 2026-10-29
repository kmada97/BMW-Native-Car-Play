# Pi USB data and power

Desk USB communication verified 2026-10-13; vehicle operation and permanent installation remain untested.

## Verified desk setup

The Pi 4 Model B Rev 1.5 booted Android 16 through the photographed 8086 USB-C/PWR splitter (without barrel jack) using the Vilros kit supply, model FJ-SW126G0513000U, rated 5.1V DC / 3A. The Mac enumerated it as `18d1:4ee7` and established authorized ADB over a physical USB transport. Android reported `connected=true`, `configured=true`, and `kernel_state=CONFIGURED`.

The readable `rpi_volt` sensor reported no active undervoltage alarm at sampling, with CPU temperature around 36–37°C. Firmware historical throttling flags could not be read because `/dev/vcio` is root-only; permissions were not changed. These observations do not establish measured voltage, electrical isolation, sustained-load reliability, or BMW compatibility. Evidence is in ignored `local/usb-bench-20261013-114212/`.

A read-only [Android Open Accessory GET_PROTOCOL request](https://source.android.com/docs/core/interaction/accessories/aoa) returned version 2 (`02 00`) from the exact observed Pi. A subsequent controlled desk test on 2026-10-13 sent neutral `Local Bench / Pi USB Accessory Test / 1.0` identification and START once. The same serial re-enumerated as `18d1:2d01`, with accessory and ADB interfaces and bulk IN/OUT endpoint pairs; Android reported the test accessory connected/configured. No BMW identity, authentication or application bulk traffic was attempted. Evidence: ignored `local/car-ready-20261013/aoa-mode-test.json` and `accessory-usb.txt`.

After the test, File Transfer (MTP) was selected as the default unlocked USB mode, following AAIdrive's USB connection guidance. Mac enumeration is now `18d1:4ee2` with authorized ADB, and Android reports MTP configured. The old `sys.usb.config` property still reads `adb` on this HAL, so use actual descriptors and `dumpsys usb` for current function evidence.

The existing `su 0` capability subsequently allowed `vcgencmd get_throttled` to be read without changing device-node permissions; it returned `0x0` after the latest reboot. That supersedes the earlier access limitation for this boot, not the absence of a voltage/isolation measurement. Anker car power is still untested.

Bluetooth-to-AUX music still has intermittent stutter. Pi Wi-Fi is OFF, Bluetooth ON, and `persist.vendor.audio.refine_position=false` is retained after improving local test-tone playback. On 2026-10-13 the user explicitly chose to investigate audio in parallel with parked-car integration testing. This is not a stable-audio pass.

The Pi 4 USB-C port carries both its gadget data and power. Its USB-A ports do not substitute for this device-side connection. Network ADB was used during initial audio setup; physical USB ADB is now confirmed as well.

The user owns the **8086 USB-C/PWR Splitter, no barrel jack**: [manufacturer listing/pin mapping](https://lectronz.com/products/usb-c_pwr-splitter).

The manufacturer maps USB2 data and ground between DATA and DATA/POWER while routing the separate POWER input's 5V to DATA/POWER. Its DATA input does not carry VBUS through that mapping. Functional enumeration is now confirmed; the actual board's voltage and isolation have not been independently measured. The maker specifies the official Raspberry Pi supply and cautions about other supplies; the observed Vilros result is a functional test of this particular setup, not manufacturer certification.

Bench wiring:

```text
Kit Pi supply -> splitter POWER
Mac USB data -> splitter USB2 DATA
splitter DATA POWER -> short USB-C to USB-C data cable -> Pi USB-C
```

Use a short cable rated for at least 3A that also carries USB2 data. The eventual BMW host cable would be USB-A to USB-C data. No host-to-host USB-A cable, passive Y cable, or GPIO injection is planned.

The maker explicitly describes this splitter as outside USB specification and warns against treating it as an Android Auto/CarPlay splitter. Our use is a Pi gadget bench experiment; it does not establish BMW compatibility. Accessory-mode enumeration now passes; sustained operation and BMW application transport remain to be tested. The user owns no multimeter/test adapters; the earlier blanket tool-purchase/measurement prerequisite was superseded on 2026-10-02. No additional test-tool purchase is required for the present ready-made-board functional test.

Vehicle deployment still needs protected mounting, heat/restart checks and shutdown/parked-current handling. The owned Anker A2724 car charger is rated 5V/3A per USB-C port, but it has not been tested with this splitter/Pi. Test that supply with the Pi before adding BMW USB data. The splitter is not a regulator, ignition controller or UPS. Do not connect 12V to it. Keep the exposed board on a dry nonconductive surface during desk work.
