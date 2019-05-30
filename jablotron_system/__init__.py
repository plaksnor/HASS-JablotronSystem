"""Jablotron System Component"""
import logging
from homeassistant.helpers.discovery import load_platform
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import CONF_PORT
    
_LOGGER = logging.getLogger(__name__)

DOMAIN = 'jablotron_system'
DEFAULT_PORT = '/dev/hidraw0'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.string
    })
}, extra=vol.ALLOW_EXTRA)

def setup(hass, config):
    """Your controller/hub specific code."""

    poort = config[DOMAIN][CONF_PORT]
    hass.data[DOMAIN] = config[DOMAIN][CONF_PORT]
    _LOGGER.info('Serial port: %s', format(poort))


    load_platform(hass, 'binary_sensor', DOMAIN, {}, config)
#    load_platform('alarm_control_panel', DOMAIN, {}, config)
    return True