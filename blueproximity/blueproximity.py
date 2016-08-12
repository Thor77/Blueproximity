#!/usr/bin/env python
# coding: utf-8

# system includes
import os
import sys
import time
import threading
import signal
import syslog
import locale


# Translation stuff
import gettext

# blueproximity
SW_VERSION = '1.2.5'
'''
Add security to your desktop by automatically locking and unlocking
the screen when you and your phone leave/enter the desk.
Think of a proximity detector for your mobile phone via bluetooth.
requires external bluetooth util hcitool to run
(which makes it unix only at this time)
Needed python extensions:
    ConfigObj (python-configobj)
    PyGTK (python-gtk2, python-glade2)
    Bluetooth (python-bluez)

Copyright by Lars Friedrichs <larsfriedrichs@gmx.de>
this source is licensed under the GPL.
I'm a big fan of talkback about how it performs!
I'm also open to feature requests and notes on programming issues,
I am no python master at all...
'''

APP_NAME = "blueproximity"

# This value gives us the base directory for language files and icons.
# Set this value to './' for svn version
# or to '/usr/share/blueproximity/' for packaged version
dist_path = './'

# Get the local directory since we are not installing anything
local_path = dist_path + 'LANG/'

# Collect available languages
available_languages = [locale.getdefaultlocale()[0]]  # system locale
available_languages += os.environ.get('LANGUAGE', '').split(':')  # environment
available_languages += ["en"]  # default language

gettext.bindtextdomain(APP_NAME, local_path)
gettext.textdomain(APP_NAME)
# Get the language to use
gettext_language = gettext.translation(
    APP_NAME, local_path, languages=available_languages, fallback=True
)
# create _-shortcut for translations
_ = gettext_language.gettext


# now the imports from external packages
try:
    import gobject
except:
    print(_("The program cannot import the module gobject."))
    print(_("Please make sure the GObject bindings for python are installed."))
    print(_("e.g. with Ubuntu Linux, type"))
    print(_(" sudo apt-get install python-gobject"))
    sys.exit(1)
try:
    from configobj import ConfigObj
    from validate import Validator
except:
    print(_("The program cannot import the module ConfigObj or Validator."))
    print(_("Please make sure the ConfigObject package for python is installed."))
    print(_("e.g. with Ubuntu Linux, type"))
    print(_(" sudo apt-get install python-configobj"))
    sys.exit(1)
IMPORT_BT = 0
try:
    import bluetooth
    IMPORT_BT = IMPORT_BT + 1
except:
    pass
try:
    import _bluetooth as bluez
    IMPORT_BT = IMPORT_BT + 1
except:
    pass
try:
    import bluetooth._bluetooth as bluez
    IMPORT_BT = IMPORT_BT + 1
except:
    pass
if IMPORT_BT != 2:
    print(_("The program cannot import the module bluetooth."))
    print(_("Please make sure the bluetooth bindings for python as well as bluez are installed."))
    print(_("e.g. with Ubuntu Linux, type"))
    print(_(" sudo apt-get install python-bluez"))
    sys.exit(1)
try:
    import pygtk
    pygtk.require("2.0")
    import gtk
except:
    print(_("The program cannot import the module pygtk."))
    print(_("Please make sure the GTK2 bindings for python are installed."))
    print(_("e.g. with Ubuntu Linux, type"))
    print(_(" sudo apt-get install python-gtk2"))
    sys.exit(1)
try:
    import gtk.glade
except:
    print(_("The program cannot import the module glade."))
    print(_("Please make sure the Glade2 bindings for python are installed."))
    print(_("e.g. with Ubuntu Linux, type"))
    print(_(" sudo apt-get install python-glade2"))
    sys.exit(1)


# Setup config file specs and defaults
# This is the ConfigObj's syntax
conf_specs = [
    'device_mac=string(max=17,default="")',
    'device_channel=integer(1,30,default=7)',
    'lock_distance=integer(0,127,default=7)',
    'lock_duration=integer(0,120,default=6)',
    'unlock_distance=integer(0,127,default=4)',
    'unlock_duration=integer(0,120,default=1)',
    'lock_command=string(default=''gnome-screensaver-command -l'')',
    'unlock_command=string(default=''gnome-screensaver-command -d'')',
    'proximity_command=string(default=''gnome-screensaver-command -p'')',
    'proximity_interval=integer(5,600,default=60)',
    'buffer_size=integer(1,255,default=1)',
    'log_to_syslog=boolean(default=True)',
    'log_syslog_facility=string(default=''local7'')',
    'log_to_file=boolean(default=False)',
    'log_filelog_filename=string(default=''' + os.getenv('HOME') + '/blueproximity.log'')'
]


