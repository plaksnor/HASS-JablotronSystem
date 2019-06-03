# HASS-JablotronSystem
Jablotron component for Home Assistant




Home Assistant component to arm and disarm the alarm system and read sensor states.

Currently supports:
- alarm control panel, to arm and disarm the Jablotron alarm system
- binary sensor, to monitor each Jablotron sensor

## Installation
To use this component, copy all scripts to "<home assistant config dir>/custom_components/jablotron_system".
Edit configuration.yaml and add the following lines:

```
jablotron_system:
  port: /dev/hidraw0
  code: 1234
  code_arm_required: True
  code_disarm_required: True
```

Note: Because my serial cable presents as a HID device there format is /dev/hidraw[x], others that present as serial may be at /dev/ttyUSB0 or similar. Use the following command line to identity the appropriate device

```
$ dmesg | grep usb
$ dmesg | grep hid
```

## How it works
Platforms will be shown on the http(s)://domainname<:8123>/states page.
- The alarm control panel is always available.
- Sensors will automatically be added as soon as they are triggered.
- In the 'Settings' -> 'Customization' section of HA you'll be able to customize each sensor:
  - friendly_name : give it a human readable name
  - device_class  : give it a class with matches the device

## Tested on
- Home Assistant 0.94.0b3, installed in docker at RPi 3 model B+
- Jablotron JA-101K-LAN, firmware: LJ60422, hardware: LJ16123

## Demo
Here you'll see a working Jablotron PIR sensor as a binary_sensor:

![Jablotron PIR sensor as binary_sensor in Home Assistant](https://i.imgur.com/nnUBorE.gif)

As a user you don't want to define all your sensors one by one. And even if you would, how do know how to identify them?

![Automatically add binary_sensor as soon as it changes state](https://i.imgur.com/GtJaDyC.gif)

Here you can see new binary sensors incoming as soon you trigger them:
- Sensor 40_01 is a wireless PIR
- 00_02 is a wireless magnetic door sensor
- 80_01 is another wireless magnetic door sensor

![Binary sensors with specific device class](https://i.imgur.com/kz6k6i8.gif)

Please ignore the 'binary_sensor.jablotron_door_sensor' sensor. This was the original binary_sensor catching all sensors, regardless the device type, name, id or state.

**Pro's**: as a user you don't need to setup all sensors manually in configuration.yaml. The script will currently create new binary sensors as soon as it receives the right packets.

**Con's**: after a restart of HA, all your binary sensors are gone. Your history is still there, but sensors will be shown as soon as they report. Which could be never if you won't open all windows, doors, etc.

## Todo list:
- Retain discovered sensors in a configuration file and read this file as soon as HA starts.

## Credits
Big thanks to @mattsaxon!

Work in progress. Any help would be great!

