.. Blueproximity documentation master file, created by
   sphinx-quickstart on Sat Aug 20 23:04:32 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Blueproximity
=============

This manual tries to give you the most pleasurable experience with your BlueProximity environment.
You should read it carefully to get the idea behind and fully understand its possibilities and limits.

Basically BlueProximity is a tool to detect your presence near your computer.
It can automatically lock your computer once you leave it and unlock it when you are back.
Technically it does it the following way.
It connects to your mobile phone via bluetooth and uses the rssi value – something like the automatically set transmission power – to get a distance approximation.
It gives more a quality information than a quantity one.
Bigger numbers are most likely bigger distances but the rssi value changes slowly and is a little inaccurate since you could also cover your phone with your hands – that will increase the rssi value without any distance change...

You see, we cannot measure exact distances but in stable environments you will most likely get reproduceable results.

Table of contents:

.. toctree::
   :maxdepth: 2



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
