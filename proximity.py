#!/usr/bin/env python

# blueproximity 0.99
# Add security to your desktop by automatically locking and unlocking 
# the screen when you and your phone leave/enter the desk. 
# Think of a proximity detector for your mobile phone via bluetooth.
# requires bluetooth utils like hcitool to run

# copyright by Lars Friedrichs <larsfriedrichs@gmx.de>
# this source is licensed under the GPL.
# I'm a big fan of talkback about how it performs!
# I'm also open to feature requests and notes on programming issues, I am no python master at all...
# ToDo List:
# - DONE:add config file support
# - add iconize function
# - add device scan for possible services
# - add usage of python native bluetooth lib
# - add expert configuration GUI


import os
import time
import threading
import gobject
import signal
from configobj import ConfigObj
from validate import Validator


try:
    import pygtk
    pygtk.require("2.0")
except:
    pass

try:
    import gtk
    import gtk.glade
except:
    sys.exit(1)

# Setup config file specs and defaults
conf_specs = [
    'device_mac=string(max=17,default=\'\')',
    'device_channel=integer(1,30,default=7)',
    'lock_distance=integer(0,255,default=4)',
    'lock_duration=integer(0,255,default=2)',
    'unlock_distance=integer(0,255,default=2)',
    'unlock_duration=integer(0,255,default=1)',
    'lock_command=string(default=''gnome-screensaver-command -a'')',
    'unlock_command=string(default=''gnome-screensaver-command -d'')',
    'buffer_size=integer(1,255,default=1)'
    ]

