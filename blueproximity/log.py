import time

import syslog


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
