#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

Module for generic device interaction - back end to device-web.cgi

Exports:
- DeviceHandler

"""  
__author__ = "Zacharias El Banna"
__version__ = "3.0"
__status__ = "Production"

from SystemFunctions import pingOS, sysIPs2Range, sysLogDebug, sysLogMsg
from Grapher import Grapher
from threading import Lock

class Device(object):

 ########################## Discover Devices ##########################
 # 
 # Defautl file names..
 #
 def __init__(self):
  self._hostsfile = '/var/tmp/device.hosts.conf'
  self._hostslock = Lock()
  self._graphplug = '/var/tmp/device.graph.plugins'
  self._graphlock = Lock()

 ########################## Discover Devices ##########################
 #
 # - aStartIP ip
 # - aStopIP ip
 # - domain string (like stolabs)
 # - ahandler, ip of machine that execute snmp fetch, defaults to 127.0.0.1
 #
 def discoverDevices(self, aStartIP, aStopIP, adomain, ahandler = '127.0.0.1'):
  from os import chmod
  sysLogMsg("deviceDiscover: " + aStartIP + " -> " + aStopIP + ", for domain '" + adomain + "', handler:" + ahandler)

  try:
   with open(self._graphplug, 'w') as f:
    f.write("#!/bin/bash\n")
   with open(self._hostsfile, 'w') as f:
    f.write("################################# HOSTS FOUND  ##################################\n")
   chmod(self._graphplug, 0o755)
   chmod(self._hostsfile, 0o644)
  except Exception as err:
   sysLogMsg("MuninDiscovery - failed to open files: [{}]".format(str(err)))
   return False

  ############### Traverse IPs #################

  grapher = Grapher()
  for ip in sysIPs2Range(aStartIP, aStopIP):
   self.detectDevice(ip, adomain, grapher, ahandler)

 ############################################### Munin Host checks model ##################################################
 #
 # Device must answer to ping(!)
 #

 def detectDevice(self, aip, adomain, agrapher, ahandler = '127.0.0.1'):
  if not pingOS(aip):
   return False

  from JRouter import JRouter
  from netsnmp import VarList, Varbind, Session
  from socket import gethostbyaddr
    
  dns,fqdn,model,snmp,type = None,None,None,None,None  
  try:
   # .1.3.6.1.2.1.1.1.0 : Device info
   # .1.3.6.1.2.1.1.5.0 : Device name
   devobjs = VarList(Varbind('.1.3.6.1.2.1.1.1.0'), Varbind('.1.3.6.1.2.1.1.5.0'))
   session = Session(Version = 2, DestHost = aip, Community = 'public', UseNumeric = 1, Timeout = 100000, Retries = 2)
   session.get(devobjs)
  except:
   pass

  snmp = devobjs[1].val.lower() if devobjs[1].val else "unknown"
  try:
   dns = gethostbyaddr(aip)[0].split('.')[0].lower()
   fqdn = dns
  except:
   dns = "unknown"
   fqdn = snmp
  fqdn = fqdn.split('.')[0] + "." + adomain if not (adomain in fqdn) else fqdn

  if devobjs[0].val:
   activeinterfaces = []    
   infolist = devobjs[0].val.split()
   if infolist[0] == "Juniper":
    if infolist[1] == "Networks,":
     model = infolist[3].upper()
     for tp in [ "EX", 'SRX', 'QFX', 'MX', 'WLC' ]:
      if tp in model:
       type = tp.lower()
       break
     else:
      type = "other"
     if not type == "other":
      jdev = JRouter(aip)
      if jdev.connect():
       activeinterfaces = jdev.getUpInterfaces()
       jdev.close()
       self._graphlock.acquire()
       with open(self._graphplug, 'a') as graphfile:
        if agrapher.getConfItem(fqdn) == None:
         agrapher.addConf(fqdn, ahandler, "no")
        graphfile.write('ln -s /usr/local/sbin/plugins/snmp__{0} /etc/munin/plugins/snmp_{1}_{0}\n'.format(type,fqdn))
        graphfile.write('ln -s /usr/share/munin/plugins/snmp__uptime /etc/munin/plugins/snmp_' + fqdn + '_uptime\n')
        graphfile.write('ln -s /usr/share/munin/plugins/snmp__users  /etc/munin/plugins/snmp_' + fqdn + '_users\n')
        for ifd in activeinterfaces:
         graphfile.write('ln -s /usr/share/munin/plugins/snmp__if_   /etc/munin/plugins/snmp_' + fqdn + '_if_'+ ifd[2] +'\n')
       self._graphlock.release()
      else:
       sysLogMsg("detectDevice: impossible to connect to {}! [{} - {}]".format(fqdn,type,model))
    else:
     subinfolist = infolist[1].split(",")
     model = subinfolist[2]
     type  = "other"
   elif infolist[0] == "VMware":
    model = "esxi"
    type  = "other"
    slef._graphlock.acquire()
    with open(self._graphplug, 'a') as graphfile:
     if not agrapher.getConfItem(fqdn):
      agrapher.addConf(fqdn, ahandler, "no")
     graphfile.write('ln -s /usr/share/graph/plugins/snmp__uptime /etc/munin/plugins/snmp_' + fqdn + '_uptime\n')              
     graphfile.write('ln -s /usr/local/sbin/plugins/snmp__esxi    /etc/munin/plugins/snmp_' + fqdn + '_esxi\n')
    self._graphlock.release()
   elif infolist[0] == "Linux":
    model = "linux"
    if "Debian" in devobjs[0].val:
     type = "Debian"
    else:
     type = "Generic"
   else:
    model = "other"
    type  = " ".join(infolist[0:4])

  with open(self._hostsfile, 'a') as hostsfile:
   self._hostslock.acquire()
   hostsfile.write("IP:{:<16} FQDN:{:<16} DNS:{:<12} SNMP:{:<12} Model:{:<12} Type:{}\n".format(aip, fqdn, dns, snmp, model, type))
   self._hostslock.release()
  return True
