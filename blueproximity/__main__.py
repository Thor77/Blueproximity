# coding: utf-8

import os.path

from xdg import BaseDirectory

import blueproximity.config
import gtk
from blueproximity import APP_NAME, Proximity, ProximityGUI


def main():
    # load config
    config_path = os.path.join(
        BaseDirectory.save_config_path(APP_NAME), 'config.ini')
    configuration = blueproximity.config.load(config_path)

    # start Proximity-thread
    proximity = Proximity(configuration)
    proximity.start()

    # start GUI
    ProximityGUI(configuration)

    # make GTK threadable
    gtk.gdk.threads_init()

    # aaaaand action!
    gtk.main()

if __name__ == '__main__':
    main()
