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
Both options 'port' and 'code' are required.

Note: Because my serial cable presents as a HID device there format is /dev/hidraw[x], others that present as serial may be at /dev/ttyUSB0 or similar. Use the following command line to identity the appropriate device

```
$ dmesg | grep usb
$ dmesg | grep hid
```

## How it works
Platforms will be shown on the http(s)://domainname<:8123>/states page.
- The alarm control panel is always available.
- Sensors will automatically be added as soon as they are triggered.
- Discovered (triggerd) sensors will be stored in config/jablotron_devices.yaml and get loaded after restart of HA.
- In the 'Settings' -> 'Customization' section of HA you'll be able to customize each sensor:
  - friendly_name : give it a human readable name
  - device_class  : give it a class with matches the device

## Tested with
- Home Assistant 0.94.0b3, installed in docker at RPi 3 model B+
- Jablotron JA-101K-LAN, firmware: LJ60422, hardware: LJ16123
- Jablotron magnetic and PIR (motion) sensors

## Demo

First you start triggering several sensors. They'll add up as soon as they are triggered:
![Jablotron sensors detected](https://i.imgur.com/H8oSrii.gif)

Each sensor gets it own entity_id with a unique number. This number represents the ID or position in J/F/O-link, the Jablotron software to configure your alarm system. If you're not able to open up J/F/O-link but you are able to access your alarm system over the internet, you could use the Jablotron app on your phone and go to Devices to get a list of devices. The order is the same as the numbers of the entity_id's.

Discovered sensors are automatically stored in your config/jablotron_devices.yaml file. You could trigger all sensors, but you could also manually change this file and restart HA in order to see them all.

After all sensors have been added, you could give them more friendly names in the Customization section:
![Customize Jablotron sensor in Home Assistant](https://i.imgur.com/DhDgQoB.gif)

At then end, you should be able to see all kind of sensors like here:
![Jablotron sensors customized in Home Assistant](https://i.imgur.com/07gn2QP.gif)

Here you'll see a Jablotron PIR sensor working as a binary_sensor, detecting movement:
![Jablotron PIR sensor as binary_sensor in Home Assistant](https://i.imgur.com/4S5ctF9.gif)


## Todo list:
- Get device info, such as battery state and last seen.
- Support for other devices such as smoke detectors, sirenes and (physical) control panel
- Support other platforms to show history and photo gallery, probably only available on JABLOTRON Web Self-service (jablonet.net)
- [DONE!] Retain discovered sensors in a configuration file and read this file as soon as HA starts.

## Credits
Big thanks to [mattsaxon](https://community.home-assistant.io/u/mattsaxon) and [Marcel1](https://community.home-assistant.io/u/marcel1)!

Work in progress. Any help would be great!

