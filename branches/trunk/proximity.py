#!/usr/bin/env python
# coding: utf-8

# blueproximity
SW_VERSION = '1.2.4'
# Add security to your desktop by automatically locking and unlocking 
# the screen when you and your phone leave/enter the desk. 
# Think of a proximity detector for your mobile phone via bluetooth.
# requires external bluetooth util hcitool to run
# (which makes it unix only at this time)
# Needed python extensions:
#  ConfigObj (python-configobj)
#  PyGTK (python-gtk2, python-glade2)
#  Bluetooth (python-bluez)

# copyright by Lars Friedrichs <larsfriedrichs@gmx.de>
# this source is licensed under the GPL.
# I'm a big fan of talkback about how it performs!
# I'm also open to feature requests and notes on programming issues, I am no python master at all...
# ToDo List can be found on sourceforge
# follow http://blueproximity.sourceforge.net

APP_NAME="blueproximity"

## This value gives us the base directory for language files and icons.
# Set this value to './' for svn version
# or to '/usr/share/blueproximity/' for packaged version
dist_path = './' 


# system includes
import os
import sys
import time
import threading
import signal
import syslog
import locale


#Translation stuff
import gettext

#Get the local directory since we are not installing anything
local_path = dist_path + 'LANG/'
# Init the list of languages to support
langs = []
#Check the default locale
lc, encoding = locale.getdefaultlocale()
if (lc):
    #If we have a default, it's the first in the list
    langs = [lc]
    # Now lets get all of the supported languages on the system
language = os.environ.get('LANGUAGE', None)
if (language):
    """langage comes back something like en_CA:en_US:en_GB:en
    on linuxy systems, on Win32 it's nothing, so we need to
    split it up into a list"""
    langs += language.split(":")
"""Now add on to the back of the list the translations that we
know that we have, our defaults"""
langs += ["en"]

"""Now langs is a list of all of the languages that we are going
to try to use.  First we check the default, then what the system
told us, and finally the 'known' list"""

gettext.bindtextdomain(APP_NAME, local_path)
gettext.textdomain(APP_NAME)
# Get the language to use
lang = gettext.translation(APP_NAME, local_path, languages=langs, fallback = True)
"""Install the language, map _() (which we marked our
strings to translate with) to self.lang.gettext() which will
translate them."""
_ = lang.gettext    


# now the imports from external packages
try:
    import gobject
except:
    print _("The program cannot import the module gobject.")
    print _("Please make sure the GObject bindings for python are installed.")
    print _("e.g. with Ubuntu Linux, type")
    print _(" sudo apt-get install python-gobject")
    sys.exit(1)
try:
    from configobj import ConfigObj
    from validate import Validator
except:
    print _("The program cannot import the module ConfigObj or Validator.")
    print _("Please make sure the ConfigObject package for python is installed.")
    print _("e.g. with Ubuntu Linux, type")
    print _(" sudo apt-get install python-configobj")
    sys.exit(1)
IMPORT_BT=0
try:
    import bluetooth
    IMPORT_BT = IMPORT_BT+1
except:
    pass
try:
    import _bluetooth as bluez
    IMPORT_BT = IMPORT_BT+1
except:
    pass
try:
    import bluetooth._bluetooth as bluez
    IMPORT_BT = IMPORT_BT+1
except:
    pass
if (IMPORT_BT!=2):
    print _("The program cannot import the module bluetooth.")
    print _("Please make sure the bluetooth bindings for python as well as bluez are installed.")
    print _("e.g. with Ubuntu Linux, type")
    print _(" sudo apt-get install python-bluez")
    sys.exit(1)
try:
    import pygtk
    pygtk.require("2.0")
    import gtk
except:
    print _("The program cannot import the module pygtk.")
    print _("Please make sure the GTK2 bindings for python are installed.")
    print _("e.g. with Ubuntu Linux, type")
    print _(" sudo apt-get install python-gtk2")
    sys.exit(1)
try:
    import gtk.glade
except:
    print _("The program cannot import the module glade.")
    print _("Please make sure the Glade2 bindings for python are installed.")
    print _("e.g. with Ubuntu Linux, type")
    print _(" sudo apt-get install python-glade2")
    sys.exit(1)


## Setup config file specs and defaults
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
    

