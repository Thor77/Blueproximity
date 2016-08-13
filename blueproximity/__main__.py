# coding: utf-8

import os.path

from xdg import BaseDirectory

import blueproximity.config
from blueproximity import APP_NAME, Proximity, ProximityGUI
from blueproximity.translation import _

try:
    import pygtk
    pygtk.require("2.0")
    import gtk
except ImportError:
    raise Exception(_('GTK2 bindings for Python are not installed.'))
try:
    import gtk.glade
except ImportError:
    raise Exception(_('Glade2 bindings for python are not installed.'))


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
