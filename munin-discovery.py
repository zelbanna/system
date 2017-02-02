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

#################### MAIN ####################
# print start, stop, stop - start

if len(argv) < 3:
 print argv[0] + " <file|stdout> <start/single ip> [<end ip>]"
 exit(0)

start = argv[2]
if len(argv) == 3:
 stop  = start
else: 
 stop  = argv[3]

muninDiscover(start,stop, "127.0.0.1")

