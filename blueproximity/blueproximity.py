#!/usr/bin/env python
# coding: utf-8

# system includes
import os
import sys
import time
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
