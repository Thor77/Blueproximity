import signal

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


def main():
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

if __name__ == '__main__':
    main()
