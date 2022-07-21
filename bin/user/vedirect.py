#!/usr/bin/python
# Copyright 2018-2022 Matthew Wall
# Distributed under the terms of the GNU Public License (GPLv3)
#
# Driver for Victron devices that communicate using VEDirect, including
# MPPT and BMV.
#
# tested with:
#  Victron MPPT 100 I 30 SmartSolar charge controller (vedirect-to-usb)
#
# based on vedirect.py by Janne Kario
#   https://github.com/karioja/vedirect
# uses extensions to vedirect.py by victronPi
#   http://majora.myqnapcloud.com:10080/root/victronPi/blob/master/vedirect.py

DRIVER_NAME = "VEDirect"
DRIVER_VERSION = "0.2"
DEFAULT_PORT = '/dev/ttyUSB0'

import os
import serial
import syslog
import time

import weewx.drivers
import weewx.engine
import weewx.units

try:
    # New-style weewx logging
    import weeutil.logger
    import logging
    log = logging.getLogger(__name__)
    def logdbg(msg):
        log.debug(msg)
    def loginf(msg):
        log.info(msg)
    def logerr(msg):
        log.error(msg)
except ImportError:
    # Old-style weewx logging
    import syslog
    def logmsg(level, msg):
        syslog.syslog(level, 'vedirect: %s: %s' % msg)
    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)
    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)
    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)


def loader(config_dict, engine):
    return VEDirectDriver(**config_dict[DRIVER_NAME])

def confeditor_loader():
    return VEDirectConfigurationEditor()


# schema specifically for victron devices
schema = [
    ('dateTime',  'INTEGER NOT NULL UNIQUE PRIMARY KEY'),
    ('usUnits',   'INTEGER NOT NULL'),
    ('interval',  'INTEGER NOT NULL'),
    ('LOAD',      'REAL'), # LOAD: OFF (0) or ON (1)
    ('ERR',     'REAL'), # ERR: 0 or 1
    ('VPV',  'REAL'), # VPV (mV) module voltage
    ('PPV',    'REAL'), # PPV (W) module power
    ('I',         'REAL'), # I (mA) current
    ('IL',    'REAL'), # IL (mA) load current?
    ('V', 'REAL'), # V (mV) battery voltage
    ('CS',   'REAL'), # CS: 0=off, 2=fault, 3=bulk, 4=abs, 5=float
    ('T',         'REAL'), # T (degree_C)
    ('P',         'REAL'), # P (W)
    ('CE',        'REAL'), # CE (mAh)
    ('SOC',       'REAL'), # SOC (%)
    ('TTG',       'REAL'), # TTG (minute)
    ('alarm',     'REAL'), # Alarm
    ('relay',     'REAL'), # Relay
    ('AR',        'REAL'), # AR
    ('H1',        'REAL'), # H1 (mAh)
    ('H2',        'REAL'), # H2 (mAh)
    ('H3',        'REAL'), # H3 (mAh)
    ('H4',        'REAL'), # H4
    ('H5',        'REAL'), # H5
    ('H6',        'REAL'), # H6 (mAh)
    ('H7',        'REAL'), # H7 (mV)
    ('H8',        'REAL'), # H8 (mV)
    ('H9',        'REAL'), # H9 (s)
    ('H10',       'REAL'), # H10
    ('H11',       'REAL'), # H11
    ('H12',       'REAL'), # H12
    ('H15',       'REAL'), # H15 (mV)
    ('H16',       'REAL'), # H16 (mV)
    ('H17',       'REAL'), # H17 (0.01 kWh): accumulated daily production
    ('H18',       'REAL'), # H18 (0.01 kWh): accumulated daily production
    ('H19',       'REAL'), # H19 (0.01 kWh): accumulated daily production
    ('H20',       'REAL'), # H20 (0.01 kWh): accumulated daily production
    ('H21',       'REAL'), # H21 (W)
    ('H22',       'REAL'), # H22 (0.01 kWh)
    ('H23',       'REAL'), # H23 (W)
]

weewx.units.obs_group_dict['range'] = 'group_range'
weewx.units.obs_group_dict['range2'] = 'group_range'
weewx.units.obs_group_dict['range3'] = 'group_range'
weewx.units.USUnits['group_range'] = 'inch'
weewx.units.MetricUnits['group_range'] = 'cm'
weewx.units.MetricWXUnits['group_range'] = 'cm'


class VEDirectConfigurationEditor(weewx.drivers.AbstractConfEditor):
    @property
    def default_stanza(self):
        return """
[VEDirect]
    # This section is for the VEDirect driver.

    # The port to which the device is connected
    port = /dev/ttyUSB0

    # The driver to use
    driver = user.vedirect
"""
    def prompt_for_settings(self):
        print "Specify the serial port on which the device is connected, for"
        print "example /dev/ttyUSB0 or /dev/ttyS0."
        port = self._prompt('port', '/dev/ttyUSB0')
        return {'port': port}

