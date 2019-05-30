"""Jablotron Sensor platform"""
from homeassistant.helpers.entity import Entity

from . import DOMAIN

import logging
import binascii
import re
import time
#import voluptuous as vol
import asyncio
import threading

from homeassistant.components.binary_sensor import (
    PLATFORM_SCHEMA,
    BinarySensorDevice,
)
from homeassistant.const import (
#    STATE_OPEN,
#    STATE_CLOSED,
    STATE_ON,
    STATE_OFF,
    STATE_UNKNOWN
)
import homeassistant.components.sensor as sensor

from homeassistant.helpers.event import track_point_in_time
from homeassistant.util import dt as dt_util

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'Jablotron Alarm sensor'

async def async_setup_platform(hass: HomeAssistantType, config: ConfigType, async_add_entities, discovery_info=None):
    async_add_entities([JablotronSensor(hass, config)])

class JablotronSensor(BinarySensorDevice):
    """Representation of a Sensor."""

    def __init__(self, hass, config):

        """Init the Sensor."""
        self._state = None
        self._sub_state = None
        self._file_path = hass.data[DOMAIN]
        self._available = False
        self._f = None
        self._hass = hass
        self._config = config
        self._model = 'Unknown'
        self._lock = threading.BoundedSemaphore()
        self._stop = threading.Event()
        self._data_flowing = threading.Event()

        _LOGGER.info('Serial port: %s', format(self._file_path))


        try:
            hass.bus.async_listen('homeassistant_stop', self.shutdown_threads)

            from concurrent.futures import ThreadPoolExecutor
            self._io_pool_exc = ThreadPoolExecutor(max_workers=5)
            self._read_loop_future = self._io_pool_exc.submit(self._read_loop)
            self._watcher_loop_future = self._io_pool_exc.submit(self._watcher_loop)
            self._io_pool_exc.submit(self._startup_message)

        except Exception as ex:
            _LOGGER.error('Unexpected error 1: %s', format(ex) )

    def shutdown_threads(self, event):
        _LOGGER.info('handle_shutdown() called' )
        self._stop.set()
        _LOGGER.info('exiting handle_shutdown()' )

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'All jablotron sensors'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

#    @property
#    def icon(self):
#        """Icon to use in the frontend, if any."""
#        return 'mdi:certificate'

    @property
    def available(self):
        return self._available

#    @property
#    def unit_of_measurement(self):
#        """Return the unit of measurement."""
#        return TEMP_CELSIUS

    async def _update_loop(self):
        while True:
            await self._update_required.wait()
            self.async_schedule_update_ha_state()
            self._update_required.clear()

    async def _update(self):
            self.async_schedule_update_ha_state()

    def _watcher_loop(self):
        while not self._stop.is_set():
            if not self._data_flowing.wait(1):
                self._startup_message()
            else:
                time.sleep(0.5)

    def _read_loop(self):
        try:
            while not self._stop.is_set():
#                self._lock.acquire()

                self._f = open(self._file_path, 'rb', 64)
                new_state = self._read()

                if new_state != self._state:
                    _LOGGER.info("Jablotron state change: %s to %s", self._state, new_state )
                    self._state = new_state
                    asyncio.run_coroutine_threadsafe(self._update(), self._hass.loop)

                self._f.close()
#                self._lock.release()
                time.sleep(1)

        except Exception as ex:
            _LOGGER.error('Unexpected error 2: %s', format(ex) )

        finally:
            _LOGGER.info('exiting read_loop()' )

    def _read(self):
        try:
            while True:

                self._data_flowing.clear()
                packet = self._f.read(64)
                self._data_flowing.set()

                if not packet:
                    _LOGGER.warn("No packets")
                    self._available = False
                    return 'No Signal'

                self._available = True

                if packet[:1] == b'\x52': # sensor?
                    _LOGGER.info("Unknown packet 52 %s", str(binascii.hexlify(packet[0:6]), 'utf-8'))

                elif packet[:2] == b'\x55\x08': # sensor?
                    _LOGGER.info("Unknown packet 55 08 %s", str(binascii.hexlify(packet[0:6]), 'utf-8'))
 
                elif packet[:2] == b'\x55\x09' or (packet[:2] == b'\xd8\x08' and packet[10:12] == b'\x55\x09'):

                    # offset is different when packet starts with d8 08
                    if packet[:2] == b'\x55\x09':
                        sensordata = packet[0:6]
                    else:
                        sensordata = packet[10:16]

                    # get info
                    _devtyp = sensordata[2:3] # only 3rd byte
                    _state  = sensordata[3:4] # only 4th byte
                    _device = sensordata[4:6] # 5th and 6th byte

                    # not sure what the 3rd byte is yet, let's try this
                    if _devtyp == b'\x00':
                        devtyp = 'magnetic or PIR'            # seen with both wireless magnetic and PIR sensors
                    elif _devtyp == b'\x01':
                        devtyp = 'PIR with photo'             # only seen when activating wireless PIR with capture photo ability
                    elif _devtyp in (b'\x0c', b'\x2e'):
                        devtyp = 'Control panel'              # only seen when using wireless control panel
                    elif _devtyp in b'\x4f':
                        devtyp = 'unknown but recognized'     # we've seen this one before with several wireless magnetic sensors, but no idea
                    else:
                        devtyp = 'unknown and unrecognized'   # never seen this before

                    # most probably user specific
                    # achterdeur              voordeur          raam
