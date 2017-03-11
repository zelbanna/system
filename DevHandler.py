#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

Module for generic device interaction - back end to device-web.cgi

Exports:
- DeviceHandler

"""  
__author__  = "Zacharias El Banna"
__version__ = "1.0GA"
__status__  = "Production"

from GenLib import ping_os, sys_ips2range, sys_ip2int, sys_log_msg
from PasswordContainer import snmp_read_community
class Devices(object):

 # console port assumes cascaded devices..
 _position = { 'domain':0, 'fqdn':1, 'dns':2, 'snmp':3, 'model':4, 'type':5, 'graphed':6, 'rack':7, 'unit':8, 'consoleport':9, 'powerslots':10 }

 @classmethod
 def get_index(cls, target):
  return cls._position[target]

 def __init__(self, aconfigfile = '/var/www/device.hosts.conf'):
  self._configfile = aconfigfile
  self._configitems = {}

 def __str__(self):
  configitems = ""
  for key, value in self._configitems.iteritems():
   configitems = "{:<16} ".format(key) + " ".join(value) + "\n" + configitems
  return "Device: {}\n{}".format(self._configfile, configitems.strip())

 def load_conf(self):
  try:
   with open(self._configfile) as conffile:
    # Clear old dict first..
    self._configitems.clear()
    for line in conffile:
     entry = " ".join(line.split()).split()
     self._configitems[entry[0]] = entry[1:]
  except Exception as err:
   sys_log_msg("DeviceHandler loadConf: error reading config file - [{}]".format(str(err)))

 def quick_entry(self, akey):
  entry = None
  try:
   with open(self._configfile) as conffile:
    for line in conffile:
     entry = " ".join(line.split()).split()
     if entry[0] == akey:
      break
   # Close properly and then..
  except Exception as err:
   sys_log_msg("DeviceHandler loadEntry: error reading config file - [{}]".format(str(err)))
  return entry[1:] 
 
 def get_entry(self, akey):
  return self._configitems.get(akey,None)

 def get_entries(self):
  keys = self._configitems.keys()
  keys.sort(key=sys_ip2int)
  return keys

 def get_target_entries(self, target, arg):
  found = []
  indx = Devices.get_index(target)
  for key, value in self._configitems.iteritems():
   if value[indx] == arg:
    found.append(key)
  found.sort(key=sys_ip2int)
  return found

 def add_entry(self, akey, aentry):
  try:
   with open(self._configfile,'a') as conffile:
    conffile.write("{:<16} {}\n".format(akey," ".joint(aentry)))
   self._configitems[akey] = aentry
  except:
   pass
 
 #
 # Lists in python are passed by ref so updating an entry is not requireing a lot of copy
 # Just modify entry using index function directly and write to file :-)
 def update_conf(self):
  from os import chmod
  try:
   with open(self._configfile,'w') as conffile:
    for key, entry in self._configitems.iteritems():
     conffile.write("{:<16} {}\n".format(key," ".join(entry)))
   chmod(self._configfile, 0o666)
  except Exception as err:
   sys_log_msg("Devices : Error writing config: " + str(err))
   return False
  return True
  
 ##################################### Device Discovery and Detection ####################################
 #
 # clear existing entries or not?
 def discover(self, aStartIP, aStopIP, aDomain, aClear = False):
  from time import time
  from threading import Thread, BoundedSemaphore

  start_time = int(time())
  sys_log_msg("Device discovery: " + aStartIP + " -> " + aStopIP + ", for domain '" + aDomain + "'")

  if not aClear and not self._configitems:
   self.load_conf()

  try:
   sema = BoundedSemaphore(10)
   for ip in sys_ips2range(aStartIP, aStopIP):
    if aClear:
     self._configitems.pop(ip,None)
    else:
     existing = self._configitems.get(ip,None)
     if existing:
      continue
    sema.acquire()
    t = Thread(target = self._detect, args=[ip, aDomain, sema])
    t.name = "Detect " + ip
    t.start()
   
   # Join all threads by acquiring all semaphore resources
   for i in range(10):
    sema.acquire()
   #  
   # Update conf
   self.update_conf()  
  except Exception as err:
   sys_log_msg("Device discovery: Error [{}]".format(str(err)))
  sys_log_msg("Device discovery: Total time spent: {} seconds".format(int(time()) - start_time))

 ########################### Detect Devices ###########################
 #
 # Device must answer to ping(!) for system to continue
 #
 # Add proper community handling..
 #
 def _detect(self, aIP, aDomain, aSema):
  from netsnmp import VarList, Varbind, Session
  from socket import gethostbyaddr
  if not ping_os(aIP):
   aSema.release()
   return False

  try:
   # .1.3.6.1.2.1.1.1.0 : Device info
   # .1.3.6.1.2.1.1.5.0 : Device name
   devobjs = VarList(Varbind('.1.3.6.1.2.1.1.1.0'), Varbind('.1.3.6.1.2.1.1.5.0'))
   session = Session(Version = 2, DestHost = aIP, Community = snmp_read_community, UseNumeric = 1, Timeout = 100000, Retries = 2)
   session.get(devobjs)
  except:
   pass
   
  dns,fqdn,model,type = 'unknown','unknown','unknown','unknown'
  snmp = devobjs[1].val.lower() if devobjs[1].val else 'unknown'
  try:
   dns = gethostbyaddr(aIP)[0].split('.')[0].lower()
   fqdn = dns
  except:
   fqdn = snmp
  fqdn = fqdn.split('.')[0] + "." + aDomain if not (aDomain in fqdn) else fqdn

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
    type = "linux"
    if "Debian" in devobjs[0].val:
     model = "debian"
    else:
     model = "generic"
   else:
    model = "other"
    type  = " ".join(infolist[0:4])

  self._configitems[aIP] = [ aDomain, fqdn, dns, snmp, model, type, 'no', 'unknown', 'unknown', 'unknown','unknown:unknown' ]
  aSema.release()
  return True

#############################################################################
