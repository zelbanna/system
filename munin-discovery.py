#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Program docstring.

Application to discovery network hosts on a subnet and deduce model (and manufacturer) and name
- Places found munin things  in /var/tmp/munin.conf
- Places found hosts updates in /var/tmp/hosts.conf

"""
__author__ = "Zacharias El Banna"
__version__ = "1.1"
__status__ = "Production"

from sys import argv, exit, path as syspath
syspath.append('/usr/local/sbin')
from Devices import DeviceHandler
from SystemFunctions import simpleArgParser

args = simpleArgParser(argv)
if len(args) < 2:
 print argv[0] + "--domain <domain/suffix> --start <start/single ip> [--end <end ip>]"
 exit(0)

start = args.get('start', '127.0.0.1')
stop  = args.get('end', start)
domain = args.get('domain','mgmt')
dev = DeviceHandler()
dev.discoverDevices(start,stop,domain)
