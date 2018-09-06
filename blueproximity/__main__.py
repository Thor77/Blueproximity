# -*- coding: utf-8 -*-
import argparse
import os.path

from xdg import BaseDirectory

from blueproximity import (APP_NAME, BluetoothDevice, Worker, config,
                           init_logging)


def cli():
    parser = argparse.ArgumentParser(prog='blueproximity', description='''
        Unlock your computer as soon as a bluetooth-device is in range
    ''')
    parser.add_argument('--gui', help='Start GUI', action='store_true')
    parser.add_argument('-c', '--config', help='Path to configfile', type=str)
    parser.add_argument(
        '-m', '--mac', help='Provide mac of target device', type=str, required=True
    )
    return parser.parse_args()


def main():
    # cli-args
    args = cli()

    # load config
    if args.config:
        config_path = args.config
    else:
        config_path = os.path.join(
            BaseDirectory.save_config_path(APP_NAME), 'config.ini')
    configuration = config.load(config_path, validate=True)
    # initiate logging
    init_logging(configuration)
    device = BluetoothDevice(args.mac)
    worker = Worker(device, configuration)
    try:
        worker.run()
    except KeyboardInterrupt:
        worker.stop()


if __name__ == '__main__':
    main()
