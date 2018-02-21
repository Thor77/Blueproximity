# -*- coding: utf-8 -*-
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser


DEFAULT_CONFIG = {
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
        'interval': 60
    },
    'Log': {
        'syslog': False,
        'syslog_facility': 'local7',
        'file': False,
        'filename': 'blueproximity.log'
    }
}

# generate dict of expected types for config settings
# by using values from DEFAULT_CONFIG as a reference
DEFAULT_CONFIG_TYPES = {
    section: {
        key: type(value)
        for key, value in settings.items()
    }
    for section, settings in DEFAULT_CONFIG.items()
}


class InvalidConfiguration(Exception):
    pass


def _validate(configuration):
    '''
    Validate `configuration` has all required parameters set
    '''
    for section, settings in DEFAULT_CONFIG_TYPES.items():
        for setting, expected_type in settings.items():
            try:
                # get value from configuration
                # and try to convert it to the expected type
                expected_type(configuration.get(section, setting))
            except ValueError:
                raise InvalidConfiguration(
                    '{}.{} can\'t be converted to expected type {}'.format(
                        section, setting, expected_type.__name__
                    )
                )


def load(path=None, validate=False):
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
    if validate:
        _validate(config)
    return config
