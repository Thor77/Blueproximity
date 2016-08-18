# coding: utf-8

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser


DEFAULT_CONFIG = {
    'Device': {
        'mac': None,
        'channel': None
    },
    'Lock': {
        'distance': 7,
        'duration': 7,
        'command': 'gnome-screensaver-command -l'
    },
    'Unlock': {
        'distance': 4,
        'duration': 1,
        'command': 'gnome-screensaver-command -d'
    },
    'Proximity': {
        'command': 'gnome-screensaver-command -p',
        'interval': 60
    },
    'Log': {
        'syslog': False,
        'syslog_facility': 'local7',
        'file': False,
        'filename': 'blueproximity.log'
    }
}


def load(path=None):
    '''
    parse config at `config_path`
    :param config_path: path to config-file
    :type config_path: str
    :return: values of config
    :rtype: tuple
    '''
    config = ConfigParser()
    # use this way to set defaults, because ConfigParser.read_dict
    # is not available < 3.2
    for section, items in DEFAULT_CONFIG.items():
        if section not in config.sections():
            config.add_section(section)
        for key, value in items.items():
            config.set(section, key, str(value))
    if path:
        config.read(path)
    return config
