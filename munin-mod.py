#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Program docstring.

Application to format munin conf entries to html or modify an entry
- assume munin.conf rw for www-data (!)

"""
__author__ = "Zacharias El Banna"
__version__ = "1.0"
__status__ = "Production"

from sys import argv, exit, path as syspath
syspath.append('/usr/local/sbin')
from Munin import muninLoadConf, muninSetConf

if argv[1] == "view" and len(argv) == 2:
 munindict = muninLoadConf('/etc/munin/munin.conf')
 keys = munindict.keys()
 keys.sort()
 for entry in keys:
  print "<TR><TD>" + entry + "</TD><TD><A HREF='munin-control.php?node=" + entry + "&curr-state=" + munindict[entry][1] + "'>" +  munindict[entry][1] + "</A></TD></TR>"
elif argv[1] == "view" and len(argv) == 3:
 munindict = muninLoadConf('/etc/munin/munin.conf')
 print argv[2] + " update is " + munindict[argv[2]][1]
elif argv[1] == "config" and len(argv) == 4:
 muninSetConf('/etc/munin/munin.conf', argv[2], argv[3])
 print argv[2] + " modified update to: " + argv[3]
else:
 print argv[0] + " <config|view> <node> [<new-state>]"
