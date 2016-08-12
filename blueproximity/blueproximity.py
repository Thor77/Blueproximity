#!/usr/bin/env python
# coding: utf-8

# system includes
import os
import sys
import time
import signal
import syslog

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