class ProximityGUI:
    # this class represents the main configuration window and
    # updates the config file after changes made are saved
    def __init__(self,proximityObject,configobj):
        #Constructor sets up the GUI and reads the current config
        
        #Set the Glade file
        self.gladefile = "proximity.glade"  
        self.wTree = gtk.glade.XML(self.gladefile) 

        #Create our dictionary and connect it
        dic = { "on_btnActivate_clicked" : self.btnActivate_clicked,
            "on_btnClose_clicked" : self.btnClose_clicked,
            "on_btnScan_clicked" : self.btnScan_clicked,
            "on_btnSelect_clicked" : self.btnSelect_clicked,
            "on_btnResetMinMax_clicked" : self.btnResetMinMax_clicked,
            "on_MainWindow_destroy" : self.Close }
        self.wTree.signal_autoconnect(dic)

        #Get the Main Window, and connect the "destroy" event
        self.window = self.wTree.get_widget("MainWindow")
        if (self.window):
            self.window.connect("destroy", self.Close)
        self.proxi = proximityObject
        self.minDist = -255
        self.maxDist = 0
        self.timer = gobject.timeout_add(1000,self.updateState)

        #Prepare the mac/name table
        self.model = gtk.ListStore(gobject.TYPE_STRING,gobject.TYPE_STRING)
        self.tree = self.wTree.get_widget("treeScanResult")
        self.tree.set_model(self.model)
        colLabel=gtk.TreeViewColumn('MAC', gtk.CellRendererText(), text=0)
        colLabel.set_resizable(True)
        colLabel.set_sort_column_id(0)
        self.tree.append_column(colLabel)
        colLabel=gtk.TreeViewColumn('Name', gtk.CellRendererText(), text=1)
        colLabel.set_resizable(True)
        colLabel.set_sort_column_id(1)
        self.tree.append_column(colLabel)
        
        #Show the current settings
        self.readSettings()
        self.config = configobj
        
        #Prepare icon
        self.window.hide()
        self.icon = gtk.StatusIcon()
        self.icon.set_tooltip("BlueProximity starting...")
        self.icon.set_from_file("blueproximity_error.gif")
        
        self.popupmenu = gtk.Menu()
        menuItem = gtk.ImageMenuItem(gtk.STOCK_EDIT)
        menuItem.connect('activate', self.showWindow)
        self.popupmenu.append(menuItem)
        menuItem = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        menuItem.connect('activate', self.quit, self.icon)
        self.popupmenu.append(menuItem)

        self.icon.connect('activate', self.showWindow)
        self.icon.connect('popup-menu', self.popupMenu, self.popupmenu)
        
        self.icon.set_visible(True)

    def popupMenu(self, widget, button, time, data = None):
        if button == 3:
            if data:
                data.show_all()
                data.popup(None, None, None, 3, time)
        pass

    def showWindow(self, widget, data = None):
        if self.window.get_property("visible"):
            self.Close()
        else:
            self.window.show()
            self.proxi.Simulate = True

    def readSettings(self):
        #Updates the controls to show the actual configuration of the running proximity
        self.wTree.get_widget("entryMAC").set_text(self.proxi.dev_mac)
        self.wTree.get_widget("hscaleLockDist").set_value(-self.proxi.gone_limit)
        self.wTree.get_widget("hscaleLockDur").set_value(self.proxi.gone_duration)
        self.wTree.get_widget("hscaleUnlockDist").set_value(-self.proxi.active_limit)
        self.wTree.get_widget("hscaleUnlockDur").set_value(self.proxi.active_duration)

    def writeSettings(self):
        #Updates the running proximity and the config file with the new settings from the controls
        self.proxi.dev_mac = self.wTree.get_widget("entryMAC").get_text()
        self.proxi.gone_limit = -self.wTree.get_widget("hscaleLockDist").get_value()
        self.proxi.gone_duration = self.wTree.get_widget("hscaleLockDur").get_value()
        self.proxi.active_limit = -self.wTree.get_widget("hscaleUnlockDist").get_value()
        self.proxi.active_duration = self.wTree.get_widget("hscaleUnlockDur").get_value()
        self.config['device_mac'] = str(self.proxi.dev_mac)
        self.config['lock_distance'] = int(-self.proxi.gone_limit)
        self.config['lock_duration'] = int(self.proxi.gone_duration)
        self.config['unlock_distance'] = int(-self.proxi.active_limit)
        self.config['unlock_duration'] = int(self.proxi.active_duration)
        self.config.write()

    def btnResetMinMax_clicked(self,widget):
        #Resets the values for the min/max viewer
        self.minDist = -255
        self.maxDist = 0

    def btnActivate_clicked(self,widget):
        self.writeSettings()

    def btnClose_clicked(self,widget):
        self.Close()

    def btnSelect_clicked(self,widget):
        #Takes the selected entry in the mac/name table and enters its mac in the MAC field
        selection = self.tree.get_selection()
        model, selection_iter = selection.get_selected()
        if (selection_iter):
            mac = self.model.get_value(selection_iter, 0)
            self.wTree.get_widget("entryMAC").set_text(mac)
        
    def btnScan_clicked(self,widget):
        # scan the area for bluetooth devices and show the results
        tmpMac = self.proxi.dev_mac
        self.proxi.dev_mac = ''
        self.proxi.kill_connection()
        macs = self.proxi.get_device_list()
        self.proxi.dev_mac = tmpMac
        self.model.clear()
        for mac in macs:
            self.model.append([mac[0], mac[1]])
        

    def Close(self):
        self.window.hide()
        self.proxi.Simulate = False

    def quit(self, widget, data = None):
        #try to close everything correctly
        self.icon.set_from_file('blueproximity_attention.gif')
        self.proxi.Stop = 1
        time.sleep(2)
        gtk.main_quit()

    def updateState(self):
        # update the display with newest measurement values
        newVal = int(self.proxi.Dist) # Values are negative!
        if newVal > self.minDist:
            self.minDist = newVal
        if newVal < self.maxDist:
            self.maxDist = newVal
        self.wTree.get_widget("labState").set_text("min: " + 
            str(-self.minDist) + " max: " + str(-self.maxDist) + " state: " + self.proxi.State)
        self.wTree.get_widget("hscaleAct").set_value(-newVal)
        
        #Update icon too
        if self.proxi.State != 'active':
            self.icon.set_from_file('blueproximity_nocon.gif')
        else:
            if newVal < self.proxi.active_limit:
                self.icon.set_from_file('blueproximity_attention.gif')
            else:
                self.icon.set_from_file('blueproximity_base.gif')
        if self.proxi.Simulate:
            simu = '\nSimulation Mode (locking disabled)'
        else:
            simu = ''
        self.icon.set_tooltip('Detected Distance: ' + str(-newVal) + "\nCurrent State: " + self.proxi.State + "\nStatus: " + self.proxi.ErrorMsg + simu)
        
        self.timer = gobject.timeout_add(1000,self.updateState)


