"""Jablotron Sensor platform"""
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

        # default binary strings for comparing states in d8 packets
        self._old_bin_string = '0'.zfill(32)
        self._new_bin_string = '0'.zfill(32)

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

            _LOGGER.info('Activating 55 packets')
            activationpacket = b'\x80\x08\x03\x39\x39\x39' + packet_code
            
            _LOGGER.info('Send activation packet 80 08 03 39 39 39 <code>')
            _LOGGER.info('Send packet 52 02 13 05 9A')
            self._sendPacket(activationpacket) # packet with code to activate 55 packets
            self._sendPacket(b'\x52\x02\x13\x05\x9A')                     # activating 55 packets

            hass.bus.async_listen('homeassistant_stop', self.shutdown_threads)

            from concurrent.futures import ThreadPoolExecutor
            self._io_pool_exc = ThreadPoolExecutor(max_workers=5)
            self._read_loop_future = self._io_pool_exc.submit(self._read_loop)
            self._watcher_loop_80_future = self._io_pool_exc.submit(self._watcher_loop_80)
            self._watcher_loop_52_future = self._io_pool_exc.submit(self._watcher_loop_52)
            self._io_pool_exc.submit(self._startup_message_80)
            self._io_pool_exc.submit(self._startup_message_52)

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

    def _watcher_loop_80(self):
        while not self._stop.is_set():
            if not self._data_flowing.wait(0.5):
                self._startup_message_80()
            else:
                time.sleep(1)

    def _watcher_loop_52(self):
        while not self._stop.is_set():
            if not self._data_flowing.wait(0.5):
                self._startup_message_52()
            else:
                time.sleep(30)

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
                time.sleep(0.5)

        except Exception as ex:
            _LOGGER.error('Unexpected error 2: %s', format(ex) )

        finally:
            _LOGGER.info('exiting read_loop()' )

    def _hextobin(self, hexstring):
        dec = int.from_bytes(hexstring, byteorder=sys.byteorder) # turn to 'little' if sys.byteorder is wrong
        bin_dec = bin(dec)
        binstring = bin_dec[2:]
        binstring = binstring.zfill(32)
        revstring = binstring [::-1]
        return revstring

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

#                if packet[:1] == b'\x52': # sensor?
#                    _LOGGER.info("Unknown packet 52 %s", str(binascii.hexlify(packet[0:6]), 'utf-8'))



#                elif packet[:2] == b'\x55\x09' or (packet[:2] == b'\xd8\x08' and packet[10:12] == b'\x55\x09'):
                if packet[:2] == b'\x55\x09':
#                elif 'a' == 'b':
                    # sensor data

                    # offset is different when packet starts with d8 08
                    # read 4 more bytes than needed for R&D
                    if packet[:2] == b'\x55\x09':
                        sensordata = packet[0:10]
                    else:
                        sensordata = packet[10:20]

                    # get info
                    _msgtype = sensordata[2:3]  # 3rd byte
                    _state   = sensordata[3:4]  # only 4th byte
                    _device  = sensordata[4:6]  # 5th and 6th byte
                    _rest    = sensordata[6:10] # 7,8,9 and 10th byte


                    if _msgtype in (b'\x00', b'\x01'):
                        if _state in (b'\x6d', b'\x75', b'\x79', b'\x7d', b'\x88', b'\x80'):
                            _device_state = STATE_ON
                        else:
                            _device_state = STATE_OFF
                    elif _msgtype == b'\x4f':
                        _LOGGER.info("Unrecognized 55 09 4f packet: %s %s %s - %s", str(binascii.hexlify(_msgtype), 'utf-8'), str(binascii.hexlify(_state), 'utf-8'), str(binascii.hexlify(_device), 'utf-8'), str(binascii.hexlify(_rest), 'utf-8'))
                    else:
                        _LOGGER.info("New unknown 55 09 packet: %s %s %s - %s", str(binascii.hexlify(_msgtype), 'utf-8'), str(binascii.hexlify(_state), 'utf-8'), str(binascii.hexlify(_device), 'utf-8'), str(binascii.hexlify(_rest), 'utf-8'))
                    

