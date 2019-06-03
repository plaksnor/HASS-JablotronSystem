"""Jablotron System Component"""
import logging
from homeassistant.helpers.discovery import load_platform
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import (CONF_PORT, CONF_CODE, CONF_NAME)
    
_LOGGER = logging.getLogger(__name__)

DOMAIN = 'jablotron_system'

DEFAULT_PORT = '/dev/hidraw'
DEFAULT_NAME = 'Jablotron Alarm'

CONF_CODE_ARM_REQUIRED = 'code_arm_required'
CONF_CODE_DISARM_REQUIRED = 'code_disarm_required'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.string,
        vol.Optional(CONF_CODE): cv.string,
        vol.Optional(CONF_CODE_ARM_REQUIRED, default=False): cv.boolean,
        vol.Optional(CONF_CODE_DISARM_REQUIRED, default=True): cv.boolean,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string
    })
}, extra=vol.ALLOW_EXTRA)

def setup(hass, config):
    """Your controller/hub specific code."""

    hass.data[DOMAIN] = config[DOMAIN]

    load_platform(hass, 'binary_sensor', DOMAIN, {}, config)
    load_platform(hass, 'alarm_control_panel', DOMAIN, {}, config)
    return True