#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Program docstring.

Application to discovery network hosts on a subnet and deduce model (and manufacturer) and name
- Places found munin things  in /var/tmp/munin.conf
- Places found hosts updates in /var/tmp/hosts.conf

"""
__author__ = "Zacharias El Banna"
__version__ = "1.0"
__status__ = "Production"

from sys import argv, exit, path as syspath
syspath.append('/usr/local/sbin')
from Munin import muninDiscover
from SystemFunctions import simpleArgParser

if len(argv) == 1:
 print argv[0] + "--domain <domain/suffix> --start <start/single ip> [--end <end ip>]"
 exit(0)

args = simpleArgParser(argv)

start = args.get('start')
stop  = args.get('end', start)
domain = args.get('domain','mgmt')

muninDiscover(start,stop,domain)
