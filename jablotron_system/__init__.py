"""Jablotron System Component"""
import logging
from homeassistant.helpers.discovery import load_platform
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import (CONF_PORT, CONF_CODE, CONF_NAME)
from homeassistant.components import mqtt

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'jablotron_system'
DEFAULT_PORT = '/dev/hidraw0'
DEFAULT_NAME = 'Jablotron Alarm'

CONF_CODE_ARM_REQUIRED = 'code_arm_required'
CONF_CODE_DISARM_REQUIRED = 'code_disarm_required'
CONF_STATE_TOPIC = 'state_topic'
CONF_COMMAND_TOPIC = 'command_topic'
DEFAULT_STATE_TOPIC = 'home-assistant/mqtt_example/state'
DEFAULT_COMMAND_TOPIC = 'home-assistant/mqtt_example/set'

# code required, since binary_sensor is using code to get 55 packets send
CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.string,
        vol.Required(CONF_CODE): cv.string,
        vol.Optional(CONF_CODE_ARM_REQUIRED, default=False): cv.boolean,
        vol.Optional(CONF_CODE_DISARM_REQUIRED, default=True): cv.boolean,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_STATE_TOPIC, default=DEFAULT_STATE_TOPIC): mqtt.valid_subscribe_topic,
        vol.Optional(CONF_COMMAND_TOPIC, default=DEFAULT_COMMAND_TOPIC): mqtt.valid_subscribe_topic
    })
}, extra=vol.ALLOW_EXTRA)

def setup(hass, config):
    """Your controller/hub specific code."""

    hass.data[DOMAIN] = config[DOMAIN]

    load_platform(hass, 'binary_sensor', DOMAIN, {}, config)
    load_platform(hass, 'alarm_control_panel', DOMAIN, {}, config)
    return True