# The icon used at normal operation and in the info dialog.
icon_base = 'blueproximity_base.svg'
# The icon used at distances greater than the unlock distance.
icon_att = 'blueproximity_attention.svg'
# The icon used if no proximity is detected.
icon_away = 'blueproximity_nocon.svg'
# The icon used during connection processes and with connection errors.
icon_con = 'blueproximity_error.svg'
# The icon shown if we are in pause mode.
icon_pause = 'blueproximity_pause.svg'

# This class creates all logging information in the desired form.
# We may log to syslog with a given syslog facility, while the severety is always info.
# We may also log a simple file.
class Logger(object):
    # Constructor does nothing special.
    def __init__(self):
        self.disable_syslogging()
        self.disable_filelogging()

    # helper function to convert a string (given by a ComboBox) to the corresponding
    # syslog module facility constant.
    # @param facility One of the 8 "localX" facilities or "user".
    def getFacilityFromString(self, facility):
        # Returns the correct constant value for the given facility
        dict = {
            "local0": syslog.LOG_LOCAL0,
            "local1": syslog.LOG_LOCAL1,
            "local2": syslog.LOG_LOCAL2,
            "local3": syslog.LOG_LOCAL3,
            "local4": syslog.LOG_LOCAL4,
            "local5": syslog.LOG_LOCAL5,
            "local6": syslog.LOG_LOCAL6,
            "local7": syslog.LOG_LOCAL7,
            "user": syslog.LOG_USER
        }
        return dict[facility]

    # Activates the logging to the syslog server.
    def enable_syslogging(self, facility):
        self.syslog_facility = self.getFacilityFromString(facility)
        syslog.openlog('blueproximity', syslog.LOG_PID)
        self.syslogging = True

    # Deactivates the logging to the syslog server.
    def disable_syslogging(self):
        self.syslogging = False
        self.syslog_facility = None

    # Activates the logging to the given file.
    # Actually tries to append to that file first, afterwards tries to write to it.
    # If both don't work it gives an error message on stdout and does not activate the logging.
    # @param filename The complete filename where to log to
    def enable_filelogging(self, filename):
        self.filename = filename
        try:
            # let's append
            self.flog = open(filename, 'a')
            self.filelogging = True
        except:
            try:
                # did not work, then try to create file (is this really needed or does python know another attribute to file()?
                self.flog = open(filename, 'w')
                self.filelogging = True
            except:
                print(_("Could not open logfile '%s' for writing." % filename))
                self.disable_filelogging

    # Deactivates logging to a file.
    def disable_filelogging(self):
        try:
            self.flog.close()
        except:
            pass
        self.filelogging = False
        self.filename = ''

    # Outputs a line to the logs. Takes care of where to put the line.
    # @param line A string that is printed in the logs. The string is unparsed and not sanatized by any means.
    def log_line(self, line):
        if self.syslogging:
            syslog.syslog(self.syslog_facility | syslog.LOG_NOTICE, line)
        if self.filelogging:
            try:
                self.flog.write(time.ctime() + " blueproximity: " + line + "\n")
                self.flog.flush()
            except:
                self.disable_filelogging()

    # Activate the logging mechanism that are requested by the given configuration.
    # @param config A ConfigObj object containing the needed settings.
    def configureFromConfig(self, config):
        if config['log_to_syslog']:
            self.enable_syslogging(config['log_syslog_facility'])
        else:
            self.disable_syslogging()
        if config['log_to_file']:
            if self.filelogging and config['log_filelog_filename'] != self.filename:
                self.disable_filelogging()
                self.enable_filelogging(config['log_filelog_filename'])
            elif not self.filelogging:
                self.enable_filelogging(config['log_filelog_filename'])

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


