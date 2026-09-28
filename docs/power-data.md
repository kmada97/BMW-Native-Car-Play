# Pi USB data and power

Research candidate selected 2026-09-28; not bench-tested or approved for permanent vehicle installation.

The Pi 4 USB-C port carries both its gadget data and power. Its USB-A ports do not substitute for this device-side connection. Start with the kit wall supply and network ADB for audio testing.

For a later USB bench test, the **8086 USB-C/PWR Splitter, no barrel jack** is a specific candidate: [US distributor](https://www.pishop.us/product/usb-c-pwr-splitter-without-barrel-jack/) and [manufacturer listing/pin mapping](https://lectronz.com/products/usb-c_pwr-splitter).

The manufacturer maps USB2 data and ground between DATA and DATA/POWER while routing the separate POWER input's 5V to DATA/POWER. Its DATA input does not carry VBUS through that mapping. This addresses the intended separation of host data and Pi power, but electrical measurements and enumeration must confirm the actual board before car use.

Bench wiring:

```text
Kit Pi supply -> splitter POWER
Mac USB data -> splitter DATA
splitter DATA/POWER -> short USB-C to USB-C data cable -> Pi USB-C
```

Use a short cable rated for at least 3A that also carries USB2 data. The eventual BMW host cable would be USB-A to USB-C data. No host-to-host USB-A cable, passive Y cable, or GPIO injection is planned.

The maker explicitly describes this splitter as outside USB specification and warns against treating it as an Android Auto/CarPlay splitter. Our proposed use is a Pi gadget bench experiment, not a conventional CarPlay dongle; that does not establish BMW compatibility. First verify isolation/no host backfeed, stable voltage under load and accessory-mode enumeration on the bench. Do not use a generic PD dock as a substitute.

Vehicle deployment still needs a regulated 5V/3A source, protected mounting, heat/restart checks and shutdown/parked-current handling. The splitter is not a regulator, ignition controller or UPS. Do not connect 12V to it. Selecting a final car supply remains dependent on the successful bench experiment and available car power sockets.
