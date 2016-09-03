Config
******

By default ``XDG_CONFIG_HOME/blueproximity/config.ini`` will be assumed as configfile-location.
You can specify a custom one by using the ``-c/--config`` cli-arg.
The config uses the ini-format, sections are defined by using ``[SECTION]`` and values are simply specified with ``key = value``.
For boolean values use ``true/yes`` or ``false/no``.

======
Device
======
* ``mac`` Mac-adress of the bluetooth-device
* ``port`` Port to connect to on the bluetooth-device
* ``name`` (optional) Name of the bluetooth device

====
Lock
====
Lock-specific settings

* ``distance`` Lock screen if device distance is greater than this value
* ``duration`` Lock device after device is out of range for x intervals (see ``Proximity.interval``)
* ``command`` Command to run for lock-action

======
Unlock
======
Unlock-specific settings

* ``distance`` Same as ``Lock.distance`` but for unlock
* ``duration`` Same as ``Lock.duration`` but for unlock
* ``command`` Same as ``Lock.command`` but for unlock

=========
Proximity
=========
General settings for Blueproximity-worker

* ``interval`` Check proximity of device every x seconds

===
Log
===
* ``syslog`` Log to syslog
* ``syslog_facility`` If ``syslog`` log to this facility
* ``file`` Log to file
* ``filename`` If ``file`` log to this filename
