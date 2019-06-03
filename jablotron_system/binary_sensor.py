"""Jablotron Sensor platform"""
import logging
import binascii
import re
import time
import asyncio
import threading

from . import DOMAIN

from homeassistant.helpers.entity import Entity
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

#from homeassistant.helpers.event import track_point_in_time
#from homeassistant.util import dt as dt_util
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import ConfigType, HomeAssistantType


_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'Jablotron Alarm sensor'
DEVICES = []

async def async_setup_platform(hass: HomeAssistantType, config: ConfigType, async_add_entities, discovery_info=None):
    jablotron_conf_file = hass.config.path('{}'.format('jablotron.conf'))
    data = ReadPort(hass, config, jablotron_conf_file, async_add_entities)





class JablotronSensor(BinarySensorDevice):
    """Representation of a Sensor."""

    def __init__(self, hass, config, name):

        """Init the Sensor."""
        self._name = name
        self._state = None
        self._sub_state = None
        self._hass = hass
        self._config = config

        self._lock = threading.BoundedSemaphore()
        self._stop = threading.Event()
        self._data_flowing = threading.Event()
        

        try:
            hass.bus.async_listen('homeassistant_stop', self.shutdown_threads)

            from concurrent.futures import ThreadPoolExecutor
            self._io_pool_exc = ThreadPoolExecutor(max_workers=5)
#            self._read_loop_future = self._io_pool_exc.submit(self._read_loop)

        except Exception as ex:
            _LOGGER.error('Unexpected error 4: %s', format(ex) )

    def shutdown_threads(self, event):
        _LOGGER.info('handle_shutdown() called' )
        self._stop.set()
        _LOGGER.info('exiting handle_shutdown()' )



    @property
    def name(self):
        """Return the name of the sensor."""
#        return 'All jablotron sensors'
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state


    async def _update_loop(self):
        while True:
            await self._update_required.wait()
            self.async_schedule_update_ha_state()
            self._update_required.clear()

    async def _update(self):
            self.async_schedule_update_ha_state()

    def _read_loop(self):
        try:
            while not self._stop.is_set():

                new_state = self._read()

                if new_state != self._state:
                    _LOGGER.info("Jablotron state change: %s to %s", self._state, new_state )
                    self._state = new_state
                    asyncio.run_coroutine_threadsafe(self._update(), self._hass.loop)

                time.sleep(5)

        except Exception as ex:
            _LOGGER.error('Unexpected error 4: %s', format(ex) )

        finally:
            _LOGGER.info('exiting read_loop()' )

    def _read(self):

        _LOGGER.warn("Do something")
        state = STATE_ON
       
        pass
        return state














class ReadPort():
    """ Read configuration and serial port """

    def __init__(self, hass, config, out_path, async_add_entities):

        """Init the port reader."""
        self._state = None
        self._sub_state = None
        self._file_path = hass.data[DOMAIN]['port']
        self._config_path = out_path
        self._available = False
        self._f = None
        self._hass = hass
        self._config = config
        self._model = 'Unknown'
        self._lock = threading.BoundedSemaphore()
        self._stop = threading.Event()
        self._data_flowing = threading.Event()
        self._async_add_entities = async_add_entities
        

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


    def _write_config_file(self, msg):
        _LOGGER.info("%s: Writing jablotron config to file: %s", self.name, self._config_path)

        try:
            with open(self._config_path, 'w+', encoding='utf-8') as file_out:
                file_out.write(msg)
#                json.dump(self._client.json_config, file_out, sort_keys=True, indent=4)
#                file_out.close()
        except IOError as exc:
            _LOGGER.error("%s: Unable to write Jablotron configuration to %s: %s", self.name, self._config_path, exc)

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

    @property
    def available(self):
        return self._available

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


                    # let's try to work only with STATE_ON, so the HA user should use device_class in order to decide if it's ON, OPENED or MOVING.
                    if _state in (b'\x6d', b'\x75', b'\x79', b'\x7d', b'\x88', b'\x80'):
                        _device_state = STATE_ON
                    elif _state == b'\xa4':
                        # some keepalive packet of a sensor which hasn't been on or off
                        _device_state = STATE_OFF
                    else:
                        _device_state = STATE_OFF

# Begin - This is all for debugging purposes, please ignore
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
                    _LOGGER.info("Sensor changed: resolves to: devtyp: %s, state: %s, device: %s", devtyp, _device_state, device)
#                    self._write_config_file(str(binascii.hexlify(packet), 'utf-8'))
# End - This is all for debugging purposes, please ignore

                    # Now we've found the right packet, let's make a sensor of it.

                    # ENTITY_ID: convert _device to bytes as string. for example: b'\x40\x01' to 40_01
                    s = str(binascii.hexlify(_device), 'utf-8')
                    n = 2
                    x = ''
                    for i in range(0, len(s), n):
# Sensors                       
#                        x = x + s[i:i+n] + ' '
                        x = x + s[i:i+n]
#                    dev_packet = x.strip().replace(' ', '_')
                    dev_packet = x.strip()

                    sensor_id = 'jablotron_' + dev_packet
                    entity_id = 'binary_sensor.' + sensor_id

                    # Check if sensor is already known
                    for dev in DEVICES:
                        if dev.name == sensor_id:
                            binarysensor = dev
                            _LOGGER.info("Entity_id %s exists, now updating", entity_id)
                            break
                    else:
                        # create new entity if sensor doesn't exist
                        _LOGGER.info("Entity_id %s doesn't exist, now creating", entity_id)
                        binarysensor = JablotronSensor(self._hass, self._config, sensor_id)
                        DEVICES.append(binarysensor)
                        self._async_add_entities([binarysensor])

                    # Set new state
                    binarysensor._state = _device_state
                    _LOGGER.info('State updated to: %s', _device_state)
                    asyncio.run_coroutine_threadsafe(binarysensor._update(), self._hass.loop)                   

                    # Set PIR states to STATE_OFF after 10 sec
                    if _state in (b'\x75', b'\x79', b'\x7d'):
                        time.sleep(10)
                        binarysensor._state = STATE_OFF
#                        _LOGGER.info('_state updated: %s', _device_state)
                        _LOGGER.info('State updated to: %s', binarysensor._state)
                        
                        asyncio.run_coroutine_threadsafe(binarysensor._update(), self._hass.loop)                   
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