# Begin - This is all for debugging purposes, please ignore
                    # not sure what the 3rd byte is yet. 00=status, 01=
                    if _msgtype == b'\x00':
                        msgtype = 'magnetic or PIR'            # seen with both wireless magnetic and PIR sensors
                    elif _msgtype == b'\x01':
                        msgtype = 'PIR with photo'             # only seen when activating wireless PIR with capture photo ability
                    elif _msgtype in (b'\x0c', b'\x2e'):
                        msgtype = 'Control panel'              # only seen when using wireless control panel
                    elif _msgtype in b'\x4f':
                        msgtype = 'unknown but recognized'     # we've seen this one before with several wireless magnetic sensors, but no idea
                    else:
                        msgtype = 'unknown and unrecognized'   # never seen this before

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

                    _LOGGER.debug("Sensor changed: 55 09 packet info: %s %s %s - %s", str(binascii.hexlify(_msgtype), 'utf-8'), str(binascii.hexlify(_state), 'utf-8'), str(binascii.hexlify(_device), 'utf-8'), str(binascii.hexlify(_rest), 'utf-8'))
                    _LOGGER.debug("Sensor changed: resolves to: msgtype: %s, state: %s, device: %s", msgtype, _device_state, device)
#                    self._write_config_file(str(binascii.hexlify(packet), 'utf-8'))
# End - This is all for debugging purposes, please ignore

                    # Now we've found the right packet, let's make a sensor of it.

                    # ENTITY_ID: convert _device to bytes as string. for example: b'\x40\x01' to 40_01
                    s = str(binascii.hexlify(_device), 'utf-8')
                    n = 2
                    x = ''
                    for i in range(0, len(s), n):
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
                            _LOGGER.debug("Entity_id %s exists, now updating", entity_id)
                            break
                    else:
                        # create new entity if sensor doesn't exist
                        _LOGGER.debug("Entity_id %s doesn't exist, now creating", entity_id)
                        binarysensor = JablotronSensor(self._hass, self._config, sensor_id)
                        DEVICES.append(binarysensor)
                        self._async_add_entities([binarysensor])

                    # Set new state
                    binarysensor._state = _device_state
                    _LOGGER.info('State %s updated to: %s', entity_id, _device_state)
                    
                    # update sensor state
                    asyncio.run_coroutine_threadsafe(binarysensor._update(), self._hass.loop)                   

                    # Set PIR states to STATE_OFF after 10 sec
                    if _state in (b'\x75', b'\x79', b'\x7d'):
                        time.sleep(10)
                        binarysensor._state = STATE_OFF
#                        _LOGGER.info('_state updated: %s', _device_state)
                        _LOGGER.info('State %s updated to: %s', entity_id, binarysensor._state)

                        # update sensor state
                        asyncio.run_coroutine_threadsafe(binarysensor._update(), self._hass.loop)                   
                    pass

                elif packet[:2] == b'\xd8\x08':