class Proximity (threading.Thread):
    # this class does 'all the magic'
    def __init__(self,config):
        # setup our local variables
        threading.Thread.__init__(self, name="WorkerThread")
        self.config = config
        self.Dist = -255
        self.State = "gone"
        self.Simulate = False
        self.Stop = False
        self.procid = 0
        self.dev_mac = self.config['device_mac']
        self.ringbuffer_size = self.config['buffer_size']
        self.ringbuffer = [-254] * self.ringbuffer_size
        self.ringbuffer_pos = 0
        self.gone_duration = self.config['lock_duration']
        self.gone_limit = -self.config['lock_distance']
        self.active_duration = self.config['unlock_duration']
        self.active_limit = -self.config['unlock_distance']
        self.ErrorMsg = "Initialized..."
    
    def get_device_list(self):
        # returns all active bluetooth devices found
        ret_tab = list()
        lines = os.popen("hcitool scan", "r").readlines()
        for line in lines:
            if line.startswith('\t'):
                ret_tab.append(line.strip('\t\n').split('\t'))
        return ret_tab

    def kill_connection(self):
        # kills the rssi detection connection
        ret_val = os.popen("kill -2 " + str(self.procid), "r").readlines()
        self.procid = 0
        return ret_val

    def get_proximity_once(self,dev_mac):
        # returns all active bluetooth devices found
        ret_val = os.popen("hcitool rssi " + dev_mac + " 2>/dev/null").readlines()
        if ret_val == []:
            ret_val = -255
        else:
            ret_val = ret_val[0].split(':')[1].strip(' ')
        return int(ret_val)

    def get_connection(self,dev_mac):
        # fire up a connection
        # don't forget to set up your phone not to ask for a connection
        # (at least for this computer)
        args = ["rfcomm", "connect" ,"1", dev_mac, str(self.config['device_channel']), ">/dev/null"]
        cmd = "/usr/bin/rfcomm"
        self.procid = os.spawnv(os.P_NOWAIT, cmd, args)
        # take some time to connect
        time.sleep(5)
        return self.procid

    def run_cycle(self,dev_mac):
        # reads the distance and averages it over the ringbuffer
        self.ringbuffer_pos = (self.ringbuffer_pos + 1) % self.ringbuffer_size
        self.ringbuffer[self.ringbuffer_pos] = self.get_proximity_once(dev_mac)
        ret_val = 0
        for val in self.ringbuffer:
            ret_val = ret_val + val
        if self.ringbuffer[self.ringbuffer_pos] == -255:
            self.ErrorMsg = "No connection found, trying to establish one..."
            #print "I can't find my master. Will try again..."
            if self.procid != 0:
                self.kill_connection()
            self.procid = self.get_connection(dev_mac)
        return int(ret_val / self.ringbuffer_size)

    def go_active(self):
        #The Doctor is in
        ret_val = os.popen(self.config['unlock_command']).readlines()

    def go_gone(self):
        #The Doctor is out
        ret_val = os.popen(self.config['lock_command']).readlines()

    def run(self):
    # this is the main loop
        duration_count = 0
        state = "gone"
        while not self.Stop:
            #print "tick"
            try:
                if self.dev_mac != "":
                    self.ErrorMsg = "running..."
                    dist = self.run_cycle(self.dev_mac)
                else:
                    dist = -255
                    self.ErrorMsg = "No bluetooth device configured..."
                if state == "gone":
                    if dist>=self.active_limit:
                        duration_count = duration_count + 1
                        if duration_count >= self.active_duration:
                            state = "active"
                            duration_count = 0
                            if not self.Simulate:
                                self.go_active()
                    else:
                        duration_count = 0
                else:
                    if dist<=self.gone_limit:
                        duration_count = duration_count + 1
                        if duration_count >= self.gone_duration:
                            state = "gone"
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
        if self.procid != 0:
            #print 'Now stopping connection...'
            p.kill_connection()

if __name__=='__main__':
    # react on ^C
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    # read config if any
    config = ConfigObj(os.getenv('HOME') + '/.blueproximityrc',{'create_empty':True,'configspec':conf_specs})
    vdt = Validator()
    config.validate(vdt, copy=True)
    config.write()
    
    p = Proximity(config)
    p.start()
    pGui = ProximityGUI(p,config)

    # make GTK threadable 
    gtk.gdk.threads_init()
    gtk.main()
    