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
from threading import Lock, Thread, active_count

class Devices(object):

 def __init__(self, aconfigfile = '/var/www/device.hosts.conf'):
  self._configfile = aconfigfile
  self._configlock = Lock()
  self._configitems = {}

 def __str__(self):
  return "Device({} {})".format(self._configfile, str(self._configitems))

 #
 # Config entry contains [ip]:  [ domain, fqdn, dns, snmp, model, type, is_graphed, rack, unit, consoleport]
 #
 def loadConf(self):
  try:
   with open(self._configfile) as conffile:
    # Clear old dict first..
    self._configitems.clear()
    for line in conffile:
     if line.startswith('#'):
      continue
     entry = " ".join(line.split()).split()
     self._configitems[entry[0]] = entry[1:8]
  except Exception as err:
   sysLogMsg("DeviceHandler loadConf: error reading config file - [{}]".format(str(err)))

 def getEntry(self, aentry):
  if not self._configitems:
   self.loadConf()
  return self._configitems.get(aentry,None)
        
 def getEntries(self):
  if not self._configitems:
   self.loadConf()
  return self._configitems.keys()
   
 def discover(self, aStartIP, aStopIP, adomain):
  from os import chmod
  from time import time
  start_time = int(time())
  sysLogMsg("Device discovery: " + aStartIP + " -> " + aStopIP + ", for domain '" + adomain + "'")
  # Reset hosts file
  try:
   with open(self._configfile, 'w') as f:
    f.write("################################# HOSTS FOUND  ##################################\n")
   chmod(self._configfile, 0o666)
   for ip in sysIPs2Range(aStartIP, aStopIP):
    t = Thread(target = self._detect, args=[ip, adomain])
    t.start()
    # Slow down a little..
    if active_count() > 10:
     t.join()
  except Exception as err:
   sysLogMsg("Device discovery: Error [{}]".format(str(err)))
  sysLogMsg("Device discovery: Total time spent: {} seconds".format(int(time()) - start_time))


 ########################### Detect Devices ###########################
 #
 # Device must answer to ping(!) for system to continue
 #
 def _detect(self, aip, adomain):
  if not pingOS(aip):
   return False

  from netsnmp import VarList, Varbind, Session
  from socket import gethostbyaddr
  
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

  with open(self._configfile, 'a') as hostsfile:
   self._configlock.acquire()
   hostsfile.write("{:<16} {:<10} {:<16} {:<12} {:<12} {:<12} {:<8} no unknown unknown unknown\n".format(aip, adomain, fqdn, dns, snmp, model, type))
   self._configlock.release()
  return True

#############################################################################
