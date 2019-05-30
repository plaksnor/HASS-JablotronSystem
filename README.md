# HASS-JablotronSystem
Jablotron component for Home Assistant




Home Assistant component to read sensors as binary sensor.

Currently supports:
- binary sensor, to monitor sensors

Feature list:
- alarm control panel, to arm away, arm home and disarm the system. This is currently under development in another repo (https://github.com/mattsaxon/HASS-Jablotron80), but needs to be combined in a multi platform component.

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

Since this is in full development, all debug lines are printed as INFO instead of DEBUG.
As soon as there is a stable release, debug lines will transformed into DEBUG lines.
