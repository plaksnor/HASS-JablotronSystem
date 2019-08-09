# HASS-JablotronSystem
Jablotron component for Home Assistant



Home Assistant component to arm and disarm the alarm system and read sensor states.

Currently supports:
- alarm control panel, to arm and disarm the Jablotron alarm system
- binary sensor, to separately monitor Jablotron sensors

## Installation
To use this component, copy all scripts to "<home assistant config dir>/custom_components/jablotron_system".
Edit configuration.yaml and add the following lines:

```
jablotron_system:
  port: /dev/hidraw0
  code: 1234
```
Both options 'port' and 'code' are required.
Optional arguments are:
```
  code_arm_required: True
  code_disarm_required: True
  state_topic: "backend/alarm_control_panel/jablotron/state"
  command_topic: "backend/alarm_control_panel/jablotron/set"
```

Note: Because my serial cable presents as a HID device there format is /dev/hidraw[x], others that present as serial may be at /dev/ttyUSB0 or similar. Use the following command line to identify the appropriate device:

```
$ dmesg | grep usb
$ dmesg | grep hid
```

## How it works
- Available platforms (alarm control panel and binary sensors) will be shown on the http(s)://domainname<:8123>/states page.
- The alarm control panel is always available.
- Sensors will automatically be added as soon as they are triggered.
- Discovered (triggered) sensors will be stored in config/jablotron_devices.yaml and get loaded after restart of HA.
- In the 'Settings' -> 'Customization' section of HA you'll be able to customize each sensor:
  - friendly_name : give it a human readable name
  - device_class  : give it a class which matches the device

## Enable MQTT support
**Alarm_control_panel**

If the mqtt: component has been properly configured on the local host (directly connected to the Jablotron system), the alarm_control_panel will publish states and listen for changed alarm states automatically. You could specify which topics should be used.
- The `state_topic` will be used for announcing new states (MQTT messages will be retained)
- The `command_topic` will be used for receiving incoming states from a remote alarm_control_panel.

On both hosts (local and remote) you need to setup an MQTT broker first of course.
- On the local host you need specify topics. For example:
```
jablotron_system:
  port: /dev/hidraw0
  code_arm_required: True
  code_disarm_required: True
  code: !secret jablotron_code
  state_topic: "backend/alarm_control_panel/jablotron/state"
  command_topic: "backend/alarm_control_panel/jablotron/set"
```

- On the remote host you need to setup a [MQTT alarm control panel](https://www.home-assistant.io/components/alarm_control_panel.mqtt/). For example:
```
alarm_control_panel:
  - platform: mqtt
    name: 'Jablotron Alarm'
    state_topic: "backend/alarm_control_panel/jablotron/state"
    command_topic: "backend/alarm_control_panel/jablotron/set"
    code_arm_required: True
    code_disarm_required: True
    code: !secret jablotron_code
```

**Binary_sensor**

In order to publish the states of binary sensors, you could make an automation on the local host like this:
```
automation:
  # if state changes then also update mqtt state
  - alias: 'send to MQTT state'
    initial_state: 'true'
    trigger:
      - platform: state
        entity_id:
          - binary_sensor.jablotron_3
          - binary_sensor.jablotron_4
          - binary_sensor.jablotron_5
    action:
      - service: mqtt.publish
        data_template:
          topic: >
            backend/{{ trigger.entity_id.split('.')[0] }}/{{ trigger.entity_id.split('.')[1] }}/state
          payload: >
            {{ trigger.to_state.state | upper }}
          retain: true
```
On the remote host you need to make MQTT based binary sensors like this:
```
binary_sensor:
  - platform: mqtt
    name: "jablotron_3"
    state_topic: "backend/binary_sensor/jablotron_3/state"
    payload_on: "ON"
    payload_off: "OFF"
    qos: 0
```

## Tested with
- Home Assistant 0.94.0b3, 0.97.0, installed in docker at RPi 3 model B+ and RPi 4
- Jablotron JA-101K-LAN, firmware: LJ60422, hardware: LJ16123
- Jablotron magnetic and PIR (motion) sensors

## Demo

First you start triggering several sensors. They'll add up as soon as they are triggered:
![Jablotron sensors detected](https://i.imgur.com/H8oSrii.gif)

Each sensor gets it own entity_id with a unique number. This number represents the ID or position in J/F/O-link, the Jablotron software to configure your alarm system. If you're not able to open up J/F/O-link but you are able to access your alarm system over the internet, you could use the Jablotron app on your phone and go to Devices to get a list of devices. The order there is the same as the numbers of the entity_id's here.

Discovered sensors are automatically stored in your config/jablotron_devices.yaml file. You could trigger all sensors, but you could also manually change this file and restart HA in order to see them all.

After all sensors have been added, you could give them more friendly names in the Customization section:
![Customize Jablotron sensor in Home Assistant](https://i.imgur.com/DhDgQoB.gif)

At the end, you should be able to see all kind of sensors like here:
![Jablotron sensors customized in Home Assistant](https://i.imgur.com/07gn2QP.gif)

Here you'll see a Jablotron PIR sensor working as a binary_sensor, detecting motion:
![Jablotron PIR sensor as binary_sensor in Home Assistant](https://i.imgur.com/4S5ctF9.gif)

# MQTT demo

Opened up 2 browsers. Left = local host, right = remote host based on MQTT:
![Jablotron alarm control panel with MQTT support](https://i.imgur.com/3bRz6uj.gif)

As you may have noticed, the MQTT alarm control panel doesn't support an 'arming' state, so I used a 'pending' state.

MQTT support for binary sensors was already supported in HA by using automations.
Opened up 2 browsers. Up = local host, down = remote host based on MQTT:
![Jablotron binary sensors with MQTT supoprt](https://i.imgur.com/OsWlwvV.gif)

## Todo list:
- Get device info, such as battery state and last seen.
- Support for other devices such as smoke detectors, sirenes and (physical) control panel
- Support other platforms to show arm/disarm history and photo gallery, probably only available on JABLOTRON Web Self-service (jablonet.net)
- [DONE!] Retain discovered sensors in a configuration file and read this file as soon as HA starts.
- [DONE!] Added MQTT support

## Credits
Big thanks to [mattsaxon](https://community.home-assistant.io/u/mattsaxon) and [Marcel1](https://community.home-assistant.io/u/marcel1)!

Work in progress. Any help would be great!

