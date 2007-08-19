blueproximity v1.0

This software helps you add a little more security to your
desktop. It does so by detecting one of your bluetooth devices, 
most likely your mobile phone, and keeping track of its distance. 

If you move away from your computer and the distance is above
a certain level (no measurement in meters is possible) for a 
given time, it automatically locks your desktop 
(or starts any other shell command you want).

Once away your computer awaits its master back - if you are 
nearer than a given level for a set time your computer unlocks 
magically without any interaction 
(or starts any other shell command you want).

See the doc/ directory which contains a manual with screenshots.

Installation - required software

You need to have a python interpreter installed. This software has 
been developed for a unix GNOME desktop - so far. In the future 
there might be updates for other systems too. If you have the GTK 
libs and proper python bindings installed it should also run under
KDE desktop (untestet!) but you should change the lock/unlock 
commands in the config file. With python you need installed 
python-configobj which is used for configuration management and
pybluez that is a python bluez/windows bluetooth stack library.

You need the hcitools package installed so that the command 
hcitool is available to the current user.

Please also note that your computer and your mobile phone should 
already be paired correctly in a way that your phone won't ask 
you any question if the computer connects to it. I will not explain 
this here. Use google and your brain - I will look for a nice page 
describing it and link to it here soon.

Installation - blueproximity

1. Download the most recent version of parpwatch from the 
   sourceforge download page.
2. Unzip the downloaded file into a directory of choice.
3. Open a terminal and switch to the chosen directory with the 
   cd command.
4. type start_proximity.sh
	    
Running blueproximity
	    
A Window will appear where everything useful for starting can be 
configured. You have to enter your phones MAC address. To find 
it, set your phone to bluetooth visible mode. In the first tab 
you can click on Scan for devices and wait some seconds. Your 
device should appear in the list. Select it by clicking on it 
and Use selected device. Then click on the Accept button in the 
lower left of the window.    
You may now set your bluetooth mode to invisible again.
	    
Please note that there are still some bugs, use the sourceforge 
site to keep track of them or tell me about new ones not mentioned 
there.
