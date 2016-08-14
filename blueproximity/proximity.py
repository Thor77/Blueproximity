# coding: utf-8

from threading import Thread

import bluetooth
from blueproximity.translation import _


class Proximity (Thread):
    '''
    Does 'all the magic' like regular device detection and decision making
    whether a device is known as present or away.
    Here is where all the bluetooth specific part takes place.
    It is build to be run a a seperate thread
    and would run perfectly without any GUI.
    Please note that the present-command is issued by the GUI
    whereas the locking and unlocking is called by this class.
    This is inconsitent and to be changed in a future release.
    '''
    def __init__(self, config):
        '''
        :param config: ConfigObj that stores all our settings
        '''
        Thread.__init__(self, name="WorkerThread")
        self.config = config
        self.Dist = -255
        self.State = _("gone")
        self.Simulate = False
        self.Stop = False
        self.procid = 0
        self.dev_mac = self.config['device_mac']
        self.dev_channel = self.config['device_channel']
        self.ringbuffer_size = self.config['buffer_size']
        self.ringbuffer = [-254] * self.ringbuffer_size
        self.ringbuffer_pos = 0
        self.gone_duration = self.config['lock_duration']
        self.gone_limit = -self.config['lock_distance']
        self.active_duration = self.config['unlock_duration']
        self.active_limit = -self.config['unlock_distance']
        self.ErrorMsg = _("Initialized...")
        self.sock = None
        self.ignoreFirstTransition = True
        self.logger = Logger()
        self.logger.configureFromConfig(self.config)
        self.timeAct = 0
        self.timeGone = 0
        self.timeProx = 0

    def get_device_list(self):
        '''
        Return all active bluetooth devices found. (blocking)
        '''
        ret_tab = list()
        nearby_devices = bluetooth.discover_devices()
        for bdaddr in nearby_devices:
            ret_tab.append([str(bdaddr), str(bluetooth.lookup_name(bdaddr))])
        return ret_tab

    def kill_connection(self):
        '''
        Kill the rssi detection connection
        '''
        if self.sock:
            self.sock.close()
        self.sock = None
        return 0

    def get_proximity_by_mac(self, dev_mac):
        '''
        Get rssi values for a connected device

        Currently not in use and doesn't work
        '''
        sock = bluez.hci_open_dev(dev_id)
        old_filter = sock.getsockopt(bluez.SOL_HCI, bluez.HCI_FILTER, 14)

        # perform a device inquiry on bluetooth device #0
        # The inquiry should last 8 * 1.28 = 10.24 seconds
        # before the inquiry is performed, bluez should flush its cache of
        # previously discovered devices
        flt = bluez.hci_filter_new()
        bluez.hci_filter_all_events(flt)
        bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
        sock.setsockopt(bluez.SOL_HCI, bluez.HCI_FILTER, flt)

        duration = 4
        max_responses = 255
        cmd_pkt = struct.pack("BBBBB", 0x33, 0x8b, 0x9e, duration, max_responses)
        bluez.hci_send_cmd(sock, bluez.OGF_LINK_CTL, bluez.OCF_INQUIRY, cmd_pkt)

        results = []

        done = False
        while not done:
            pkt = sock.recv(255)
            ptype, event, plen = struct.unpack("BBB", pkt[:3])
            if event == bluez.EVT_INQUIRY_RESULT_WITH_RSSI:
                pkt = pkt[3:]
                nrsp = struct.unpack("B", pkt[0])[0]
                for i in range(nrsp):
                    addr = bluez.ba2str(pkt[1 + 6 * i:1 + 6 * i + 6])
                    rssi = struct.unpack("b", pkt[1+13*nrsp+i])[0]
                    results.append((addr, rssi))
                    print("[%s] RSSI: [%d]" % (addr, rssi))
            elif event == bluez.EVT_INQUIRY_COMPLETE:
                done = True
            elif event == bluez.EVT_CMD_STATUS:
                status, ncmd, opcode = struct.unpack("BBH", pkt[3:7])
                if status != 0:
                    print("uh oh...")
                    printpacket(pkt[3:7])
                    done = True
            else:
                print("unrecognized packet type 0x%02x" % ptype)

        # restore old filter
        sock.setsockopt(bluez.SOL_HCI, bluez.HCI_FILTER, old_filter)

        sock.close()
        return results

    def get_proximity_once(self, dev_mac):
        '''
        Return the rssi value of a connection to the given mac address

        :param dev_mac: mac address of the device to check
        '''
        ret_val = os.popen("hcitool rssi " + dev_mac + " 2>/dev/null").readlines()
        if ret_val == []:
            ret_val = -255
        else:
            ret_val = ret_val[0].split(':')[1].strip(' ')
        return int(ret_val)

    def get_connection(self, dev_mac, dev_channel):
        '''
        Fire up an rfcomm connection to a certain device on the given channel

        :param dev_mac: mac address of the device to connect to
        :param dev_channel: rfcomm channel we want to connect to
        '''
        try:
            self.procid = 1
            _sock = bluez.btsocket()
            self.sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM, _sock)
            self.sock.connect((dev_mac, dev_channel))
        except:
            self.procid = 0
            pass
        return self.procid

    def run_cycle(self, dev_mac, dev_channel):
        # reads the distance and averages it over the ringbuffer
        self.ringbuffer_pos = (self.ringbuffer_pos + 1) % self.ringbuffer_size
        self.ringbuffer[self.ringbuffer_pos] = self.get_proximity_once(dev_mac)
        ret_val = 0
        for val in self.ringbuffer:
            ret_val = ret_val + val
        if self.ringbuffer[self.ringbuffer_pos] == -255:
            self.ErrorMsg = _("No connection found, trying to establish one...")
            self.kill_connection()
            self.get_connection(dev_mac, dev_channel)
        return int(ret_val / self.ringbuffer_size)

    def go_active(self):
        # The Doctor is in
        if self.ignoreFirstTransition:
            self.ignoreFirstTransition = False
        else:
            self.logger.log_line(_('screen is unlocked'))
            if (self.timeAct == 0):
                self.timeAct = time.time()
                ret_val = os.popen(self.config['unlock_command']).readlines()
                self.timeAct = 0
            else:
                self.logger.log_line(_('A command for %s has been skipped because the former command did not finish yet.') % _('unlocking'))
                self.ErrorMsg = _('A command for %s has been skipped because the former command did not finish yet.') % _('unlocking')

    def go_gone(self):
        # The Doctor is out
        if self.ignoreFirstTransition:
            self.ignoreFirstTransition = False
        else:
            self.logger.log_line(_('screen is locked'))
            if (self.timeGone == 0):
                self.timeGone = time.time()
                ret_val = os.popen(self.config['lock_command']).readlines()
                self.timeGone = 0
            else:
                self.logger.log_line(_('A command for %s has been skipped because the former command did not finish yet.') % _('locking'))
                self.ErrorMsg = _('A command for %s has been skipped because the former command did not finish yet.') % _('locking')

    def go_proximity(self):
        # The Doctor is still in
        if (self.timeProx == 0):
            self.timeProx = time.time()
            ret_val = os.popen(self.config['proximity_command']).readlines()
            self.timeProx = 0
        else:
            self.logger.log_line(_('A command for %s has been skipped because the former command did not finish yet.') % _('proximity'))
            self.ErrorMsg = _('A command for %s has been skipped because the former command did not finish yet.') % _('proximity')

    def run(self):
        '''
        Main loop for proximity detection.
        It checks the rssi value against limits and invokes all commands.
        '''
        duration_count = 0
        state = _("gone")
        proxiCmdCounter = 0
        while not self.Stop:
            try:
                if self.dev_mac != "":
                    self.ErrorMsg = _("running...")
                    dist = self.run_cycle(self.dev_mac, self.dev_channel)
                else:
                    dist = -255
                    self.ErrorMsg = "No bluetooth device configured..."
                if state == _("gone"):
                    if dist >= self.active_limit:
                        duration_count = duration_count + 1
                        if duration_count >= self.active_duration:
                            state = _("active")
                            duration_count = 0
                            if not self.Simulate:
                                # start the process asynchronously so we are not hanging here...
                                timerAct = gobject.timeout_add(5, self.go_active)
                                # self.go_active()
                    else:
                        duration_count = 0
                else:
                    if dist <= self.gone_limit:
                        duration_count = duration_count + 1
                        if duration_count >= self.gone_duration:
                            state = _("gone")
                            proxiCmdCounter = 0
                            duration_count = 0
                            if not self.Simulate:
                                # start the process asynchronously so we are not hanging here...
                                timerGone = gobject.timeout_add(5, self.go_gone)
                                # self.go_gone()
                    else:
                        duration_count = 0
                        proxiCmdCounter = proxiCmdCounter + 1
                if dist != self.Dist or state != self.State:
                    # print "Detected distance atm: " + str(dist) + "; state is " + state
                    pass
                self.State = state
                self.Dist = dist
                # let's handle the proximity command
                if (proxiCmdCounter >= self.config['proximity_interval']) and not self.Simulate and (self.config['proximity_command'] != ''):
                    proxiCmdCounter = 0
                    # start the process asynchronously so we are not hanging here...
                    timerProx = gobject.timeout_add(5, self.go_proximity)
                time.sleep(1)
            except KeyboardInterrupt:
                break
        self.kill_connection()
