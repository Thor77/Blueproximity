# -*- coding: utf-8 -*-
import re
import subprocess

import bluetooth
import bluetooth._bluetooth as bluez
from blueproximity.log import logger

rssi_re = re.compile('^RSSI return value: (-?\d+)')


def scan():
    '''
    Scan for bluetooth-devices

    :return: list of bluetooth-devices
    :rtype: [blueproximity.device.BluetoothDevice]
    '''
    def _scan():
        for mac, name in bluetooth.discover_devices(lookup_names=True):
            yield BluetoothDevice(mac, name)
    return list(_scan())


class BluetoothDevice(object):
    '''
    Abstract access to a bluetooth-device
    '''
    def __init__(self, mac, port=None, name=None):
        self.mac = mac
        self.port = port
        if not name:
            self.name = bluetooth.lookup_name(mac)
        else:
            self.name = name

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
            except:
                logger.debug('Couldn\'t get connection on port %s', port)

    def connect(self, port=None):
        '''
        Connect to the device

        :param port: port used for connection
        :type port: int
        '''
        if not port:
            port = self.port
        self.sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM,
                                              bluez.btsocket())
        self.sock.connect((self.mac, port))

    def disconnect(self):
        '''
        Disconnect the device
        '''
        if self.sock:
            self.sock.close()
            self.sock = None

    @property
    def distance(self):
        '''
        Determinte distance of the device

        :return: distance of the device
        :rtype: int
        '''
        p = subprocess.run(['hcitool', 'rssi', self.mac],
                           stdout=subprocess.PIPE)
        if p.returncode == 0:
            match = rssi_re.match(p.stdout.decode('utf-8'))
            if match:
                return int(match.group(1))
        return -255

    def __str__(self):
        return '{name}({mac}, {port})'.format(name=self.name, mac=self.mac,
                                              port=self.port)

    def __repr__(self):
        return self.__str__()
