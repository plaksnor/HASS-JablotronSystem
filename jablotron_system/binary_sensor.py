"""Jablotron Sensor platform"""
# HA forum    : https://community.home-assistant.io/t/jablotron-ja-80-series-and-ja-100-series-alarm-integration/113315/
# Github repo : https://github.com/plaksnor/HASS-JablotronSystem
#
# The code contains 2 classes:
# - ReadPort() is scanning for packets with sensor data
# - JablotronSensor() is representing a binary_sensor object in HA
#
# The Jablotron data (for at least the JA-100 series) consists of two important type of packets which are getting send by the alarm system.
#
# The packets starting with d8 08 seem to contain some kind of status reports.
# For example:
#  1  2  3  4  5  6  7  8   9 10 11 12 13 14 15 16  <====================== byte number
# d8 08 00 00 00 00 00 00  00 00 00 10 14 55 00 10  |.............U..|    : nothing is activated
# d8 08 00 00 01 00 00 00  00 00 55 09 00 88 00 02  |..........U.....|    : one or multiple devices has been activated
#
# byte number:
#  4 and  5 = accumulated sensor ID's of devices which are ON. See hextobin() function for decoding. This data is not being used right now.
# 11 and 12 = if 55 09, a specific sensor caused this d8 packet
#        14 = status (on/off) of sensor which has changed state
# 15 and 16 = specific sensor ID of sensor which has changed state
#
# The packets starting with 55 09 also seem to contain sensor data, but they are only getting send when there has been send a d8 or 55 packet in the last 30 seconds.
# For example:
#  1  2  3  4  5  6  7  8   9 10 11 12 13 14 15 16  <====================== byte number
# 55 09 00 8a 00 02 40 cc  d2 3b 13 00 0b 00 00 00  |U.....@..;......|    : sensor 00 02 became inactive (8a)
# 55 09 00 80 80 01 60 cc  f2 3b 14 00 14 55 00 10  |U.....`..;...U..|    : sensor 80 01 became active (80)
#
# byte number:
#         4 = status (on/off) of device which has changed state
#  5 and  6 = specific sensor ID of sensor which has changed state
#
# How data will get sent:
# If some kind of activity occur after an inactivity of 30 seconds, a d8 packet will get sent first and then 55 packets.
# So it seems like a d8 packet always getting sent first and get followed by one or more 55 packets if sensors change state.
# If no sensors are active, an 'empty' d8 packet will get sent.

import logging
import binascii
import sys
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
    STATE_ON,
    STATE_OFF
)
import homeassistant.components.sensor as sensor

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import ConfigType, HomeAssistantType


_LOGGER = logging.getLogger(__name__)

DEVICES = []

async def async_setup_platform(hass: HomeAssistantType, config: ConfigType, async_add_entities, discovery_info=None):
    jablotron_conf_file = hass.config.path('{}'.format('jablotron.conf'))
    data = ReadPort(hass, config, jablotron_conf_file, async_add_entities)



class JablotronSensor(BinarySensorDevice):
    """Representation of a Sensor."""

    def __init__(self, hass, config, name):
        self._name = name
        self._state = None
#        self._sub_state = None
#        self._hass = hass
#        self._config = config

    @property
    def name(self):
        """Return the name of the sensor."""
#        return 'All jablotron sensors'
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    async def _update(self):
            self.async_schedule_update_ha_state()



class ReadPort():
    """ Read configuration and serial port and check for incoming data"""

    def __init__(self, hass, config, out_path, async_add_entities):
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

        # Variable to store last known d8 packet
        self._last_d8 = b''

        # default binary strings for comparing states in d8 packets
        self._old_bin_string = '0'.zfill(32)
        self._new_bin_string = '0'.zfill(32)
        self._activation_packet = b''

        _LOGGER.info('Serial port: %s', format(self._file_path))

        try:
          
            switcher = {
                "0": b'\x30',
                "1": b'\x31',
                "2": b'\x32',
                "3": b'\x33',
                "4": b'\x34',
                "5": b'\x35',
                "6": b'\x36',
                "7": b'\x37',
                "8": b'\x38',
                "9": b'\x39'
            }

            # generating activation packet            
            packet_code = b''
            for c in hass.data[DOMAIN]['code']:
                packet_code = packet_code + switcher.get(c)

            # generate activation packet to trigger 55 packets
            self._activation_packet = b'\x80\x08\x03\x39\x39\x39' + packet_code
            
            hass.bus.async_listen('homeassistant_stop', self.shutdown_threads)

            from concurrent.futures import ThreadPoolExecutor
            self._io_pool_exc = ThreadPoolExecutor(max_workers=5)
            self._read_loop_future = self._io_pool_exc.submit(self._read_loop)
            self._watcher_loop_keepalive_future = self._io_pool_exc.submit(self._watcher_loop_keepalive)
            self._watcher_loop_triggersensorupdate_future = self._io_pool_exc.submit(self._watcher_loop_triggersensorupdate)
