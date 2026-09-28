# Hardware and purchase order

Planning date: 2026-09-28. These are prototype choices, not a proven vehicle kit. No purchases made. Costs below are rough USD planning allowances, not live retailer quotes.

## Get first: BMW compatibility test

| Item | Selection | Purpose |
| --- | --- | --- |
| Borrowed/spare Android phone | Prefer a reasonably recent device that can install the current official My BMW/MINI app and AAIdrive; no SIM needed for initial Wi-Fi setup | BMW USB authentication and factory-screen/control test |
| USB data cable | Match phone socket and actual BMW USB socket; commonly USB-A to USB-C | Data connection; charging-only cable will not work |
| Existing iPhone and computer | Reuse what is available | Everyday source device; setup/documentation |

Do not buy a dedicated Android phone just on an Android-version claim. AAIdrive source currently declares minSdk 23, but the official app's current requirements and successful car authentication are separate constraints. Borrowing is preferable. Budget $0–15 if a phone can be borrowed.

## After the BMW connection works: Linux bench kit

| Qty | Item | Recommendation / constraint |
| --- | --- | --- |
| 1 | Linux computer | Reuse an existing Linux machine; otherwise Raspberry Pi 4 Model B, 2GB or 4GB is a reasonable bench candidate |
| 1 | Power supply | Official Raspberry Pi 15W USB-C supply for Pi 4 desk testing (5.1V/3A); not a vehicle supply |
| 1 | Storage | 32GB or larger reputable microSD, plus reader if needed |
| 1 | Case/cooling | Ventilated Pi 4 case with heatsinks; validate temperature later |
| 1 | Audio output | Start with Pi 4's built-in 3.5mm output and stereo TRS cable if BMW AUX is confirmed; USB DAC is optional if noise/quality requires it |
| 1 | Call-test microphone | Linux-compatible USB microphone, or existing class-compliant USB headset for bench calls |
| Existing | Headphones or powered speaker | Prove bench output before connecting the car |

Pi 4 includes Bluetooth and Wi-Fi. Do not buy an extra Bluetooth dongle until testing indicates it is needed. A monitor is optional: configure network/SSH during OS imaging and administer from the existing computer. Prefer Ethernet during desk testing; decide the Pi/Android in-car local network after both endpoints work independently.

Allow roughly $100–170 for a new Pi bench setup with power, storage, case, cable and basic microphone; borrowing equipment reduces this. A dedicated Android phone and final car power hardware are additional. No exact all-in vehicle price is established.

## Defer until integration succeeds

- Vehicle accessory-socket supply delivering adequate regulated 5V current, with a documented shutdown strategy. The car's USB port is reserved for Android data and is not assumed to power the whole build.
- Final enclosure, mounting, cooling and sleep-current testing.
- Optional USB DAC/noise isolation only after measuring the actual audio path.
- Dedicated Android device only after validating that exact device/app combination.

Do not order an MMI, display, CAN/OBD adapter, LVDS converter or USB CarPlay dongle for this prototype. MMI remains a separate fallback if the BMW app interface fails.

## Sources checked

- [Raspberry Pi 4 specifications](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/): board connectivity and desk setup.
- [Official 15W supply](https://www.raspberrypi.com/products/type-c-power-supply/): 5.1V/3A specification.
- [AAIdrive](https://github.com/BimmerGestalt/AAIdrive): vehicle/app requirements.
