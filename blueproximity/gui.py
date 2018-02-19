# -*- coding: utf-8 -*-
from collections import namedtuple
from queue import PriorityQueue

import gi

from blueproximity.gui_worker import GUIWorker

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk  # noqa: E402 isort:skip


Task = namedtuple('Task', ['action', 'args'])


class DevicesPage(Gtk.Box):
    def __init__(self, queue):
        super().__init__()
        self.orientation = Gtk.Orientation.VERTICAL
        self.add(Gtk.Label('Devices page content'))


class BlueproximityGUI(Gtk.Window):
    def __init__(self, queue):
        super().__init__(title='Blueproximity')
        self.set_default_size(400, 550)

        notebook = Gtk.Notebook()
        self.add(notebook)

        # Devices page
        notebook.append_page(DevicesPage(queue), Gtk.Label('Devices'))

        # Proximity page
        proximity_page = Gtk.Box()
        proximity_page.add(Gtk.Label('Proximity page content'))
        notebook.append_page(proximity_page, Gtk.Label('Proximity'))

        # Actions page
        actions_page = Gtk.Box()
        actions_page.add(Gtk.Label('Actions page content'))
        notebook.append_page(actions_page, Gtk.Label('Actions'))


def run():
    queue = PriorityQueue()
    # start gui worker
    gw = GUIWorker(queue)
    gw.start()

    window = BlueproximityGUI(queue)
    window.connect('delete-event', Gtk.main_quit)
    window.connect(
        'delete-event', lambda *a: queue.put(a[2]), Task('quit', [])
    )
    window.show_all()
    Gtk.main()
