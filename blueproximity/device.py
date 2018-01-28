# -*- coding: utf-8 -*-
import re
import subprocess

import bluetooth
import bluetooth._bluetooth as bluez

from blueproximity.log import logger
from blueproximity.exceptions import DeviceException

rssi_re = re.compile('^RSSI return value: (-?\d+)')


def scan():
    '''
    Scan for bluetooth-devices

    :return: list of bluetooth-devices
    :rtype: [blueproximity.device.BluetoothDevice]
    '''
    def _scan():
        for mac, name in bluetooth.discover_devices(lookup_names=True):
            yield BluetoothDevice(mac=mac, name=name)
    return list(_scan())


class BluetoothDevice(object):
    '''
    Abstract access to a bluetooth-device
    '''
    def __init__(self, mac, port=None, name=None):
        self.mac = mac
        self.port = port
        self.name = name

        self.port = self.scan_ports() if not port else port
        self.name = bluetooth.lookup_name(mac) if not name else name

    def scan_ports(self):
        '''
        Find a suitable port for connection

        :return: suitable port
        :rtype: int
        '''
        for port in range(1, 30):
            try:
                self.connect(port)
                self.disconnect()
                return port
            except bluetooth.btcommon.BluetoothError:
                logger.debug('Couldn\'t get connection on port %s', port)
        raise DeviceException(
            '{}: Couldn\'t find suitable port for connection'.format(self)
        )

    def connect(self, port=None):
        '''
        Connect to the device

        :param port: port used for connection
        :type port: int
        '''
        if self.connected:
            return
        if not port:
            port = self.port
        self.sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM,
                                              bluez.btsocket())
        self.sock.connect((self.mac, port))

    def disconnect(self):
        '''
        Disconnect the device
        '''
        if not self.connected:
            return
        if self.sock:
            self.sock.close()
            self.sock = None

    @property
    def connected(self):
        p = subprocess.run(
            ['hcitool', 'lq', self.mac],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return p.returncode == 0

    @property
    def distance(self):
        '''
        Determinte distance of the device

        :return: distance of the device
        :rtype: int
        '''
        if not self.connected:
            self.connect()
        p = subprocess.run(
            ['hcitool', 'rssi', self.mac],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        if p.returncode == 0:
            match = rssi_re.match(p.stdout.decode('utf-8'))
            if match:
                return abs(int(match.group(1)))
        return 255

    def __str__(self):
        return 'BluetoothDevice(mac={mac}, port={port}, name={name}, '\
            'connected={connected})'.format(
                mac=self.mac, port=self.port,
                name=self.name, connected=self.connected
            )

    def __repr__(self):
        return self.__str__()