## The icon used at normal operation and in the info dialog.
icon_base = 'blueproximity_base.svg'
## The icon used at distances greater than the unlock distance.
icon_att = 'blueproximity_attention.svg'
## The icon used if no proximity is detected.
icon_away = 'blueproximity_nocon.svg'
## The icon used during connection processes and with connection errors.
icon_con = 'blueproximity_error.svg'
## The icon shown if we are in pause mode.
icon_pause = 'blueproximity_pause.svg'


## This class represents the main configuration window and
# updates the config file after changes made are saved
class ProximityGUI:

    ## Constructor sets up the GUI and reads the current config
    # @param proximityObject A proximity object representing the detection mechanism
    # @param configobj A ConfigObj object representing the configuration of the proximity object
    # @param show_window_on_start Set to True to show the config screen immediately after the start.
    # This is true if no prior config file has been detected (initial start).
    def __init__(self,proximityObject,configobj,show_window_on_start):
        
        #This is to block events from firing a config write because we initialy set a value
        self.gone_live = False
        
        #Set the Glade file
        self.gladefile = dist_path + "proximity.glade"  
        self.wTree = gtk.glade.XML(self.gladefile) 

        #Create our dictionary and connect it
        dic = { "on_btnInfo_clicked" : self.aboutPressed,
            "on_btnClose_clicked" : self.btnClose_clicked,
            "on_btnScan_clicked" : self.btnScan_clicked,
            "on_btnScanChannel_clicked" : self.btnScanChannel_clicked,
            "on_btnSelect_clicked" : self.btnSelect_clicked,
            "on_btnResetMinMax_clicked" : self.btnResetMinMax_clicked,
            "on_settings_changed" : self.event_settings_changed,
            "on_settings_changed_reconnect" : self.event_settings_changed_reconnect,
            "on_treeScanChannelResult_changed" : self.event_scanChannelResult_changed,
            "on_MainWindow_destroy" : self.btnClose_clicked }
        self.wTree.signal_autoconnect(dic)

        #Get the Main Window, and connect the "destroy" event
        self.window = self.wTree.get_widget("MainWindow")
        if (self.window):
            self.window.connect("delete_event", self.btnClose_clicked)
        self.window.set_icon(gtk.gdk.pixbuf_new_from_file(dist_path + icon_base))
        self.proxi = proximityObject
        self.minDist = -255
        self.maxDist = 0
        self.pauseMode = False
        self.lastMAC = ''
        self.scanningChannels = False

        #Prepare the mac/name table
        self.model = gtk.ListStore(gobject.TYPE_STRING,gobject.TYPE_STRING)
        self.tree = self.wTree.get_widget("treeScanResult")
        self.tree.set_model(self.model)
	self.tree.get_selection().set_mode(gtk.SELECTION_SINGLE)
        colLabel=gtk.TreeViewColumn(_('MAC'), gtk.CellRendererText(), text=0)
        colLabel.set_resizable(True)
        colLabel.set_sort_column_id(0)
        self.tree.append_column(colLabel)
        colLabel=gtk.TreeViewColumn(_('Name'), gtk.CellRendererText(), text=1)
        colLabel.set_resizable(True)
        colLabel.set_sort_column_id(1)
        self.tree.append_column(colLabel)
        
        #Prepare the channel/state table
        self.modelScan = gtk.ListStore(gobject.TYPE_STRING,gobject.TYPE_STRING)
        self.treeChan = self.wTree.get_widget("treeScanChannelResult")
        self.treeChan.set_model(self.modelScan)
        colLabel=gtk.TreeViewColumn(_('Channel'), gtk.CellRendererText(), text=0)
        colLabel.set_resizable(True)
        colLabel.set_sort_column_id(0)
        self.treeChan.append_column(colLabel)
        colLabel=gtk.TreeViewColumn(_('State'), gtk.CellRendererText(), text=1)
        colLabel.set_resizable(True)
        colLabel.set_sort_column_id(1)
        self.treeChan.append_column(colLabel)
        
        #Show the current settings
        self.config = configobj
        self.readSettings()
        self.timer = gobject.timeout_add(1000,self.updateState)
        self.timer2 = gobject.timeout_add(1000*self.config['proximity_interval'],self.proximityCommand)
        
        #Only show if we started unconfigured
        if show_window_on_start:
            self.window.show()

        #Prepare icon
        self.icon = gtk.StatusIcon()
        self.icon.set_tooltip(_("BlueProximity starting..."))
        self.icon.set_from_file(dist_path + icon_con)
        
        #Setup the popup menu and associated callbacks
        self.popupmenu = gtk.Menu()
        menuItem = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        menuItem.connect('activate', self.showWindow)
        self.popupmenu.append(menuItem)
        menuItem = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PAUSE)
        menuItem.connect('activate', self.pausePressed)
        self.popupmenu.append(menuItem)
        menuItem = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
        menuItem.connect('activate', self.aboutPressed)
        self.popupmenu.append(menuItem)
        menuItem = gtk.MenuItem()
        self.popupmenu.append(menuItem)
        menuItem = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        menuItem.connect('activate', self.quit)
        self.popupmenu.append(menuItem)

        self.icon.connect('activate', self.showWindow)
        self.icon.connect('popup-menu', self.popupMenu, self.popupmenu)
        
        self.icon.set_visible(True)
        
        #now the control may fire change events
        self.gone_live = True
        self.proxi.logger.log_line(_('started.'))

    ## Callback to show the pop-up menu if icon is right-clicked.
    def popupMenu(self, widget, button, time, data = None):
        if button == 3:
            if data:
                data.show_all()
                data.popup(None, None, None, 3, time)
        pass

    ## Callback to show and hide the config dialog.
    def showWindow(self, widget, data = None):
        if self.window.get_property("visible"):
            self.Close()
        else:
            self.window.show()
            self.proxi.Simulate = True

    ## Callback to create and show the info dialog.
    def aboutPressed(self, widget, data = None):
        logo = gtk.gdk.pixbuf_new_from_file(dist_path + icon_base)
        description = _("Leave it - it's locked, come back - it's back too...")
        copyright = u"""Copyright (c) 2007 Lars Friedrichs"""
        people = [
            u"Lars Friedrichs <LarsFriedrichs@gmx.de>",
            u"Tobias Jakobs",
            u"Zsolt Mazolt"]
        translators = """Translators:
   de Lars Friedrichs <LarsFriedrichs@gmx.de>
   en Lars Friedrichs <LarsFriedrichs@gmx.de>
   es César Palma <cesarpalma80@gmail.com>
   fa Ali Sattari <ali.sattari@gmail.com>
   it e633 <e633@users.sourceforge.net>
   Prosper <prosper.nl@gmail.com>
   ru Alexey Lubimov
   sv Jan Braunisch <x@r6.se>
   th Maythee Anegboonlap & pFz <null@llun.info>
Former translators:
   fr Claude <f5pbl@users.sourceforge.net>
   sv Alexander Jönsson <tp-sv@listor.tp-sv.se>
   sv Daniel Nylander <dnylander@users.sourceforge.net>
            """
        license = _("""
        BlueProximity is free software; you can redistribute it and/or modify it 
        under the terms of the GNU General Public License as published by the 
        Free Software Foundation; either version 2 of the License, or 
        (at your option) any later version.

        BlueProximity is distributed in the hope that it will be useful, but 
        WITHOUT ANY WARRANTY; without even the implied warranty of 
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  
        See the GNU General Public License for more details.

        You should have received a copy of the GNU General Public License 
        along with Envy; if not, write to the 

        Free Software Foundation, Inc., 
        59 Temple Place, Suite 330, 
        Boston, MA  02111-1307  USA
        """)
        about = gtk.AboutDialog()
        about.set_icon(logo)
        about.set_name("BlueProximity")
        about.set_version(SW_VERSION)
        about.set_copyright(copyright)
        about.set_comments(description)
        about.set_authors(people)
        about.set_logo(logo)
        about.set_license(license)
        about.set_website("http://blueproximity.sourceforge.net")
        about.set_translator_credits(translators)
        about.connect('response', lambda widget, response: widget.destroy())
        about.show()

    ## Callback to activate and deactivate pause mode.
    # This is actually done by removing the proximity object'smac address.
    def pausePressed(self, widget, data = None):
        if self.pauseMode:
            self.pauseMode = False
            self.proxi.dev_mac = self.lastMAC
            self.proxi.Simulate = False
            self.icon.set_from_file(dist_path + icon_con)
        else:
            self.pauseMode = True
            self.lastMAC = self.proxi.dev_mac
            self.proxi.dev_mac = ''
            self.proxi.Simulate = True
            self.proxi.kill_connection()


    ## helper function to set a ComboBox's value to value if that exists in the Combo's list
    # The value is not changed if the new value is not member of the list.
    # @param widget a gtkComboBox object
    # @param value the value the gtkComboBox should be set to.    
    def setComboValue(self, widget, value):
        model = widget.get_model()
        for row in model:
            if row[0] == value:
                widget.set_active_iter(row.iter)
                break
        

    ## helper function to get a ComboBox's value
    def getComboValue(self, widget):
        model = widget.get_model()
        iter = widget.get_active_iter()
        return model.get_value(iter, 0)

    ## Reads the config settings and sets all GUI components accordingly.
    def readSettings(self):
        #Updates the controls to show the actual configuration of the running proximity
        self.wTree.get_widget("entryMAC").set_text(self.proxi.dev_mac)
        self.wTree.get_widget("entryChannel").set_value(self.proxi.dev_channel)
        self.wTree.get_widget("hscaleLockDist").set_value(-self.proxi.gone_limit)
        self.wTree.get_widget("hscaleLockDur").set_value(self.proxi.gone_duration)
        self.wTree.get_widget("hscaleUnlockDist").set_value(-self.proxi.active_limit)
        self.wTree.get_widget("hscaleUnlockDur").set_value(self.proxi.active_duration)
        self.wTree.get_widget("comboLock").child.set_text(self.config['lock_command'])
        self.wTree.get_widget("comboUnlock").child.set_text(self.config['unlock_command'])
        self.wTree.get_widget("comboProxi").child.set_text(self.config['proximity_command'])
        self.wTree.get_widget("hscaleProxi").set_value(self.config['proximity_interval'])
        self.wTree.get_widget("checkSyslog").set_active(self.config['log_to_syslog'])
        self.setComboValue(self.wTree.get_widget("comboFacility"), self.config['log_syslog_facility'])
        self.wTree.get_widget("checkFile").set_active(self.config['log_to_file'])
        self.wTree.get_widget("entryFile").set_text(self.config['log_filelog_filename'])

    ## Reads the current settings from the GUI and stores them in the configobj object.
    def writeSettings(self):
        #Updates the running proximity and the config file with the new settings from the controls
        self.proxi.dev_mac = self.wTree.get_widget("entryMAC").get_text()
        self.proxi.dev_channel = int(self.wTree.get_widget("entryChannel").get_value())
        self.proxi.gone_limit = -self.wTree.get_widget("hscaleLockDist").get_value()
        self.proxi.gone_duration = self.wTree.get_widget("hscaleLockDur").get_value()
        self.proxi.active_limit = -self.wTree.get_widget("hscaleUnlockDist").get_value()
        self.proxi.active_duration = self.wTree.get_widget("hscaleUnlockDur").get_value()
        self.config['device_mac'] = str(self.proxi.dev_mac)
        self.config['device_channel'] = str(self.proxi.dev_channel)
        self.config['lock_distance'] = int(-self.proxi.gone_limit)
        self.config['lock_duration'] = int(self.proxi.gone_duration)
        self.config['unlock_distance'] = int(-self.proxi.active_limit)
        self.config['unlock_duration'] = int(self.proxi.active_duration)
        self.config['lock_command'] = self.wTree.get_widget('comboLock').child.get_text()
        self.config['unlock_command'] = str(self.wTree.get_widget('comboUnlock').child.get_text())
        self.config['proximity_command'] = str(self.wTree.get_widget('comboProxi').child.get_text())
        self.config['proximity_interval'] = int(self.wTree.get_widget('hscaleProxi').get_value())
        self.config['log_to_syslog'] = self.wTree.get_widget("checkSyslog").get_active()
        self.config['log_syslog_facility'] = str(self.getComboValue(self.wTree.get_widget("comboFacility")))
        self.config['log_to_file'] = self.wTree.get_widget("checkFile").get_active()
        self.config['log_filelog_filename'] = str(self.wTree.get_widget("entryFile").get_text())
        self.proxi.logger.configureFromConfig(self.config)
        self.config.write()

    ## Callback for resetting the values for the min/max viewer.
    def btnResetMinMax_clicked(self,widget, data = None):
        self.minDist = -255
        self.maxDist = 0

    ## Callback called by almost all GUI elements if their values are changed.
    # We don't react if we are still initializing (self.gone_live==False)
    # because setting the values of the elements would already fire their change events.
    # @see gone_live
    def event_settings_changed(self,widget, data = None):
        if self.gone_live:
            self.writeSettings()
        pass

    ## Callback called by certain GUI elements if their values are changed.
    # We don't react if we are still initializing (self.gone_live==False)
    # because setting the values of the elements would already fire their change events.
    # But in any case we kill a possibly existing connection. 
    # Changing the rfcomm channel e.g. fires this event instead of event_settings_changed.
    # @see event_settings_changed
    def event_settings_changed_reconnect(self,widget, data = None):
        self.proxi.kill_connection()
        if self.gone_live:
            self.writeSettings()
        pass

    def event_scanChannelResult_changed(self,widget, data = None):
        # Put selected channel in channel entry field
        selection = self.wTree.get_widget("treeScanChannelResult").get_selection()
        (model, iter) = selection.get_selected()
        value = model.get_value(iter, 0)
        self.wTree.get_widget("entryChannel").set_value(int(value))

    def btnClose_clicked(self,widget, data = None):
        self.Close()
        return 1

    def btnSelect_clicked(self,widget, data = None):
        #Takes the selected entry in the mac/name table and enters its mac in the MAC field
        selection = self.tree.get_selection()
	selection.set_mode(gtk.SELECTION_SINGLE)
        model, selection_iter = selection.get_selected()
        if (selection_iter):
            mac = self.model.get_value(selection_iter, 0)
            self.wTree.get_widget("entryMAC").set_text(mac)
        
    def cb_btnScan_clicked(self):
        #Idle callback to show the watch cursor while scanning (HIG)
        tmpMac = self.proxi.dev_mac
        self.proxi.dev_mac = ''
        self.proxi.kill_connection()
        macs = self.proxi.get_device_list()
        self.proxi.dev_mac = tmpMac
        self.model.clear()
        for mac in macs:
            self.model.append([mac[0], mac[1]])
        self.window.window.set_cursor(None)
        
        
    def btnScanChannel_clicked(self,widget, data = None):
        # scan the selected device for possibly usable channels
        if self.scanningChannels:
            self.wTree.get_widget("labelBtnScanChannel").set_label(_("Sca_n channels on device"))
            self.wTree.get_widget("channelScanWindow").hide_all()
            self.scanningChannels = False
            self.scanner.doStop()
        else:
            mac = self.proxi.dev_mac
            if self.pauseMode:
                mac = self.lastMAC
                was_paused = True
            else:
                self.pausePressed(None)
                was_paused = False
            self.wTree.get_widget("labelBtnScanChannel").set_label(_("Stop sca_nning"))
            self.wTree.get_widget("channelScanWindow").show_all()
            self.scanningChannels = True
            dialog = gtk.MessageDialog(message_format=_("The scanning process tries to connect to each of the 30 possible ports. This will take some time and you should watch your bluetooth device for any actions to be taken. If possible click on accept/connect. If you are asked for a pin your device was not paired properly before, see the manual on how to fix this."),buttons=gtk.BUTTONS_OK)
            dialog.connect("response", lambda x,y: dialog.destroy())
            dialog.run()
            self.scanner = ScanDevice(mac,self.modelScan,was_paused,self.btnScanChannel_done)
        return 0
    
    def btnScanChannel_done(self,was_paused):
        self.wTree.get_widget("labelBtnScanChannel").set_label(_("Sca_n channels on device"))
        self.scanningChannels = False
        if not was_paused:
            self.pausePressed(None)
            self.proxi.Simulate = True

    def btnScan_clicked(self,widget, data = None):
        # scan the area for bluetooth devices and show the results
        watch = gtk.gdk.Cursor(gtk.gdk.WATCH)
        self.window.window.set_cursor(watch)
        self.model.clear()
        self.model.append(['...', _('Now scanning...')])
        gobject.idle_add(self.cb_btnScan_clicked)
        

    def Close(self):
        self.window.hide()
        self.proxi.Simulate = False

    def quit(self, widget, data = None):
        #try to close everything correctly
        self.icon.set_from_file(dist_path + icon_att)
        self.proxi.logger.log_line(_('stopped.'))
        self.proxi.Stop = 1
        time.sleep(2)
        gtk.main_quit()

    def updateState(self):
        # update the display with newest measurement values (once per second)
        newVal = int(self.proxi.Dist) # Values are negative!
        if newVal > self.minDist:
            self.minDist = newVal
        if newVal < self.maxDist:
            self.maxDist = newVal
        self.wTree.get_widget("labState").set_text(_("min: ") + 
            str(-self.minDist) + _(" max: ") + str(-self.maxDist) + _(" state: ") + self.proxi.State)
        self.wTree.get_widget("hscaleAct").set_value(-newVal)
        
        #Update icon too
        if self.pauseMode:
            self.icon.set_from_file(dist_path + icon_pause)
            self.icon.set_tooltip(_('Pause Mode - not connected'))
        else:
            if self.proxi.ErrorMsg == "No connection found, trying to establish one...":
                self.icon.set_from_file(dist_path + icon_con)
            else:
                if self.proxi.State != _('active'):
                    self.icon.set_from_file(dist_path + icon_away)
                else:
                    if newVal < self.proxi.active_limit:
                        self.icon.set_from_file(dist_path + icon_att)
                    else:
                        self.icon.set_from_file(dist_path + icon_base)
            if self.proxi.Simulate:
                simu = _('\nSimulation Mode (locking disabled)')
            else:
                simu = ''
            self.icon.set_tooltip(_('Detected Distance: ') + str(-newVal) + _("\nCurrent State: ") + self.proxi.State + _("\nStatus: ") + self.proxi.ErrorMsg + simu)
        
        self.timer = gobject.timeout_add(1000,self.updateState)
        
    def proximityCommand(self):
        #This is the proximity command callback called asynchronously as the updateState above
        if self.proxi.State == _('active') and not self.proxi.Simulate:
            ret_val = os.popen(self.config['proximity_command']).readlines()
        self.timer2 = gobject.timeout_add(1000*self.config['proximity_interval'],self.proximityCommand)


