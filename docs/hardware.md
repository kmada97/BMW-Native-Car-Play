# Buy now: Pi 4 development kit

Decision: 2026-09-28, following user's request to proceed with a Pi purchase. This supersedes earlier hold-purchases and borrowed-Android-first instructions. Recommended for prototyping; BMW compatibility is not proven.

| Quantity | Item | Selection |
| --- | --- | --- |
| 1 | **Raspberry Pi 4 Model B, 4GB RAM** | Exact preferred board; built-in Bluetooth/Wi-Fi, analog audio and USB-C gadget-capable port |
| 1 | Official Raspberry Pi **15W USB-C supply** | Pi 4 5.1V/3A wall supply for the desk |
| 1 | **64GB microSD** | Reputable A1/A2 card; 32GB works for initial image, 64GB gives development room |
| As needed | microSD reader | Compatible with the Mac's ports |
| 1 | Pi 4 case with heatsinks and fan | Access to USB-C, micro-HDMI and audio jack |
| 1 | **Micro-HDMI to HDMI cable** | Desk setup using an existing TV/monitor; not a vehicle screen |
| 1 | **3.5mm stereo TRS male-to-male cable** | Pi analog output to confirmed BMW AUX, and desk speakers |
| Existing/borrow | USB keyboard/mouse and TV/monitor | Initial Android setup; no permanent extra screen planned |
| Optional | Second microSD, 32GB+ | Separate Linux audio experiment without overwriting Android |
| Later | Linux/Android class-compliant USB mic | Only when starting bidirectional call tests |

Purchase through [Raspberry Pi's approved-reseller selector](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/). Do not substitute a Pico, Pi 400 keyboard or Zero. A Pi 5 is capable of USB gadget mode too, but Pi 4 gives us a built-in analog output and a concrete Android device-tree target. 4GB is our development choice, not an upstream minimum (the selected Android image documents 2GB minimum).

Allow roughly $100–160 for board/power/storage/cooling/cables, excluding a new monitor or keyboard. This is a planning allowance, not a verified retailer quote or current stock claim. Check kit contents to avoid duplicate accessories.

## What this purchase gets us

A single-board test platform for Android-based BMW authentication/USB experiments and Bluetooth iPhone audio reception. Android runs on the Pi itself; no separate phone is on the current shopping list. Start with [Pi first boot](pi-first-boot.md).

## Do not buy yet

MMI, replacement display, CAN/OBD adapter, CarPlay dongle, external Bluetooth dongle or GPIO power hardware. None is needed for the first desk experiment.

Vehicle power is a separate unresolved selection. Pi USB-C is both the power input and the device data port; simultaneous BMW USB data and independent power needs a verified arrangement that prevents backfeeding. No Y cable or car USB power assumption is approved by this plan. Use the wall supply with Wi-Fi/Ethernet for the first boot.

Sources checked 2026-09-28:
- https://www.raspberrypi.com/products/raspberry-pi-4-model-b/
- https://www.raspberrypi.com/products/type-c-power-supply/
- https://github.com/raspberrypi/rpi-usb-gadget (Pi 4/5 gadget data uses USB-C)
- https://konstakang.com/devices/rpi4/AOSP16/
