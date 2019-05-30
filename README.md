# HASS-JablotronSystem
Jablotron component for Home Assistant




Home Assistant component to read sensors as binary sensor.

Currently supports:
- binary sensor, to monitor each Jablotron sensor

## Installation
To use this component, copy all scripts to "<home assistant config dir>/custom_components/jablotron_system".
Edit configuration.yaml and add the following lines:

```
jablotron_system:
  port: /dev/hidraw0
```

Note: Because my serial cable presents as a HID device there format is /dev/hidraw[x], others that present as serial may be at /dev/ttyUSB0 or similar. Use the following command line to identity the appropriate device

```
$ dmesg | grep usb
$ dmesg | grep hid
```

## Debug

Since this is in full development, all debug lines are printed as INFO lines instead of DEBUG lines.
As soon as there is a stable release, debug lines will be transformed into DEBUG lines.

## Demo
Here you'll see a working Jablotron PIR sensor as a binary_sensor:

![Jablotron PIR sensor as binary_sensor in Home Assistant](https://i.imgur.com/nnUBorE.gif)

As a user you don't want to define all your sensors one by one. And even if you would, how do know how to identify them?
So currently the code is using hass.states.set() with an automatically generated entity_id "binary_sensor.jablotron_<device_id>" to keep track on devices which report a new state.

![Automatically add binary_sensor as soon as it changes state](https://i.imgur.com/GtJaDyC.gif)

Here you can see new binary sensors incoming as soon you trigger them:
- Sensor 40_01 is a wireless PIR
- 00_02 is a wireless magnetic door sensor
- 80_01 is another wireless magnetic door sensor

Please ignore the 'binary_sensor.jablotron_door_sensor' sensor. This was the original binary_sensor catching all sensors, regardless the device type, name, id or state.

**Pro's**: as a user you don't need to setup all sensors manually in configuration.yaml. The script will currently create new binary sensors as soon as it receives the right packets.

**Con's**: after a restart of HA, all your binary sensors are gone. Your history is still there, but sensors will be shown as soon as they report. Which could be never if you won't open all windows, doors, etc.

## Todo list:
- add alarm control panel, to arm away, arm home and disarm the system. This is currently under development in another repo (https://github.com/mattsaxon/HASS-Jablotron80), but needs to be combined in a multi platform component.
- optimized use of class JablotronSensor in binary_sensor.py

Work in progress. Any help would be great!
