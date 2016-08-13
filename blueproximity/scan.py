# coding: utf-8


# ScanDevice is a helper class used for scanning for open rfcomm channels
# on a given device. It uses asynchronous calls via gobject.timeout_add to
# not block the main process. It updates a given model after every scanned port
# and calls a callback function after finishing the scanning process.
class ScanDevice(object):
    # Constructor which sets up and immediately starts the scanning process.
    # Note that the bluetooth device should not be connected while scanning occurs.
    # @param device_mac MAC address of the bluetooth device to be scanned.
    # @param was_paused A parameter to be passed to the finishing callback function.
    # This is to automatically put the GUI in simulation mode if it has been before scanning. (dirty hack)
    # @param callback A callback function to be called after scanning has been done.
    # It takes one parameter which is preset by the was_paused parameter.
    def __init__(self, device_mac, model, was_paused, callback):
        self.mac = device_mac
        self.model = model
        self.stopIt = False
        self.port = 1
        self.timer = gobject.timeout_add(500, self.runStep)
        self.model.clear()
        self.was_paused = was_paused
        self.callback = callback

    # Checks whether a certain port on the given mac address is reachable.
    # @param port An integer from 1 to 30 giving the rfcomm channel number to try to reach.
    # The function does not return True/False but the actual translated strings.
    def scanPortResult(self, port):
        # here we scan exactly one port and give a textual result
        _sock = bluez.btsocket()
        sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM, _sock)
        try:
            sock.connect((self.mac, port))
            sock.close
            return _("usable")
        except:
            return _("closed or denied")

    # Asynchronous working thread.
    # It scans a single port at a time and reruns with the next one in the next loop.
    def runStep(self):
        # here the scanning of all ports is done
        self.model.append([str(self.port), self.scanPortResult(self.port)])
        self.port = self.port + 1
        if not self.port > 30 and not self.stopIt:
            self.timer = gobject.timeout_add(500, self.runStep)
        else:
            self.callback(self.was_paused)

    def doStop(self):
        self.stopIt = True
