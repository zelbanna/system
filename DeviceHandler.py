#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

Module for generic device interaction - back end to device-web.cgi

Exports:
- DeviceHandler

"""  
__author__  = "Zacharias El Banna"
__version__ = "5.0"
__status__  = "Production"

from SystemFunctions import pingOS, sysIPs2Range, sysLogDebug, sysLogMsg
from threading import Lock, Thread, active_count, enumerate

class Devices(object):

 def __init__(self, aconfigfile = '/var/www/device.hosts.conf'):
  self._configfile = aconfigfile
  self._configitems = {}

 def __str__(self):
  configitems = ""
  for key, value in self._configitems.iteritems():
   configitems = "{:<16} ".format(key) + " ".join(value) + "\n" + configitems
  return "Device: {}\n{}".format(self._configfile, configitems.strip())

 def index(self,target):
  position = { 'domain':0, 'fqdn':1, 'dns':2, 'snmp':3, 'model':4, 'type':5, 'is_graphed':6, 'rack':7, 'unit':8, 'consoleport':9 }
  return position[target]

 # Add target :-)
 def widgetDeviceTable(self, view='dev_cont'):
  print "<DIV CLASS=z-table>"             
  print "<TABLE WIDTH=340>"
  print "<TR><TH>IP</TH><TH>FQDN</TH><TH>Model</TH></TR>"
  #
  # Sort?
  #
  for key, values in self._configitems.iteritems():
   print "<TR><TD><A TARGET={0} HREF=device-web.cgi?op=deviceinifo&id={1}>{1}</A></TD><TD>{2}</TD><TD>{3}</TD></TR>".format(view, key, values[1], values[4]) 
  print "</TABLE>"
  print "</DIV>"

 def loadConf(self):
  try:
   with open(self._configfile) as conffile:
    # Clear old dict first..
    self._configitems.clear()
    for line in conffile:
     if line.startswith('#'):
      continue
     entry = " ".join(line.split()).split()
     self._configitems[entry[0]] = entry[1:]
  except Exception as err:
   sysLogMsg("DeviceHandler loadConf: error reading config file - [{}]".format(str(err)))
 
 def getEntry(self, aentry):
  return self._configitems.get(aentry,None)

 def getEntries(self):
  keys = self._configitems.keys()
  keys.sort()
  return keys

 def getTargetEntries(self, target, arg):
  found = []
  indx = self.index(target)
  for key, value in self._configitems.iteritems():
   if value[indx] == arg:
    found.append(key)
  found.sort()
  return found

 def addEntry(self, akey, aentry):
  try:
   with open(self._configfile,'a') as conffile:
    conffile.write("{:<16} {}\n".format(akey," ".joint(aentry)))
   self._configitems[akey] = aentry
  except:
   pass
 
 #
 # Lists in python are passed by ref so updating an entry is not requireing a lot of copy
 # Just modify entry using index function directly and write to file :-)
 def updateConf(self):
  from os import chmod
  try:
   with open(self._configfile,'w') as conffile:
    conffile.write("################################# HOSTS DB ##################################\n")
    for key, entry in self._configitems.iteritems():
     conffile.write("{:<16} {}\n".format(key," ".join(entry)))
   chmod(self._configfile, 0o666)
  except Exception as err:
   sysLogMsg("Devices : Error writing config: " + str(err))
   return False
  return True
  
 ##################################### Device Discovery and Detection ####################################
 #
 # clear existing entries or not?
 def discover(self, aStartIP, aStopIP, adomain, aclear = False):
  from time import time

  start_time = int(time())
  sysLogMsg("Device discovery: " + aStartIP + " -> " + aStopIP + ", for domain '" + adomain + "'")

  try:
   for ip in sysIPs2Range(aStartIP, aStopIP):
    if aclear:
     self._configitems.pop(ip,None)
    else:
     existing = self._configitems.get(ip,None)
     if existing:
      continue
 
    t = Thread(target = self._detect, args=[ip, adomain])
    t.name = "Detect " + ip
    t.start()
    # Slow down a little..
    if active_count() > 10:
     t.join()
  except Exception as err:
   sysLogMsg("Device discovery: Error [{}]".format(str(err)))
  sysLogMsg("Device discovery: Total time spent: {} seconds".format(int(time()) - start_time))
  
  # Join all threads
  wait = True
  while wait:
   if active_count() > 1:
    t = enumerate()
    t[1].join()
   else:
    wait = False
  #  
  # Update conf
  self.updateConf()

 ########################### Detect Devices ###########################
 #
 # Device must answer to ping(!) for system to continue
 #
 def _detect(self, aip, adomain):
  from netsnmp import VarList, Varbind, Session
  from socket import gethostbyaddr
  if not pingOS(aip):
   return False
  
  try:
   # .1.3.6.1.2.1.1.1.0 : Device info
   # .1.3.6.1.2.1.1.5.0 : Device name
   devobjs = VarList(Varbind('.1.3.6.1.2.1.1.1.0'), Varbind('.1.3.6.1.2.1.1.5.0'))
   session = Session(Version = 2, DestHost = aip, Community = 'public', UseNumeric = 1, Timeout = 100000, Retries = 2)
   session.get(devobjs)
  except:
   pass
   
  dns,fqdn,model,type = 'unknown','unknown','unknown','unknown'
  snmp = devobjs[1].val.lower() if devobjs[1].val else 'unknown'
  try:
   dns = gethostbyaddr(aip)[0].split('.')[0].lower()
   fqdn = dns
  except:
   fqdn = snmp
  fqdn = fqdn.split('.')[0] + "." + adomain if not (adomain in fqdn) else fqdn

  if devobjs[0].val:
   infolist = devobjs[0].val.split()
   if infolist[0] == "Juniper":
    if infolist[1] == "Networks,":
     model = infolist[3].lower()
     for tp in [ 'ex', 'srx', 'qfx', 'mx', 'wlc' ]:
      if tp in model:
       type = tp
       break
     else:
      type = "other"
    else:
     subinfolist = infolist[1].split(",")
     model = subinfolist[2]
     type  = "other"
   elif infolist[0] == "VMware":
    model = "esxi"
    type  = "esxi"
   elif infolist[0] == "Linux":
    model = "linux"
    if "Debian" in devobjs[0].val:
     type = "debian"
    else:
     type = "generic"
   else:
    model = "other"
    type  = " ".join(infolist[0:4])

  self._configitems[aip] = [ adomain, fqdn, dns, snmp, model, type, 'no', 'unknown', 'unknown', 'unknown' ]
  return True

#############################################################################