## This class creates all logging information in the desired form.
# We may log to syslog with a given syslog facility, while the severety is always info.
# We may also log a simple file.
class Logger:
    ## Constructor does nothing special.
    def __init__(self):
        self.disable_syslogging()
        self.disable_filelogging()
        
    ## helper function to convert a string (given by a ComboBox) to the corresponding
    # syslog module facility constant.
    # @param facility One of the 8 "localX" facilities or "user".
    def getFacilityFromString(self, facility):
        #Returns the correct constant value for the given facility
        dict = {
            "local0" : syslog.LOG_LOCAL0,
            "local1" : syslog.LOG_LOCAL1,
            "local2" : syslog.LOG_LOCAL2,
            "local3" : syslog.LOG_LOCAL3,
            "local4" : syslog.LOG_LOCAL4,
            "local5" : syslog.LOG_LOCAL5,
            "local6" : syslog.LOG_LOCAL6,
            "local7" : syslog.LOG_LOCAL7,
            "user" : syslog.LOG_USER
        }
        return dict[facility]

    ## Activates the logging to the syslog server.
    def enable_syslogging(self, facility):
        self.syslog_facility = self.getFacilityFromString(facility)
        syslog.openlog('blueproximity',syslog.LOG_PID)
        self.syslogging = True
        
    ## Deactivates the logging to the syslog server.
    def disable_syslogging(self):
        self.syslogging = False
        self.syslog_facility = None
        
    def enable_filelogging(self, filename):
        self.filename = filename
        try:
            #let's append
            self.flog = file(filename,'a')
            self.filelogging = True
        except:
            try:
                #did not work, then try to create file (is this really needed or does python know another attribute to file()?
                self.flog = file(filename,'w')
                self.filelogging = True
            except:
                print _("Could not open '") + filename +  _("' for writing.")
                self.disable_filelogging

    def disable_filelogging(self):
        try:
            self.flog.close()
        except:
            pass
        self.filelogging = False
        self.filename = ''

    def log_line(self, line):
        if self.syslogging:
            syslog.syslog(self.syslog_facility | syslog.LOG_NOTICE, line)
        if self.filelogging:
            try:
                self.flog.write( time.ctime() + " blueproximity: " + line + "\n")
                self.flog.flush()
            except:
                self.disable_filelogging()
    
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

