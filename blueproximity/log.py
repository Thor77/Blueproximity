# -*- coding: utf-8 -*-
import logging
import logging.handlers

from blueproximity import APP_NAME

logger = logging.getLogger(APP_NAME)


def init(configuration):
    '''
    Initiate package-logger based on `configuration`

    :param configuration: parsed configuration
    :type configuration: configparser.ConfigParser
    '''
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
    # add handlers
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if configuration.getboolean('Log', 'syslog'):
        sh = logging.handlers.SysLogHandler(
            configuration.get('Log', 'syslog_facility'))
        sh.setFormatter(formatter)
        logger.addHandler(sh)
    if configuration.getboolean('Log', 'file'):
        fh = logging.FileHandler(filename=configuration.get('Log', 'filename'))
        fh.setFormatter(formatter)
        logger.addHandler(fh)
