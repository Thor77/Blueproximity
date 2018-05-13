# -*- coding: utf-8 -*-
# pylama:skip=1
APP_NAME = 'blueproximity'

from blueproximity.log import init as init_logging
from blueproximity.device import BluetoothDevice
from blueproximity.worker import Worker
from blueproximity.gui import run as run_gui
from blueproximity import config