#                elif packet[:2] == b'\xd8\x08' and packet[10:12] == b'\x55\x09':
#                    _LOGGER.info("Unknown #1 packet d8 08 ::: %s %s %s %s %s %s %s %s", str(binascii.hexlify(packet[0:1]), 'utf-8'), str(binascii.hexlify(packet[1:2]), 'utf-8'), str(binascii.hexlify(packet[2:3]), 'utf-8'), str(binascii.hexlify(packet[3:4]), 'utf-8'), str(binascii.hexlify(packet[4:5]), 'utf-8'), str(binascii.hexlify(packet[5:6]), 'utf-8'), str(binascii.hexlify(packet[6:7]), 'utf-8'), str(binascii.hexlify(packet[7:8]), 'utf-8'))
#                    _LOGGER.info("Unknown #1              ::: %s %s %s %s %s %s %s %s", str(binascii.hexlify(packet[8:9]), 'utf-8'), str(binascii.hexlify(packet[9:10]), 'utf-8'), str(binascii.hexlify(packet[10:11]), 'utf-8'), str(binascii.hexlify(packet[11:12]), 'utf-8'), str(binascii.hexlify(packet[12:13]), 'utf-8'), str(binascii.hexlify(packet[13:14]), 'utf-8'), str(binascii.hexlify(packet[14:15]), 'utf-8'), str(binascii.hexlify(packet[15:16]), 'utf-8'))
 
                    _LOGGER.debug("d8 08 packet byte 1-8  ::: %s %s %s %s %s %s %s %s", str(binascii.hexlify(packet[0:1]), 'utf-8'), str(binascii.hexlify(packet[1:2]), 'utf-8'), str(binascii.hexlify(packet[2:3]), 'utf-8'), str(binascii.hexlify(packet[3:4]), 'utf-8'), str(binascii.hexlify(packet[4:5]), 'utf-8'), str(binascii.hexlify(packet[5:6]), 'utf-8'), str(binascii.hexlify(packet[6:7]), 'utf-8'), str(binascii.hexlify(packet[7:8]), 'utf-8'))
                    _LOGGER.debug("             byte 9-16 ::: %s %s %s %s %s %s %s %s", str(binascii.hexlify(packet[8:9]), 'utf-8'), str(binascii.hexlify(packet[9:10]), 'utf-8'), str(binascii.hexlify(packet[10:11]), 'utf-8'), str(binascii.hexlify(packet[11:12]), 'utf-8'), str(binascii.hexlify(packet[12:13]), 'utf-8'), str(binascii.hexlify(packet[13:14]), 'utf-8'), str(binascii.hexlify(packet[14:15]), 'utf-8'), str(binascii.hexlify(packet[15:16]), 'utf-8'))

                    byte3 = packet[2:3]  # 3rd byte unknown, always 00
                    byte4 = packet[3:4]  # 4th byte, last part of id
                    byte5 = packet[4:5]  # 5th byte, first part of id

                    part = byte4+byte5

                    # make a binary string of the new hex part string
                    self._new_bin_string = self._hextobin(part)
                    _LOGGER.debug('old_bin_string: %s', self._old_bin_string)
                    _LOGGER.debug('new_bin_string: %s', self._new_bin_string)


                    # ga nu vergelijken
                    for i, (x, y) in enumerate(zip(self._old_bin_string, self._new_bin_string)):
                        if x != y:
                            _LOGGER.debug('%s changed from %s to %s', i, x, y)


                            sensor_id = 'jablotron_' + str(i)
                            entity_id = 'binary_sensor.' + sensor_id

                            # Check if sensor is already known
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

                            # Set new state
                            if y == '1':
                                binarysensor._state = STATE_ON
                            else:
                                binarysensor._state = STATE_OFF
                            _LOGGER.info('State %s updated to: %s', entity_id, binarysensor._state)

                            # update sensor state
                            asyncio.run_coroutine_threadsafe(binarysensor._update(), self._hass.loop)                   
                    
                    # save last binary string as old binary string
                    self._old_bin_string = self._new_bin_string                    

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

    def _startup_message_52(self):
        """ Send Start Message to system"""

#        try:
#            self._lock.acquire()

        self._sendPacket(b'\x52\x02\x13\x05\x9A')             # Get states of sensors
        _LOGGER.debug('Send packet 52 02 13 05 9A')

    def _startup_message_80(self):
        """ Send Start Message to system"""

#        try:
#            self._lock.acquire()
        self._sendPacket(b'\x80\x01\x02')             # Get states of sensors
        _LOGGER.debug('Send packet 80 01 02')

#        self._sendPacket(b'\x80\x01\x0f')             # Get states of sensors
#        self._sendPacket(b'\x80\x01\x04')             # Get states of sensors
#        self._sendPacket(b'\x52\x02\x13\x05\x9a')             # Get states of sensors

#        self._sendPacket(b'\x52\x01\x02')             # Get states of sensors
#        _LOGGER.info('Send packet 52 01 02')
        
#        time.sleep(0.1) # lower reliability without this delay

#        finally:
#            self._lock.release()

#    def update(self):
#        """Fetch new state data for the sensor.
#        This is the only method that should fetch new data for Home Assistant.
#        """
#        self._state = self.hass.data[DOMAIN]['temperature']
#        _LOGGER.info("file_path: %s", self._file_path)