#                    if _state == b'\x88' or _state == b'\x80' or _state == b'\xa4':
#                        self._state = STATE_OPEN
#                    elif _state == b'\x8a' or _state == b'\x82' or _state == b'\xa6':
#                        self._state = STATE_CLOSED
#                    elif _state == b'\x75' or _state == b'\x79' or _state == b'\x7d':
                        # PIR's do not seem to get an OFF state
#                        self._state = STATE_ON
#                    else:
#                        state = 'unknown'
#                        self._state = STATE_UNKNOWN

                    # let's try to work only with STATE_ON, so the HA user should use device_class in order to decide if it's ON, OPENED or MOVING.
                    if _state in (b'\x6d', b'\x75', b'\x79', b'\x7d', b'\x88', b'\x80', b'\xa4'):
                        self._state = STATE_ON
                    else:
                        self._state = STATE_OFF

                    # Currently not doing anything with this info, only for debugging purposes
                    if _device == b'\x00\x02':
                        device = 'backdoor'
                    elif _device == b'\x80\x01':
                        device = 'frontdoor'
                    elif _device == b'\x40\x01':
                        device = 'studio'
                    elif _device == b'\xc0\x00':
                        device = 'hall'
                    elif _device == b'\x00\x01':
                        device = 'garage'
                    elif _device == b'\xc0\x03':
                        device = 'window kitchen'
                    elif _device == b'\x82\x00':
                        device = 'control panel'
                    else:
                        device = 'unknown'

                    _LOGGER.info("Sensor changed: 55 09 packet info: %s %s %s", str(binascii.hexlify(_devtyp), 'utf-8'), str(binascii.hexlify(_state), 'utf-8'), str(binascii.hexlify(_device), 'utf-8'))
                    _LOGGER.info("Sensor changed: resolves to: devtyp: %s, state: %s, device: %s", devtyp, self._state, device)
                    
                    # Ok, now we have tried to recognize some patterns, let's setup an entity_id for HA.

                    # ENTITY_ID: convert _device to bytes as string. for example: b'\x40\x01' to 40_01
                    s = str(binascii.hexlify(_device), 'utf-8')
                    n = 2
                    x = ''
                    for i in range(0, len(s), n):
                        x = x + s[i:i+n] + ' '
                    dev_packet = x.strip().replace(' ', '_')

                    entity_id = 'binary_sensor.jablotron_' + dev_packet

                    # Currently not using this, but if we're passing a new state to HA, we should retain attributes. Todo.
#                    d_entity_id = self._hass.data[DOMAIN].get(entity_id)
#                    _LOGGER.info('No entity_id provided: %s', d_entity_id)
#                    if not d_entity_id:
#                        _LOGGER.info('No entity_id provided')

#                    d_state = self._hass.data[DOMAIN].get('state')
#                    _LOGGER.info('d_state: %s', d_state)
#                    if not d_state:
#                        _LOGGER.info('No state provided')

#                    d_old_state = self._hass.states.get(entity_id)
#                    if d_old_state:
#                        attrs = d_old_state.attributes
#                    else:
#                        attrs = None
#                    _LOGGER.info('Attributes: %s', attrs)

#                    self._hass.states.set(entity_id, d_state, attrs)


                    # For now, just create a binary sensor without attributes
                    self._hass.states.set(entity_id, self._state, None)

                    # Usually, you have multiple sensors which run this JablotronSensor class. Every object has it's own name and state.
                    # In that case, you should update a new state to HA with the line below.
                    # However, since we experiment with 'states.set' in the line above, the line below is not relevant yet.
                    self.schedule_update_ha_state()

                    # If a state is ON (for example with a PIR motion sensor), manually set it off after 1 sec
                    # The bytes below are recognized as PIR devices.
                    if _state in (b'\x75', b'\x79', b'\x7d'):
                        time.sleep(1)
                        self._state = STATE_OFF
                        
                        # Refresh state off in HA
#                        self._hass.states.set(entity_id, d_state, attrs)
                        self._hass.states.set(entity_id, self._state, None)
                        self.schedule_update_ha_state()
                    pass

#                else:
#                    _LOGGER.info("Unknown packet: %s", packet)
#                    self._stop.set()


        except (IndexError, FileNotFoundError, IsADirectoryError, UnboundLocalError, OSError):
            _LOGGER.warning("File or data not present at the moment: %s", self._file_path)
            return 'Failed'

        except Exception as ex:
            _LOGGER.error('Unexpected error 3: %s', format(ex) )
            return 'Failed'

        return state

    def _sendPacket(self, packet):
        f = open(self._file_path, 'wb')
        f.write(packet)
        time.sleep(0.1) # lower reliability without this delay
        f.close()

    def _startup_message(self):
        """ Send Start Message to system"""

#        try:
#            self._lock.acquire()
        self._sendPacket(b'\x80\x01\x02')             # Get states of sensors

#        finally:
#            self._lock.release()

#    def update(self):
#        """Fetch new state data for the sensor.
#        This is the only method that should fetch new data for Home Assistant.
#        """
#        self._state = self.hass.data[DOMAIN]['temperature']
#        _LOGGER.info("file_path: %s", self._file_path)

