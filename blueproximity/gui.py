# coding: utf-8


class ProximityGUI (object):
    '''
    Main configuration window
    '''

    def __init__(self, configs, show_window_on_start):
        '''
        Set up GUI and read current config

        @param configs A list of lists of name, ConfigObj object, proximity object
        @param show_window_on_start Set to True to show the config screen immediately after the start
        '''

        # This is to block events from firing a config write because we initialy set a value
        self.gone_live = False

        # Set the Glade file
        self.gladefile = dist_path + "proximity.glade"
        self.wTree = gtk.glade.XML(self.gladefile)

        # Create our dictionary and connect it
        dic = {
            "on_btnInfo_clicked": self.aboutPressed,
            "on_btnClose_clicked": self.btnClose_clicked,
            "on_btnNew_clicked": self.btnNew_clicked,
            "on_btnDelete_clicked": self.btnDelete_clicked,
            "on_btnRename_clicked": self.btnRename_clicked,
            "on_comboConfig_changed": self.comboConfig_changed,
            "on_btnScan_clicked": self.btnScan_clicked,
            "on_btnScanChannel_clicked": self.btnScanChannel_clicked,
            "on_btnSelect_clicked": self.btnSelect_clicked,
            "on_btnResetMinMax_clicked": self.btnResetMinMax_clicked,
            "on_settings_changed": self.event_settings_changed,
            "on_settings_changed_reconnect": self.event_settings_changed_reconnect,
            "on_treeScanChannelResult_changed": self.event_scanChannelResult_changed,
            "on_btnDlgNewDo_clicked": self.dlgNewDo_clicked,
            "on_btnDlgNewCancel_clicked": self.dlgNewCancel_clicked,
            "on_btnDlgRenameDo_clicked": self.dlgRenameDo_clicked,
            "on_btnDlgRenameCancel_clicked": self.dlgRenameCancel_clicked,
            "on_MainWindow_destroy": self.btnClose_clicked
        }
        self.wTree.signal_autoconnect(dic)

        # Get the Main Window, and connect the "destroy" event
        self.window = self.wTree.get_widget("MainWindow")
        if (self.window):
            self.window.connect("delete_event", self.btnClose_clicked)
        self.window.set_icon(gtk.gdk.pixbuf_new_from_file(dist_path + icon_base))
        self.proxi = configs[0][2]
        self.minDist = -255
        self.maxDist = 0
        self.pauseMode = False
        self.lastMAC = ''
        self.scanningChannels = False

        # Get the New Config Window, and connect the "destroy" event
        self.windowNew = self.wTree.get_widget("createNewWindow")
        if (self.windowNew):
            self.windowNew.connect("delete_event", self.dlgNewCancel_clicked)

        # Get the Rename Config Window, and connect the "destroy" event
        self.windowRename = self.wTree.get_widget("renameWindow")
        if self.windowRename:
            self.windowRename.connect("delete_event", self.dlgRenameCancel_clicked)

        # Prepare the mac/name table
        self.model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.tree = self.wTree.get_widget("treeScanResult")
        self.tree.set_model(self.model)
        self.tree.get_selection().set_mode(gtk.SELECTION_SINGLE)
        colLabel = gtk.TreeViewColumn(_('MAC'), gtk.CellRendererText(), text=0)
        colLabel.set_resizable(True)
        colLabel.set_sort_column_id(0)
        self.tree.append_column(colLabel)
        colLabel = gtk.TreeViewColumn(_('Name'), gtk.CellRendererText(), text=1)
        colLabel.set_resizable(True)
        colLabel.set_sort_column_id(1)
        self.tree.append_column(colLabel)

        # Prepare the channel/state table
        self.modelScan = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.treeChan = self.wTree.get_widget("treeScanChannelResult")
        self.treeChan.set_model(self.modelScan)
        colLabel = gtk.TreeViewColumn(_('Channel'), gtk.CellRendererText(), text=0)
        colLabel.set_resizable(True)
        colLabel.set_sort_column_id(0)
        self.treeChan.append_column(colLabel)
        colLabel = gtk.TreeViewColumn(_('State'), gtk.CellRendererText(), text=1)
        colLabel.set_resizable(True)
        colLabel.set_sort_column_id(1)
        self.treeChan.append_column(colLabel)

        # Show the current settings
        self.configs = configs
        self.configname = configs[0][0]
        self.config = configs[0][1]
        self.fillConfigCombo()
        self.readSettings()
        # this is the gui timer
        self.timer = gobject.timeout_add(1000, self.updateState)
        # fixme: this will execute the proximity command at the given interval - is now not working
        self.timer2 = gobject.timeout_add(1000*self.config['proximity_interval'], self.proximityCommand)


        # Only show if we started unconfigured
        if show_window_on_start:
            self.window.show()

        # Prepare icon
        self.icon = gtk.StatusIcon()
        self.icon.set_tooltip(_("BlueProximity starting..."))
        self.icon.set_from_file(dist_path + icon_con)

        # Setup the popup menu and associated callbacks
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

        # now the control may fire change events
        self.gone_live = True
        # log start in all config files
        for config in self.configs:
            config[2].logger.log_line(_('started.'))

    def dlgRenameCancel_clicked(self, widget, data=None):
        '''
        Callback to just close and not destroy the rename config window
        '''
        self.windowRename.hide()
        return 1

    def dlgRenameDo_clicked(self, widget, data=None):
        '''
        Callback to rename a config file.
        '''
        newconfig = self.wTree.get_widget("entryRenameName").get_text()
        # check if something has been entered
        if (newconfig == ''):
            dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, _("You must enter a name for the configuration."))
            dlg.run()
            dlg.destroy()
            return 0
        # now check if that config already exists
        newname = os.path.join(os.getenv('HOME'), '.blueproximity', newconfig + ".conf")
        try:
            os.stat(newname)
            dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, _("A configuration file with the name '%s' already exists.") % newname)
            dlg.run()
            dlg.destroy()
            return 0
        except:
            pass
        config = None
        for conf in self.configs:
            if (conf[0] == self.configname):
                config = conf
        # change the path of the config file
        oldfile = self.config.filename
        self.config.filename = newname
        # save it under the new name
        self.config.write()
        # delete the old file
        try:
            os.remove(oldfile)
        except:
            print(_("The configfile '%s' could not be deleted.") % oldfile)
        # change the gui name
        self.configname = newconfig
        # update the configs array
        config[0] = newconfig
        # show changes
        self.fillConfigCombo()
        self.windowRename.hide()

    def dlgNewCancel_clicked(self, widget, data=None):
        '''
        Callback to just close and not destroy the new config window
        '''
        self.windowNew.hide()
        return 1

    def dlgNewDo_clicked(self, widget, data=None):
        '''
        Callback to create a config file.
        '''
        newconfig = self.wTree.get_widget("entryNewName").get_text()
        # check if something has been entered
        if (newconfig == ''):
            dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, _("You must enter a name for the new configuration."))
            dlg.run()
            dlg.destroy()
            return 0
        # now check if that config already exists
        newname = os.path.join(os.getenv('HOME'), '.blueproximity', newconfig + ".conf")
        try:
            os.stat(newname)
            dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, _("A configuration file with the name '%s' already exists.") % newname)
            dlg.run()
            dlg.destroy()
            return 0
        except:
            pass
        # then let's get it on...
        # create the new config
        newconf = ConfigObj(self.config.dict())
        newconf.filename = newname
        # and save it to the new name
        newconf.write()
        # create the according Proximity object
        p = Proximity(newconf)
        p.Simulate = True
        p.start()
        # fill that into our list of active configs
        self.configs.append([newconfig, newconf, p])
        # now refresh the gui to take account of our new config
        self.config = newconf
        self.configname = newconfig
        self.proxi = p
        self.readSettings()
        self.configs.sort()
        self.fillConfigCombo()
        # close the new config dialog
        self.windowNew.hide()

    def setSensitiveConfigManagement(self, activate):
        '''
        Helper function to enable or disable the change or creation of the config files
        This is called during non blockable functions that rely on the config not
        being changed over the process like scanning for devices or channels
        @param activate set to True to activate buttons, False to disable
        '''
        # get the widget
        combo = self.wTree.get_widget("comboConfig")
        combo.set_sensitive(activate)
        button = self.wTree.get_widget("btnNew")
        button.set_sensitive(activate)
        button = self.wTree.get_widget("btnRename")
        button.set_sensitive(activate)
        button = self.wTree.get_widget("btnDelete")
        button.set_sensitive(activate)

    def fillConfigCombo(self):
        '''
        Helper function to populate the list of configurations.
        '''
        # get the widget
        combo = self.wTree.get_widget("comboConfig")
        model = combo.get_model()
        combo.set_model(None)
        # delete the list
        model.clear()
        pos = 0
        activePos = -1
        # add all configurations we have, remember the index of the active one
        for conf in self.configs:
            model.append([conf[0]])
            if (conf[0] == self.configname):
                activePos = pos
            pos = pos + 1
        combo.set_model(model)
        # let the comboBox show the active config entry
        if (activePos != -1):
            combo.set_active(activePos)

    def comboConfig_changed(self, widget, data=None):
        '''
        Callback to select a different config file for editing.
        '''
        # get the widget
        combo = self.wTree.get_widget("comboConfig")
        model = combo.get_model()
        name = combo.get_active_text()
        # only continue if this is different to the former config
        if name != self.configname:
            newconf = None
            # let's find the new ConfigObj
            for conf in self.configs:
                if (name == conf[0]):
                    newconf = conf
            # if found set it as our active one and show it's settings in the GUI
            if newconf:
                self.config = newconf[1]
                self.configname = newconf[0]
                self.proxi = newconf[2]
                self.readSettings()

    def btnNew_clicked(self, widget, data=None):
        '''
        Callback to create a new config file for editing.
        '''
        # reset the entry widget
        self.wTree.get_widget("entryNewName").set_text('')
        self.windowNew.show()

    def btnDelete_clicked(self, widget, data=None):
        '''
        Callback to delete a config file.
        '''
        # never delete the last config
        if (len(self.configs) == 1):
            dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, _("The last configuration file cannot be deleted."))
            dlg.run()
            dlg.destroy()
            return 0
        # security question
        dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_YES_NO, _("Do you really want to delete the configuration '%s'.") % self.configname)
        retval = dlg.run()
        dlg.destroy()
        if (retval == gtk.RESPONSE_YES):
            # ok, now stop the detection for that config
            self.proxi.Stop = True
            # save the filename
            configfile = self.config.filename
            # rip it out of our configs array
            self.configs.remove([self.configname, self.config, self.proxi])
            # change active config to the next one
            self.configs.sort()
            self.configname = configs[0][0]
            self.config = configs[0][1]
            self.proxi = configs[0][2]
            # update gui
            self.readSettings()
            self.fillConfigCombo()
            # now delete the file on the disk
            try:
                os.remove(configfile)
            except:
                # should this be a GUI message?
                print(_("The configfile '%s' could not be deleted.") % configfile)

    def btnRename_clicked(self, widget, data=None):
        '''
        Callback to rename a config file.
        '''
        # set the entry widget
        self.wTree.get_widget("entryRenameName").set_text(self.configname)
        self.windowRename.show()

    def popupMenu(self, widget, button, time, data=None):
        '''
        Callback to show the pop-up menu if icon is right-clicked.
        '''
        if button == 3:
            if data:
                data.show_all()
                data.popup(None, None, None, 3, time)
        pass

    def showWindow(self, widget, data=None):
        '''
        Callback to show and hide the config dialog.
        '''
        if self.window.get_property("visible"):
            self.Close()
        else:
            self.window.show()
            for config in self.configs:
                config[2].Simulate = True

    def aboutPressed(self, widget, data=None):
        '''
        Callback to create and show the info dialog.
        '''
        logo = gtk.gdk.pixbuf_new_from_file(dist_path + icon_base)
        description = _("Leave it - it's locked, come back - it's back too...")
        copyright = """Copyright (c) 2007,2008 Lars Friedrichs"""
        people = [
            "Lars Friedrichs <LarsFriedrichs@gmx.de>",
            "Tobias Jakobs",
            "Zsolt Mazolt"]
        translators = """Translators:
   de Lars Friedrichs <LarsFriedrichs@gmx.de>
   en Lars Friedrichs <LarsFriedrichs@gmx.de>
   es César Palma <cesarpalma80@gmail.com>
   fa Ali Sattari <ali.sattari@gmail.com>
   fr Claude <f5pbl@users.sourceforge.net>
   hu Kami <kamihir@freemail.hu>
   it e633 <e633@users.sourceforge.net>
   Prosper <prosper.nl@gmail.com>
   ru Alexey Lubimov
   sv Jan Braunisch <x@r6.se>
   th Maythee Anegboonlap & pFz <null@llun.info>
Former translators:
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
        along with BlueProximity; if not, write to the

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

    def pausePressed(self, widget, data=None):
        '''
        Callback to activate and deactivate pause mode.
        This is actually done by removing the proximity object's mac address.
        '''
        if self.pauseMode:
            self.pauseMode = False
            for config in configs:
                config[2].dev_mac = config[2].lastMAC
                config[2].Simulate = False
            self.icon.set_from_file(dist_path + icon_con)
        else:
            self.pauseMode = True
            for config in configs:
                config[2].lastMAC = config[2].dev_mac
                config[2].dev_mac = ''
                config[2].Simulate = True
                config[2].kill_connection()

    def setComboValue(self, widget, value):
        '''
        helper function to set a ComboBox's value to value if that exists in the Combo's list
        The value is not changed if the new value is not member of the list.
        @param widget a gtkComboBox object
        @param value the value the gtkComboBox should be set to.
        '''
        model = widget.get_model()
        for row in model:
            if row[0] == value:
                widget.set_active_iter(row.iter)
                break

    def getComboValue(self, widget):
        '''
        helper function to get a ComboBox's value
        '''
        model = widget.get_model()
        iter = widget.get_active_iter()
        return model.get_value(iter, 0)

    def readSettings(self):
        '''
        Reads the config settings and sets all GUI components accordingly.
        '''
        # Updates the controls to show the actual configuration of the running proximity
        was_live = self.gone_live
        self.gone_live = False
        self.wTree.get_widget("entryMAC").set_text(self.config['device_mac'])
        self.wTree.get_widget("entryChannel").set_value(int(self.config['device_channel']))
        self.wTree.get_widget("hscaleLockDist").set_value(int(self.config['lock_distance']))
        self.wTree.get_widget("hscaleLockDur").set_value(int(self.config['lock_duration']))
        self.wTree.get_widget("hscaleUnlockDist").set_value(int(self.config['unlock_distance']))
        self.wTree.get_widget("hscaleUnlockDur").set_value(int(self.config['unlock_duration']))
        self.wTree.get_widget("comboLock").child.set_text(self.config['lock_command'])
        self.wTree.get_widget("comboUnlock").child.set_text(self.config['unlock_command'])
        self.wTree.get_widget("comboProxi").child.set_text(self.config['proximity_command'])
        self.wTree.get_widget("hscaleProxi").set_value(self.config['proximity_interval'])
        self.wTree.get_widget("checkSyslog").set_active(self.config['log_to_syslog'])
        self.setComboValue(self.wTree.get_widget("comboFacility"), self.config['log_syslog_facility'])
        self.wTree.get_widget("checkFile").set_active(self.config['log_to_file'])
        self.wTree.get_widget("entryFile").set_text(self.config['log_filelog_filename'])
        self.gone_live = was_live

    def writeSettings(self):
        '''
        Reads the current settings from the GUI and stores them in the configobj object.
        '''
        # Updates the running proximity and the config file with the new settings from the controls
        was_live = self.gone_live
        self.gone_live = False
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
        self.gone_live = was_live

    def btnResetMinMax_clicked(self, widget, data=None):
        '''
        Callback for resetting the values for the min/max viewer.
        '''
        self.minDist = -255
        self.maxDist = 0

    def event_settings_changed(self, widget, data=None):
        '''
        Callback called by almost all GUI elements if their values are changed.
        We don't react if we are still initializing (self.gone_live==False)
        because setting the values of the elements would already fire their change events.
        @see gone_live
        '''
        if self.gone_live:
            self.writeSettings()
        pass

    def event_settings_changed_reconnect(self, widget, data=None):
        '''
        Callback called by certain GUI elements if their values are changed.
        We don't react if we are still initializing (self.gone_live==False)
        because setting the values of the elements would already fire their change events.
        But in any case we kill a possibly existing connection.
        Changing the rfcomm channel e.g. fires this event instead of event_settings_changed.
        @see event_settings_changed
        '''
        self.proxi.kill_connection()
        if self.gone_live:
            self.writeSettings()
        pass

    def event_scanChannelResult_changed(self, widget, data=None):
        '''
        Callback called when one clicks into the channel scan results.
        It sets the 'selected channel' field to the selected channel
        '''
        # Put selected channel in channel entry field
        selection = self.wTree.get_widget("treeScanChannelResult").get_selection()
        (model, iter) = selection.get_selected()
        value = model.get_value(iter, 0)
        self.wTree.get_widget("entryChannel").set_value(int(value))
        self.writeSettings()

    def btnClose_clicked(self, widget, data=None):
        '''
        Callback to just close and not destroy the main window
        '''
        self.Close()
        return 1

    def btnSelect_clicked(self, widget, data=None):
        '''
        Callback called when one clicks on the 'use selected address' button
        it copies the MAC address of the selected device into the mac address field.
        '''
        # Takes the selected entry in the mac/name table and enters its mac in the MAC field
        selection = self.tree.get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        model, selection_iter = selection.get_selected()
        if (selection_iter):
            mac = self.model.get_value(selection_iter, 0)
            self.wTree.get_widget("entryMAC").set_text(mac)
            self.writeSettings()

    def btnScan_clicked(self, widget, data=None):
        '''
        Callback that is executed when the scan for devices button is clicked
        actually it starts the scanning asynchronously to have the gui redraw nicely before hanging :-)
        '''
        # scan the area for bluetooth devices and show the results
        watch = gtk.gdk.Cursor(gtk.gdk.WATCH)
        self.window.window.set_cursor(watch)
        self.model.clear()
        self.model.append(['...', _('Now scanning...')])
        self.setSensitiveConfigManagement(False)
        gobject.idle_add(self.cb_btnScan_clicked)

    def cb_btnScan_clicked(self):
        '''
        Asynchronous callback function to do the actual device discovery scan
        '''
        tmpMac = self.proxi.dev_mac
        self.proxi.dev_mac = ''
        self.proxi.kill_connection()
        macs = []
        try:
            macs = self.proxi.get_device_list()
        except:
            macs = [['', _('Sorry, the bluetooth device is busy connecting.\nPlease enter a correct mac address or no address at all\nfor the config that is not connecting and try again later.')]]
        self.proxi.dev_mac = tmpMac
        self.model.clear()
        for mac in macs:
            self.model.append([mac[0], mac[1]])
        self.window.window.set_cursor(None)
        self.setSensitiveConfigManagement(True)

    def btnScanChannel_clicked(self, widget, data=None):
        '''
        Callback that is executed when the scan channels button is clicked.
        It starts an asynchronous scan for the channels via initiating a ScanDevice object.
        That object does the magic, updates the gui and afterwards calls the callback function btnScanChannel_done.
        '''
        # scan the selected device for possibly usable channels
        if self.scanningChannels:
            self.wTree.get_widget("labelBtnScanChannel").set_label(_("Sca_n channels on device"))
            self.wTree.get_widget("channelScanWindow").hide_all()
            self.scanningChannels = False
            self.scanner.doStop()
            self.setSensitiveConfigManagement(True)
        else:
            self.setSensitiveConfigManagement(False)
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
            dialog.connect("response", lambda x, y: dialog.destroy())
            dialog.run()
            self.scanner = ScanDevice(mac, self.modelScan, was_paused, self.btnScanChannel_done)
        return 0

    def btnScanChannel_done(self, was_paused):
        '''
        The callback that is called by the ScanDevice object that scans for a device's usable rfcomm channels.
        It is called after all channels have been scanned.
        @param was_paused informs this function about the pause state before the scan started.
        That state will be reconstructed by the function.
        '''
        self.wTree.get_widget("labelBtnScanChannel").set_label(_("Sca_n channels on device"))
        self.scanningChannels = False
        self.setSensitiveConfigManagement(True)
        if not was_paused:
            self.pausePressed(None)
            self.proxi.Simulate = True

    def Close(self):
        # Hide the settings window
        self.window.hide()
        # Disable simulation mode for all configs
        for config in configs:
            config[2].Simulate = False

    def quit(self, widget, data=None):
        # try to close everything correctly
        self.icon.set_from_file(dist_path + icon_att)
        for config in configs:
            config[2].logger.log_line(_('stopped.'))
            config[2].Stop = 1
            time.sleep(2)
            gtk.main_quit()

    def updateState(self):
        '''
        Updates the GUI (values, icon, tooltip) with the latest values
        is always called via gobject.timeout_add call to run asynchronously without a seperate thread.
        '''
        # update the display with newest measurement values (once per second)
        newVal = int(self.proxi.Dist)  # Values are negative!
        if newVal > self.minDist:
            self.minDist = newVal
        if newVal < self.maxDist:
            self.maxDist = newVal
        self.wTree.get_widget("labState").set_text(_("min: ") +
            str(-self.minDist) + _(" max: ") + str(-self.maxDist) + _(" state: ") + self.proxi.State)
        self.wTree.get_widget("hscaleAct").set_value(-newVal)

        # Update icon too
        if self.pauseMode:
            self.icon.set_from_file(dist_path + icon_pause)
            self.icon.set_tooltip(_('Pause Mode - not connected'))
        else:
            # we have to show the 'worst case' since we only have one icon but many configs...
            connection_state = 0
            con_info = ''
            con_icons = [icon_base, icon_att, icon_away, icon_con]
            for config in configs:
                if config[2].ErrorMsg == "No connection found, trying to establish one...":
                    connection_state = 3
                else:
                    if config[2].State != _('active'):
                        if (connection_state < 2):
                            connection_state = 2
                    else:
                        if newVal < config[2].active_limit:
                            if (connection_state < 1):
                                connection_state = 1
                if (con_info != ''):
                    con_info = con_info + '\n\n'
                con_info = con_info + config[0] + ': ' + _('Detected Distance: ') + str(-config[2].Dist) + '; ' + _("Current State: ") + config[2].State + '; ' + _("Status: ") + config[2].ErrorMsg
            if self.proxi.Simulate:
                simu = _('\nSimulation Mode (locking disabled)')
            else:
                simu = ''
            self.icon.set_from_file(dist_path + con_icons[connection_state])
            self.icon.set_tooltip(con_info + '\n' + simu)
        self.timer = gobject.timeout_add(1000, self.updateState)

    def proximityCommand(self):
        # This is the proximity command callback called asynchronously as the updateState above
        if self.proxi.State == _('active') and not self.proxi.Simulate:
            ret_val = os.popen(self.config['proximity_command']).readlines()
        self.timer2 = gobject.timeout_add(1000*self.config['proximity_interval'], self.proximityCommand)
