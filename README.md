Blueproximity [![Documentation Status](https://readthedocs.org/projects/blueproximity/badge/?version=latest)](http://blueproximity.readthedocs.io/en/latest/?badge=latest) [![Build Status](https://travis-ci.org/Thor77/Blueproximity.svg?branch=master)](https://travis-ci.org/Thor77/Blueproximity)
=============

**Currently only [CLI](#CLI) usage is in a working state**
**You have to pair your bluetooth device manually and specifc it's MAC-address as an argument**

[TODOs until reaching usable state](https://github.com/Thor77/Blueproximity/milestone/1)

This software helps you add a little more security to your
desktop. It does so by detecting one of your bluetooth devices,
most likely your mobile phone, and keeping track of its distance.

If you move away from your computer and the distance is above
a certain level (no measurement in meters is possible) for a
given time, it automatically locks your desktop
(or starts any other shell command you want).
See end of this file for interesting commands.

Once away your computer awaits its master back - if you are
nearer than a given level for a set time your computer unlocks
magically without any interaction
(or starts any other shell command you want).

See the doc/ directory or the website which both contain
a manual with screenshots.

Please note that there might still some bugs, use the sourceforge
site to keep track of them or tell me about new ones not mentioned
there.
Please read the whole manual - it's short enough, hopefully easy
understandable and hey - it even got some pretty pictures in there
too :-)

## Contributors
* Tobias Jakobs (GUI optimizations)
* Zsolt Mazolt (GUI and KDE stuff)
* christoss (Slovene translation)
* eljak (Arabic translation)
* byMeanMachine (Polish translation)

## Interesting commands
* Un-/Locking gnome-screenserver
    * `gnome-screensaver-command -l`
    * `gnome-screensaver-command -d`
* Telling GAIM your status
  * `gaim-remote "irc:setstatus?status=away&message=BlueProximity thinks I am away"`
  * `gaim-remote "irc:setstatus?status=available"`

## CLI
```
usage: blueproximity [-h] [--gui] [-c CONFIG] -m MAC

Unlock your computer as soon as a bluetooth-device is in range

optional arguments:
  -h, --help            show this help message and exit
  --gui                 Start GUI
  -c CONFIG, --config CONFIG
                        Path to configfile
  -m MAC, --mac MAC     Provide mac of target device
```

Example `config.ini`
```
[Lock]
distance = 7
duration = 7
command = gnome-screensaver-command -l

[Unlock]
distance = 4
duration = 1
command = gnome-screensaver-command -d
```
