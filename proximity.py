# requires bluetooth utils like hcitool to run

import os
import time
import threading
import gobject
import signal

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

class ProximityGUI:
    def __init__(self,proximityObject):
        #Set the Glade file
        self.gladefile = "proximity.glade"  
        self.wTree = gtk.glade.XML(self.gladefile) 

        #Create our dictionay and connect it
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
        self.readSettings()

    def readSettings(self):
        self.wTree.get_widget("entryMAC").set_text(self.proxi.dev_mac)
        self.wTree.get_widget("hscaleLockDist").set_value(-self.proxi.gone_limit)
        self.wTree.get_widget("hscaleLockDur").set_value(self.proxi.gone_duration)
        self.wTree.get_widget("hscaleUnlockDist").set_value(-self.proxi.active_limit)
        self.wTree.get_widget("hscaleUnlockDur").set_value(self.proxi.active_duration)

    def writeSettings(self):
        self.proxi.dev_mac = self.wTree.get_widget("entryMAC").get_text()
        self.proxi.gone_limit = -self.wTree.get_widget("hscaleLockDist").get_value()
        self.proxi.gone_duration = self.wTree.get_widget("hscaleLockDur").get_value()
        self.proxi.active_limit = -self.wTree.get_widget("hscaleUnlockDist").get_value()
        self.proxi.active_duration = self.wTree.get_widget("hscaleUnlockDur").get_value()

    def btnResetMinMax_clicked(self,widget):
        self.minDist = -255
        self.maxDist = 0

    def btnActivate_clicked(self,widget):
        self.writeSettings()

    def btnClose_clicked(self,widget):
        self.Close()

    def btnSelect_clicked(self,widget):
        selection = self.tree.get_selection()
        model, selection_iter = selection.get_selected()
        if (selection_iter):
            mac = self.model.get_value(selection_iter, 0)
            self.wTree.get_widget("entryMAC").set_text(mac)
        
    def btnScan_clicked(self,widget):
        # scan the area for bluetooth devices and show the results
        macs = self.proxi.get_device_list()
        self.model.clear()
        for mac in macs:
            self.model.append([mac[0], mac[1]])
        

    def Close(self):
        self.proxi.Stop = 1
        time.sleep(1)
        gtk.main_quit()

    def updateState(self):
        # update the display with newest values
        newVal = int(self.proxi.Dist)
        if newVal > self.minDist:
            self.minDist = newVal
        if newVal < self.maxDist:
            self.maxDist = newVal
        self.wTree.get_widget("labState").set_text("min: " + 
            str(-self.minDist) + " max: " + str(-self.maxDist) + " state: " + self.proxi.State)
        self.wTree.get_widget("hscaleAct").set_value(-newVal)
        self.timer = gobject.timeout_add(1000,self.updateState)


class Proximity (threading.Thread):
    def __init__(self,dev_mac,buffer_size,gone_duration,gone_limit,active_duration,active_limit):
        threading.Thread.__init__(self, name="WorkerThread")
        self.Dist = -255
        self.State = "gone"
        self.Simulate = False
        self.Stop = False
        self.pid = 0
        self.dev_mac = dev_mac
        self.ringbuffer_size = buffer_size
        self.ringbuffer = [-254] * self.ringbuffer_size
        self.ringbuffer_pos = 0
        self.gone_duration = gone_duration
        self.gone_limit = gone_limit
        self.active_duration = active_duration
        self.active_limit = active_limit
        self.ErrorMsg = "Initialized..."
    
    def get_device_list(self):
        # returns all active bluetooth devices found
        ret_tab = list()
        lines = os.popen("hcitool scan", "r").readlines()
        for line in lines:
            if line.startswith('\t'):
                ret_tab.append(line.strip('\t\n').split('\t'))
        return ret_tab

    def kill_connection(self,pid):
        # kills the rssi detection connection
        ret_val = os.popen("kill -2 " + str(pid), "r").readlines()
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
        args = ["rfcomm", "connect" ,"1", dev_mac, "7"]
        cmd = "/usr/bin/rfcomm"
        #print "debug: fuehre aus '" + cmd + "' mit args '" + str(args) + "'"
        self.pid = os.spawnv(os.P_NOWAIT, cmd, args)
        time.sleep(5)

    def run_cycle(self,dev_mac):
        # reads the distance and averages it over the ringbuffer
        self.ringbuffer_pos = (self.ringbuffer_pos + 1) % self.ringbuffer_size
        self.ringbuffer[self.ringbuffer_pos] = self.get_proximity_once(dev_mac)
        ret_val = 0
        for val in self.ringbuffer:
            ret_val = ret_val + val
        if self.ringbuffer[self.ringbuffer_pos] == -255:
            self.ErrorMsg = "No connection found, trying to establish one..."
            print "I can't find my master. Will try again..."
            self.pid = self.get_connection(dev_mac)
        return int(ret_val / self.ringbuffer_size)

    def go_active(self):
        print "The Doctor is in !"
        ret_val = os.popen("gnome-screensaver-command -d").readlines()

    def go_gone(self):
        print "The Doctor is out !"
        ret_val = os.popen("gnome-screensaver-command -a").readlines()

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
                    print "Detected distance atm: " + str(dist) + "; state is " + state
                self.State = state
                self.Dist = dist
                time.sleep(1)
            except KeyboardInterrupt:
                break
        if self.pid > 0:
            print 'Now stopping connection...'
            p.kill_connection(self.pid)

if __name__=='__main__':
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    p = Proximity("00:12:D1:8A:D7:8D",1,2,-4,1,-2)
    p.Simulate = True
    #print 'Now scanning surrounding devices (using hcitool)...'
    #print (p.get_device_list())
    #print 'Now starting connection to detect rssi values...'
    #p.get_connection("00:12:D1:8A:D7:8D")
    #print 'Started with PID ' + str(p.pid)
    p.start()
    pGui = ProximityGUI(p)
    gtk.gdk.threads_init()
    gtk.main()
    