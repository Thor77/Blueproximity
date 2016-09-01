import subprocess
import threading
import time

from blueproximity.device import BluetoothDevice
from blueproximity.log import logger


class Worker(threading.Thread):
    def __init__(self, configuration):
        # setup bluetooth device
        self.device = BluetoothDevice(
            configuration.get('Device', 'mac'),
            configuration.get('Device', 'port'),
            configuration.get('Device', 'name')
        )
        # make config globally available
        self.config = configuration

    def run(self):
        # how many intervals the device was in range
        unlock = 0
        # how many intervals the device was not in range
        lock = 0
        while True:
            # connect to the device
            self.device.connect()
            # check proximity
            distance = self.device.distance
            if distance <= self.config.get('Unlock', 'distance'):
                unlock += 1
                lock = 0
            elif distance >= self.config.get('Lock', 'distance'):
                lock += 1
                unlock = 0
            else:
                unlock = 0
                lock = 0
            # check for (un)lock threshold
            if unlock >= self.config.get('Unlock', 'duration'):
                # set unlock command
                command = self.config.get('Unlock', 'command')
            elif lock >= self.config.get('Lock', 'duration'):
                # set lock command
                command = self.config.get('Lock', 'command')
            else:
                command = None
            if command:
                # reset lock and unlock variables
                unlock = 0
                lock = 0
                # run command
                p = subprocess.run(command.split(), stdout=subprocess.PIPE)
                if p.returncode != 0:
                    logger.critical(
                        'Failed to run "%s": %s',
                        command, p.stdout.decode('utf-8')
                    )
            # sleep interval
            time.sleep(self.interval)
