#!/usr/bin/env python

# blueproximity
SW_VERSION = '1.2 svn'
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

import os
import time
import threading
import gobject
import signal
from configobj import ConfigObj
from validate import Validator
import bluetooth
import _bluetooth as bluez


try:
    import pygtk
    pygtk.require("2.0")
except:
    sys.exit(1)

try:
    import gtk
    import gtk.glade
except:
    sys.exit(1)

# Setup config file specs and defaults
conf_specs = [
    'device_mac=string(max=17,default="")',
    'device_channel=integer(1,30,default=7)',
    'lock_distance=integer(0,255,default=4)',
    'lock_duration=integer(0,255,default=2)',
    'unlock_distance=integer(0,255,default=2)',
    'unlock_duration=integer(0,255,default=1)',
    'lock_command=string(default=''gnome-screensaver-command -l'')',
    'unlock_command=string(default=''gnome-screensaver-command -d'')',
    'buffer_size=integer(1,255,default=1)'
    ]

# set this value to './' for svn version
# or to '/usr/share/blueproximity/' for packaged version
dist_path = './' 

class ProximityGUI:
    # this class represents the main configuration window and
    # updates the config file after changes made are saved
    def __init__(self,proximityObject,configobj,show_window_on_start):
        #Constructor sets up the GUI and reads the current config
        
        #This is to block events from firing a config write because we initialy set a value
        self.gone_live = False
        
        #Set the Glade file
        self.gladefile = dist_path + "proximity.glade"  
        self.wTree = gtk.glade.XML(self.gladefile) 

        #Create our dictionary and connect it
        dic = { "on_btnInfo_clicked" : self.aboutPressed,
            "on_btnClose_clicked" : self.btnClose_clicked,
            "on_btnScan_clicked" : self.btnScan_clicked,
            "on_btnSelect_clicked" : self.btnSelect_clicked,
            "on_btnResetMinMax_clicked" : self.btnResetMinMax_clicked,
            "on_settings_changed" : self.event_settings_changed,
            "on_MainWindow_destroy" : self.btnClose_clicked }
        self.wTree.signal_autoconnect(dic)

        #Get the Main Window, and connect the "destroy" event
        self.window = self.wTree.get_widget("MainWindow")
        if (self.window):
            self.window.connect("destroy", self.btnClose_clicked)
        self.window.set_icon(gtk.gdk.pixbuf_new_from_file(dist_path + "blueproximity_base.gif"))
        self.proxi = proximityObject
        self.minDist = -255
        self.maxDist = 0
        self.pauseMode = False
        self.timer = gobject.timeout_add(1000,self.updateState)
        self.lastMAC = ''

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
        self.config = configobj
        self.readSettings()
        
        if show_window_on_start:
            self.window.show()

        #Prepare icon
        self.icon = gtk.StatusIcon()
        self.icon.set_tooltip("BlueProximity starting...")
        self.icon.set_from_file(dist_path + "blueproximity_error.gif")
        
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

    def aboutPressed(self, widget, data = None):
        logo = gtk.gdk.pixbuf_new_from_file(dist_path + "blueproximity_base.gif")
        description = "Leave it - it's locked, come back - it's back too..."
        copyright = u"""Copyright \xa9 2007 Lars Friedrichs"""
        people = [
            u"Lars Friedrichs <LarsFriedrichs@gmx.de>",
            u"Tobias Jakobs"]
        about = gtk.AboutDialog()
        about.set_icon(logo)
        about.set_name("BlueProximity")
        about.set_version(SW_VERSION)
        about.set_copyright(copyright)
        about.set_comments(description)
        about.set_authors(people)
        about.set_logo(logo)
        #about.set_license(license)
        about.set_website("http://blueproximity.sourceforge.net")
        about.connect('response', lambda widget, response: widget.destroy())
        about.show()

    def pausePressed(self, widget, data = None):
        if self.pauseMode:
            self.pauseMode = False
            self.proxi.dev_mac = self.lastMAC
            self.proxi.Simulate = False
            self.icon.set_from_file(dist_path + "blueproximity_error.gif")
        else:
            self.pauseMode = True
            self.lastMAC = self.proxi.dev_mac
            self.proxi.dev_mac = ''
            self.proxi.Simulate = True
            self.proxi.kill_connection()

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

    def btnResetMinMax_clicked(self,widget, data = None):
        #Resets the values for the min/max viewer
        self.minDist = -255
        self.maxDist = 0

    def event_settings_changed(self,widget, data = None):
        #Don't react if we are still initializing (were we set the values)
        if self.gone_live:
            self.writeSettings()
        pass

    def btnClose_clicked(self,widget, data = None):
        self.Close()

    def btnSelect_clicked(self,widget, data = None):
        #Takes the selected entry in the mac/name table and enters its mac in the MAC field
        selection = self.tree.get_selection()
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
        
        
    def btnScan_clicked(self,widget, data = None):
        # scan the area for bluetooth devices and show the results
        watch = gtk.gdk.Cursor(gtk.gdk.WATCH)
        self.window.window.set_cursor(watch)
        self.model.clear()
        self.model.append(['...', 'Now scanning...'])
        gobject.idle_add(self.cb_btnScan_clicked)
        

    def Close(self):
        self.window.hide()
        self.proxi.Simulate = False

    def quit(self, widget, data = None):
        #try to close everything correctly
        self.icon.set_from_file(dist_path + 'blueproximity_attention.gif')
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
        if self.pauseMode:
            self.icon.set_from_file(dist_path + 'blueproximity_pause.gif')
            self.icon.set_tooltip('Pause Mode - not connected')
        else:
            if self.proxi.ErrorMsg == "No connection found, trying to establish one...":
                self.icon.set_from_file(dist_path + 'blueproximity_error.gif')
            else:
                if self.proxi.State != 'active':
                    self.icon.set_from_file(dist_path + 'blueproximity_nocon.gif')
                else:
                    if newVal < self.proxi.active_limit:
                        self.icon.set_from_file(dist_path + 'blueproximity_attention.gif')
                    else:
                        self.icon.set_from_file(dist_path + 'blueproximity_base.gif')
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
        self.sock = None
    
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

    def get_connection(self,dev_mac):
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
            self.sock.connect((dev_mac, self.config['device_channel']))
            #print str(_sock.getsockid())
        except:
            self.procid = 0
            pass

        # take some time to connect (only when using spawnv)
        #time.sleep(5)
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
            self.kill_connection()
            self.get_connection(dev_mac)
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
        self.kill_connection()

if __name__=='__main__':
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
    