# This class does 'all the magic' like regular device detection and decision making
# whether a device is known as present or away. Here is where all the bluetooth specific
# part takes place. It is build to be run a a seperate thread and would run perfectly without any GUI.
# Please note that the present-command is issued by the GUI whereas the locking and unlocking
# is called by this class. This is inconsitent and to be changed in a future release.
class Proximity (threading.Thread):
    # Constructor to setup our local variables and initialize threading.
    # @param config a ConfigObj object that stores all our settings
    def __init__(self, config):
        threading.Thread.__init__(self, name="WorkerThread")
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

    # Returns all active bluetooth devices found. This is a blocking call.
    def get_device_list(self):
        ret_tab = list()
        nearby_devices = bluetooth.discover_devices()
        for bdaddr in nearby_devices:
            ret_tab.append([str(bdaddr), str(bluetooth.lookup_name(bdaddr))])
        return ret_tab

    # Kills the rssi detection connection.
    def kill_connection(self):
        if self.sock:
            self.sock.close()
        self.sock = None
        return 0

    # This function is NOT IN USE. It is a try to create a python only way to
    # get the rssi values for a connected device. It does not work at this time.
    def get_proximity_by_mac(self, dev_mac):
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

    # Returns the rssi value of a connection to the given mac address.
    # @param dev_mac mac address of the device to check.
    # This should also be removed but I still have to find a way to read the rssi value from python
    def get_proximity_once(self, dev_mac):
        ret_val = os.popen("hcitool rssi " + dev_mac + " 2>/dev/null").readlines()
        if ret_val == []:
            ret_val = -255
        else:
            ret_val = ret_val[0].split(':')[1].strip(' ')
        return int(ret_val)

    # Fire up an rfcomm connection to a certain device on the given channel.
    # Don't forget to set up your phone not to ask for a connection.
    # (at least for this computer.)
    # @param dev_mac mac address of the device to connect to.
    # @param dev_channel rfcomm channel we want to connect to.
    def get_connection(self, dev_mac, dev_channel):
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

    # This is the main loop of the proximity detection engine.
    # It checks the rssi value against limits and invokes all commands.
    def run(self):
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


if __name__ == '__main__':
    gtk.glade.bindtextdomain(APP_NAME, local_path)
    gtk.glade.textdomain(APP_NAME)

    # react on ^C
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    # read config if any
    configs = []
    new_config = True
    conf_dir = os.path.join(os.getenv('HOME'), '.blueproximity')
    try:
        # check if config directory exists
        os.mkdir(conf_dir)
        print((_("Creating new config directory '%s'.") % conf_dir))
        # we should now look for an old config file and try to move it to a better place...
        os.rename(os.path.join(os.getenv('HOME'), '.blueproximityrc'), os.path.join(conf_dir, _("standard") + ".conf"))
        print((_("Moved old configuration to the new config directory.")))
    except:
        # we can't create it because it is already there...
        pass

    # now look for .conf files in there
    vdt = Validator()
    for filename in os.listdir(conf_dir):
        if filename.endswith('.conf'):
            try:
                # add every valid .conf file to the array of configs
                config = ConfigObj(os.path.join(conf_dir, filename), {'create_empty': False, 'file_error': True, 'configspec': conf_specs})
                # first validate it
                config.validate(vdt, copy=True)
                # rewrite it in a secure manner
                config.write()
                # if everything worked add this config as functioning
                configs.append([filename[:-5], config])
                new_config = False
                print((_("Using config file '%s'.") % filename))
            except:
                print((_("'%s' is not a valid config file.") % filename))

    # no previous configuration could be found so let's create a new one
    if new_config:
        config = ConfigObj(os.path.join(conf_dir, _('standard') + '.conf'), {'create_empty': True, 'file_error': False, 'configspec': conf_specs})
        # next line fixes a problem with creating empty strings in default values for configobj
        config['device_mac'] = ''
        config.validate(vdt, copy=True)
        # write it in a secure manner
        config.write()
        configs.append([_('standard'), config])
        # we can't log these messages since logging is not yet configured, so we just print it to stdout
    print((_("Creating new configuration.")))
    print((_("Using config file '%s'.") % _('standard')))

    # now start the proximity detection for each configuration
    for config in configs:
        p = Proximity(config[1])
        p.start()
        config.append(p)

    configs.sort()
    # the idea behind 'configs' is an array containing the name, the configobj and the proximity object
    pGui = ProximityGUI(configs, new_config)

    # make GTK threadable
    gtk.gdk.threads_init()

    # aaaaand action!
    gtk.main()