#            self._io_pool_exc.submit(self._keepalive)
#            self._io_pool_exc.submit(self._triggersensorupdate)

        except Exception as ex:
            _LOGGER.error('Unexpected error 1: %s', format(ex) )


# not in use yet
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
        return 'Jablotron scanner'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def available(self):
        return self._available


#    async def _update(self):
#            self.async_schedule_update_ha_state()

    def _watcher_loop_keepalive(self):
        while not self._stop.is_set():
            if not self._data_flowing.wait(0.5):
                self._keepalive()
            else:
                time.sleep(1)

    def _watcher_loop_triggersensorupdate(self):
        while not self._stop.is_set():
            if not self._data_flowing.wait(0.5):
                self._triggersensorupdate()
            else:
                time.sleep(15)

    def _read_loop(self):
        try:
            while not self._stop.is_set():

                self._f = open(self._file_path, 'rb', 64)
                new_state = self._read()

                self._f.close()
                time.sleep(0.5)

        except Exception as ex:
            _LOGGER.error('Unexpected error 2: %s', format(ex) )

        finally:
            _LOGGER.info('exiting read_loop()' )

    # function to transform a hex string into a binary string
    def _hextobin(self, hexstring):
        dec = int.from_bytes(hexstring, byteorder=sys.byteorder) # turn to 'little' if sys.byteorder is wrong
        bin_dec = bin(dec)
        binstring = bin_dec[2:]
        binstring = binstring.zfill(32)
        revstring = binstring [::-1]
        return revstring

    def _binarysensor(self, sensor_id, entity_id):
        # Check if the sensor is already a binary_sensor
        for dev in DEVICES:
            if dev.name == sensor_id:
                binarysensor = dev
                _LOGGER.debug("Entity_id %s exists, now updating", entity_id)
                break
        else:
            # create new entity if sensor doesn't exist
            _LOGGER.debug("Entity_id %s doesn't exist, now creating", entity_id)
            binarysensor = JablotronSensor(self._hass, self._config, sensor_id)
            DEVICES.append(binarysensor)
            self._async_add_entities([binarysensor])

        return binarysensor


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
                self._state = True




                if packet[:2] == b'\xd8\x08' and packet[:5] != self._last_d8:
                    # new incoming status message with changed state

                    _LOGGER.debug('d8 08 packet, state changed')

                    byte3 = packet[2:3]  # 3rd byte unknown, always 00
                    byte4 = packet[3:4]  # 4th byte, last part of id
                    byte5 = packet[4:5]  # 5th byte, first part of id

                    # byte 4 and 5 contain device id
                    part = byte4+byte5

                    # make a binary string of the new hex part string
                    self._new_bin_string = self._hextobin(part)
                    _LOGGER.debug('old_bin_string: %s', self._old_bin_string)
                    _LOGGER.debug('new_bin_string: %s', self._new_bin_string)

                    # compare new binary string with old binary string
                    # the outcome tells which devices need to get a STATE_OFF or STATE_ON
                    for idx, (x, y) in enumerate(zip(self._old_bin_string, self._new_bin_string)):
                        # if old state is different than new state
                        if x != y:

                            sensor_id = 'jablotron_' + str(idx)
                            entity_id = 'binary_sensor.' + sensor_id

                            _LOGGER.debug('changing %s from %s to %s', sensor_id, x, y)

                            binarysensor = self._binarysensor(sensor_id, entity_id)

                            # Set new state
                            if y == '1':
                                _device_state = STATE_ON
                            else:
                                _device_state = STATE_OFF

                            # set new state if changed
                            if binarysensor._state != _device_state:
                                binarysensor._state = _device_state

                                # update sensor state
                                asyncio.run_coroutine_threadsafe(binarysensor._update(), self._hass.loop)                   
                                _LOGGER.info('State %s updated to: %s', entity_id, binarysensor._state)

                    # save last binary string as old binary string
                    _LOGGER.debug('updating bin string to %s', self._new_bin_string)
                    self._old_bin_string = self._new_bin_string                    

                    # store last d8 value to compare with new incoming d8 packets
                    self._last_d8 = packet[:5]