## ScanDevice is a helper class used for scanning for open rfcomm channels
# on a given device. It uses asynchronous calls via gobject.timeout_add to
# not block the main process. It updates a given model after every scanned port
# and calls a callback function after finishing the scanning process.
class ScanDevice():
    ## Constructor which sets up and immediately starts the scanning process.
    # Note that the bluetooth device should not be connected while scanning occurs.
    # @param device_mac MAC address of the bluetooth device to be scanned.
    # @param was_paused A parameter to be passed to the finishing callback function.
    # This is to automatically put the GUI in simulation mode if it has been before scanning. (dirty hack)
    # @param callback A callback function to be called after scanning has been done. 
    # It takes one parameter which is preset by the was_paused parameter.
    def __init__(self,device_mac,model,was_paused,callback):
        self.mac = device_mac
        self.model = model
        self.stopIt = False
        self.port = 1
        self.timer = gobject.timeout_add(500,self.runStep)
        self.model.clear()
        self.was_paused = was_paused
        self.callback = callback

    def scanPortResult(self,port):
    # here we scan exactly one port and give a textual result
        _sock = bluez.btsocket()
        sock = bluetooth.BluetoothSocket( bluetooth.RFCOMM , _sock )
        try:
            sock.connect((self.mac, port))
            sock.close
            return _("usable")
        except:
            return _("closed or denied")


    def runStep(self):
    # here the scanning of all ports is done
        self.model.append([str(self.port), self.scanPortResult(self.port)])
        self.port = self.port + 1
        if not self.port > 30 and not self.stopIt:
            self.timer = gobject.timeout_add(500,self.runStep)
        else:
            self.callback(self.was_paused)

    def doStop(self):
        self.stopIt = True