class VEDirectDriver(weewx.drivers.AbstractDevice):

    def __init__(self, **stn_dict):
        loginf('driver version is %s' % DRIVER_VERSION)
        self._model = stn_dict.get('model', 'VEDirect')
        self._poll_interval = int(stn_dict.get('poll_interval', 1))
        loginf('poll interval is %s' % self._poll_interval)
        port = stn_dict.get('port', DEFAULT_PORT)
        loginf('port is %s' % port)
        self._ved = VEDirect(port)
        self._ved.open()

    def closePort(self):
        self._ved.close()

    @property
    def hardware_name(self):
        return self._model

    def genLoopPackets(self):
        while True:
            data = self._ved.get_data()
            if data:
                logdbg("raw data: %s" % data)
                packet = self._data_to_packet(data)
                logdbg("packet: %s" % packet)
                if packet:
                    yield packet
            time.sleep(self._poll_interval)
                

    def _data_to_packet(self, data):
        # convert raw data to database fields
        # {'LOAD': 'OFF', 'H19': '467', 'VPV': '56790', 'ERR': '0', 'FW': '130', 'I': '6900', 'H21': '96', 'PID': '0xA056', 'H20': '4', 'H23': '117', 'H22': '22', 'HSDS': '25', 'SER#': 'HQ1804IWW4P', 'V': '13580', 'CS': '3', 'PPV': '96'}

        # FW: firmware version
        # SER#: serial number
        # PID: product ID
        # HSDS: 
        
        pkt = dict()
        if 'ERR' in data:
            pkt['error'] = 0 if data.get('ERR', '0') == '0' else 1
        if 'LOAD' in data:
            pkt['load'] = 0 if data.get('LOAD', 'OFF') == 'OFF' else 1
        if 'CS' in data:
            pkt['CS'] = int(data['CS'])
        for k in ['PPV']:
            if k in data:
                pkt[k] = int(data[k])
        for k in ['I', 'V', 'VPV']:
            if k in data:
                pkt[k] = float(data[k]) / 1000.0
        for k in ['H19', 'H20', 'H21', 'H22', 'H23']:
            if k in data:
                pkt[k] = int(data[k])

        # if we actually ended up with something, then make it a weewx packet
        if pkt:
            pkt['dateTime'] = int(time.time() + 0.5)
            pkt['usUnits'] = weewx.US
        return pkt


class VEDirect:

    (HEX, WAIT_HEADER, IN_KEY, IN_VALUE, IN_CHECKSUM) = range(5)

    def __init__(self, port):
        self.ser = None
        self.port = port
        self.baudrate = 19200
        self.timeout = 3
        self.header1 = '\r'
        self.header2 = '\n'
        self.hexmarker = ':'
        self.delimiter = '\t'
        self.key = ''
        self.start = ''
        self.value = ''
        self.bytes_sum = 0;
        self.state = self.WAIT_HEADER
        self.values = {}

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, _, value, traceback):
        self.close()

    def open(self):
        self.ser = serial.Serial(
            self.port, self.baudrate, timeout=self.timeout)

    def close(self):
        if self.ser is not None:
            self.ser.close()
            self.ser = None

    def input(self, byte):
        if byte == self.hexmarker and self.state != self.IN_CHECKSUM:
            self.state = self.HEX
        if self.state == self.WAIT_HEADER:
            self.bytes_sum += ord(byte)
            if byte == self.header1:
                self.state = self.WAIT_HEADER
            elif byte == self.header2:
                self.state = self.IN_KEY
            return None
        elif self.state == self.IN_KEY:
            self.bytes_sum += ord(byte)
            if byte == self.delimiter:
                if self.start == self.key:
                    self.start = 'ALL'
                elif self.start == '':
                    self.start = self.key
                if self.key == 'Checksum':
                    self.state = self.IN_CHECKSUM
                else:
                    self.state = self.IN_VALUE
            else:
                self.key += byte
            return None
        elif self.state == self.IN_VALUE:
            self.bytes_sum += ord(byte)
            if byte == self.header1:
                self.state = self.WAIT_HEADER
                self.values[self.key] = self.value;
                self.key = '';
                self.value = '';
            else:
                self.value += byte
            return None
        elif self.state == self.IN_CHECKSUM:
            self.bytes_sum += ord(byte)
            self.key = ''
            self.value = ''
            self.state = self.WAIT_HEADER
            if self.bytes_sum % 256 == 0:
                self.bytes_sum = 0
                if self.start == 'ALL':
                    self.start = ''
                    return self.values
                else:
                    return None
            else:
                # malformed packet
                self.bytes_sum = 0
                self.start = ''
                self.values = dict()
        elif self.state == self.HEX:
            self.bytes_sum = 0
            if byte == self.header2:
                self.state = self.WAIT_HEADER
        else:
            raise AssertionError()

    def get_data(self):
        while True:
            byte = self.ser.read(1)
            if byte:
                packet = self.input(byte)
                if packet is not None:
                    return packet
            else:
                break


# define a main entry point for basic testing of the station without weewx
# engine and service overhead.  invoke this as follows from the weewx root dir:
#
# PYTHONPATH=bin python bin/weewx/drivers/vedirect.py

if __name__ == '__main__':
    import optparse

    usage = """%prog [options] [--debug] [--help]"""
    
    syslog.openlog('vedirect', syslog.LOG_PID | syslog.LOG_CONS)
    syslog.setlogmask(syslog.LOG_UPTO(syslog.LOG_INFO))
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('--version', dest='version', action='store_true',
                      help='display driver version')
    parser.add_option('--debug', dest='debug', action='store_true',
                      help='display diagnostic information while running')
    parser.add_option('--port', dest='port', metavar='PORT',
                      help='serial port to which the station is connected',
                      default=DEFAULT_PORT)

    (options, args) = parser.parse_args()

    if options.version:
        print "vedirect driver version %s" % DRIVER_VERSION
        exit(1)

    if options.debug:
        syslog.setlogmask(syslog.LOG_UPTO(syslog.LOG_DEBUG))

    with VEDirect(options.port) as s:
        while True:
            data = s.get_data()
            print "data:", data
            time.sleep(1)