#                elif packet[:2] == b'\x55\x09' or (packet[:2] == b'\xd8\x08' and packet[10:12] == b'\x55\x09'):
#                if packet[:2] == b'\x55\x09':
                elif packet[:2] == b'\x55\x09':

                    _LOGGER.debug('55 09 packet, state changed')

                    packetpart = packet[0:10]

                    byte3 = packetpart[2:3]  # 3rd byte
                    byte4 = packetpart[3:4]  # 4th byte
                    byte5 = packetpart[4:5]  # 5th byte
                    byte6 = packetpart[5:6]  # 6th byte

                    if byte3 in (b'\x00', b'\x01'):
                        if byte4 in (b'\x6d', b'\x75', b'\x79', b'\x7d', b'\x88', b'\x80'):
                            _device_state = STATE_ON
                        else:
                            _device_state = STATE_OFF

                        # byte 4 and 5 contain device id
                        part = byte5+byte6

                        # Calculate sensor ID based on byte5+byte6
                        dec = int.from_bytes(part, byteorder=sys.byteorder) # turn to 'little' if sys.byteorder is wrong
                        i = int(dec/64)                    

                        sensor_id = 'jablotron_' + str(i)
                        entity_id = 'binary_sensor.' + sensor_id

                        binarysensor = self._binarysensor(sensor_id, entity_id)

                        # update both sensor state as DEVICES list
                        for idx, dev in enumerate(DEVICES):
                            if dev.name == sensor_id:
                                # read from list
                                binarysensor = dev

                                # set new state if changed
                                if binarysensor._state != _device_state:
                                    binarysensor._state = _device_state
                                    _LOGGER.info('State %s updated to: %s', entity_id, _device_state)

                                    # update sensor state
                                    asyncio.run_coroutine_threadsafe(binarysensor._update(), self._hass.loop)                   

                                # stop searching, we're done yet.
                                break

                    elif byte3 == b'\x0c':
                        # we don't know yet. Must be some keep alive packet from a sensor who hasn't been triggered in a loooong time
                        _LOGGER.info("Unrecognized 55 09 0c packet: %s %s %s %s", str(binascii.hexlify(byte3), 'utf-8'), str(binascii.hexlify(byte4), 'utf-8'), str(binascii.hexlify(byte5), 'utf-8'), str(binascii.hexlify(byte6), 'utf-8'))
                        _LOGGER.info("Probably Control Panel OFF?")

                    elif byte3 == b'\x2e':
                        # we don't know yet. Must be some keep alive packet from a sensor who hasn't been triggered in a loooong time
                        _LOGGER.info("Unrecognized 55 09 2e packet: %s %s %s %s", str(binascii.hexlify(byte3), 'utf-8'), str(binascii.hexlify(byte4), 'utf-8'), str(binascii.hexlify(byte5), 'utf-8'), str(binascii.hexlify(byte6), 'utf-8'))
                        _LOGGER.info("Probably Control Panel ON?")

                    elif byte3 == b'\x4f':
                        # we don't know yet. Must be some keep alive packet from a sensor who hasn't been triggered in a loooong time
                        _LOGGER.info("Unrecognized 55 09 4f packet: %s %s %s %s", str(binascii.hexlify(byte3), 'utf-8'), str(binascii.hexlify(byte4), 'utf-8'), str(binascii.hexlify(byte5), 'utf-8'), str(binascii.hexlify(byte6), 'utf-8'))
                        _LOGGER.info("Probably some keep alive packet from a sensor which hasn't been triggered recently")

                    else:
                        _LOGGER.info("New unknown 55 09 packet: %s %s %s %s", str(binascii.hexlify(byte3), 'utf-8'), str(binascii.hexlify(byte4), 'utf-8'), str(binascii.hexlify(byte5), 'utf-8'), str(binascii.hexlify(byte6), 'utf-8'))

                else:
                    pass
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

    def _triggersensorupdate(self):
        """ Send trigger for sensor update to system"""

        _LOGGER.debug('Send activation packet: %s', self._activation_packet)
        _LOGGER.debug('Send packet: 52 02 13 05 9a')

        self._sendPacket(self._activation_packet)
        self._sendPacket(b'\x52\x02\x13\x05\x9a')

    def _keepalive(self):
        """ Send keepalive to system"""

        _LOGGER.debug('Send packet 52 01 02')
        self._sendPacket(b'\x52\x01\x02')
        