## This class does 'all the magic' like regular device detection and decision making
# whether a device is known as present or away. Here is where all the bluetooth specific
# part takes place. It is build to be run a a seperate thread and would run perfectly without any GUI.
# Please note that the present-command is issued by the GUI whereas the locking and unlocking
# is called by this class. This is inconsitent and to be changed in a future release.
class Proximity (threading.Thread):
    ## Constructor to setup our local variables and initialize threading.
    # @param config a ConfigObj object that stores all our settings
    def __init__(self,config):
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
    
    def get_device_list(self):
        # returns all active bluetooth devices found
        ret_tab = list()
#        lines = os.popen("hcitool scan", "r").readlines()
#        for line in lines:
#            if line.startswith('\t'):
#                ret_tab.append(line.strip('\t\n').split('\t'))
        nearby_devices = bluetooth.discover_devices()
        for bdaddr in nearby_devices:
            ret_tab.append([str(bdaddr),str(bluetooth.lookup_name( bdaddr ))])
        return ret_tab

    def kill_connection(self):
        # kills the rssi detection connection
        #ret_val = os.popen("kill -2 " + str(self.procid), "r").readlines()
        #self.procid = 0
        if self.sock != None:
            self.sock.close()
        self.sock = None
        return 0 #ret_val if popen used

    def get_proximity_by_mac(self,dev_mac):
        sock = bluez.hci_open_dev(dev_id)
        old_filter = sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)

        # perform a device inquiry on bluetooth device #0
        # The inquiry should last 8 * 1.28 = 10.24 seconds
        # before the inquiry is performed, bluez should flush its cache of
        # previously discovered devices
        flt = bluez.hci_filter_new()
        bluez.hci_filter_all_events(flt)
        bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
        sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, flt )

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
                    addr = bluez.ba2str( pkt[1+6*i:1+6*i+6] )
                    rssi = struct.unpack("b", pkt[1+13*nrsp+i])[0]
                    results.append( ( addr, rssi ) )
                    print "[%s] RSSI: [%d]" % (addr, rssi)
            elif event == bluez.EVT_INQUIRY_COMPLETE:
                done = True
            elif event == bluez.EVT_CMD_STATUS:
                status, ncmd, opcode = struct.unpack("BBH", pkt[3:7])
                if status != 0:
                    print "uh oh..."
                    printpacket(pkt[3:7])
                    done = True
            else:
                print "unrecognized packet type 0x%02x" % ptype


        # restore old filter
        sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )

        sock.close()
        return results


    def get_proximity_once(self,dev_mac):
        # returns all active bluetooth devices found
        # this should also be removed but I still have to find a way to read the rssi value from python
        ret_val = os.popen("hcitool rssi " + dev_mac + " 2>/dev/null").readlines()
        if ret_val == []:
            ret_val = -255
        else:
            ret_val = ret_val[0].split(':')[1].strip(' ')
        return int(ret_val)

    def get_connection(self,dev_mac,dev_channel):
        # fire up a connection
        # don't forget to set up your phone not to ask for a connection
        # (at least for this computer)
        #args = ["rfcomm", "connect" ,"1", dev_mac, str(self.config['device_channel']), ">/dev/null"]
        #cmd = "/usr/bin/rfcomm"
        #self.procid = os.spawnv(os.P_NOWAIT, cmd, args)
        try:
            self.procid = 1
            _sock = bluez.btsocket()
            self.sock = bluetooth.BluetoothSocket( bluetooth.RFCOMM , _sock )
            self.sock.connect((dev_mac, dev_channel))
            #print str(_sock.getsockid())
        except:
            self.procid = 0
            pass

        # take some time to connect (only when using spawnv)
        #time.sleep(5)
        return self.procid

    def run_cycle(self,dev_mac,dev_channel):
        # reads the distance and averages it over the ringbuffer
        self.ringbuffer_pos = (self.ringbuffer_pos + 1) % self.ringbuffer_size
        self.ringbuffer[self.ringbuffer_pos] = self.get_proximity_once(dev_mac)
        ret_val = 0
        for val in self.ringbuffer:
            ret_val = ret_val + val
        if self.ringbuffer[self.ringbuffer_pos] == -255:
            self.ErrorMsg = _("No connection found, trying to establish one...")
            #print "I can't find my master. Will try again..."
            self.kill_connection()
            self.get_connection(dev_mac,dev_channel)
        return int(ret_val / self.ringbuffer_size)

    def go_active(self):
        #The Doctor is in
        if self.ignoreFirstTransition:
            self.ignoreFirstTransition = False
        else:
            self.logger.log_line(_('screen is unlocked'))
            ret_val = os.popen(self.config['unlock_command']).readlines()

    def go_gone(self):
        #The Doctor is out
        if self.ignoreFirstTransition:
            self.ignoreFirstTransition = False
        else:
            self.logger.log_line(_('screen is locked'))
            ret_val = os.popen(self.config['lock_command']).readlines()

    def run(self):
    # this is the main loop
        duration_count = 0
        state = _("gone")
        while not self.Stop:
            #print "tick"
            try:
                if self.dev_mac != "":
                    self.ErrorMsg = _("running...")
                    dist = self.run_cycle(self.dev_mac,self.dev_channel)
                else:
                    dist = -255
                    self.ErrorMsg = "No bluetooth device configured..."
                if state == _("gone"):
                    if dist>=self.active_limit:
                        duration_count = duration_count + 1
                        if duration_count >= self.active_duration:
                            state = _("active")
                            duration_count = 0
                            if not self.Simulate:
                                self.go_active()
                    else:
                        duration_count = 0
                else:
                    if dist<=self.gone_limit:
                        duration_count = duration_count + 1
                        if duration_count >= self.gone_duration:
                            state = _("gone")
                            duration_count = 0
                            if not self.Simulate:
                                self.go_gone()
                    else:
                        duration_count = 0                    
                if dist != self.Dist or state != self.State:
                    #print "Detected distance atm: " + str(dist) + "; state is " + state
                    pass
                self.State = state
                self.Dist = dist
                time.sleep(1)
            except KeyboardInterrupt:
                break
        self.kill_connection()


if __name__=='__main__':
    gtk.glade.bindtextdomain(APP_NAME, local_path)
    gtk.glade.textdomain(APP_NAME)

    
    # react on ^C
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    # read config if any
    new_config = False
    try:
        config = ConfigObj(os.getenv('HOME') + '/.blueproximityrc',{'create_empty':False,'file_error':True,'configspec':conf_specs})
    except:
        new_config = True
    if new_config:
        config = ConfigObj(os.getenv('HOME') + '/.blueproximityrc',{'create_empty':True,'file_error':False,'configspec':conf_specs})
        # next line fixes a problem with creating empty strings in default values for configobj
        config['device_mac'] = ''
    vdt = Validator()
    config.validate(vdt, copy=True)
    config.write()
    
    p = Proximity(config)
    p.start()
    pGui = ProximityGUI(p,config,new_config)

    # make GTK threadable 
    gtk.gdk.threads_init()
    gtk.main()
    
