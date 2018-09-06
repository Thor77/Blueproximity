# -*- coding: utf-8 -*-
import subprocess
import threading
import time
from collections import namedtuple

from blueproximity.log import logger

State = namedtuple('State', ['name', 'distance', 'command'])


class Worker(threading.Thread):
    def __init__(self, device, configuration):
        self.device = device
        self.configuration = configuration
        self.stopped = False
        super().__init__()

    def run(self):
        super().run()
        logger.info('Starting daemon for "%s"', self.device)
        # determine lock and unlock distance and command
        states = {
            state: State(
                state,
                self.configuration.getint(state.title(), 'distance'),
                self.configuration.get(state.title(), 'command')
            )
            for state in ['lock', 'unlock']
        }
        # set initial state
        state = states['unlock']
        while not self.stopped:
            last_state = state
            # determine current distance
            current_distance = self.device.distance
            logger.debug('Current distance: %s', current_distance)
            # set new state
            if current_distance >= states['lock'].distance:
                state = states['lock']
            elif current_distance <= states['unlock'].distance:
                state = states['unlock']

            if state != last_state:
                logger.info('Running command for new state %s', state.name)
                subprocess.run(state.command.split())
            # sleep for configured interval
            time.sleep(self.configuration.getint('Proximity', 'interval'))
        # disconnect from device
        self.device.disconnect()

    def stop(self):
        logger.info('Stopping daemon for "%s"', self.device)
        # make sure loop doesn't run again
        self.stopped = True
        # disconnect devicd
        self.device.disconnect()

