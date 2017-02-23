#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

Module for graph interaction

Exports:
- Grapher

"""  
__author__ = "Zacharias El Banna"
__version__ = "5.0"
__status__ = "Production"

from SystemFunctions import sysLogDebug, sysLogMsg, pingOS
from threading import Lock, Thread, active_count

####################################### Grapher Class ##########################################
#
#

class Grapher(object):

 def __init__(self, aconf='/etc/munin/munin.conf', agraphplug = '/var/www/device.graph.plugins'):
  self._configfile = aconf
  self._configitems = {}
  self._graphplug = agraphplug
  self._graphlock = Lock()
 
 def __str__(self):
  return "ConfigFile:{} PluginFile:{} ConfigKeys:[{}]".format(self._configfile, self._graphplug, str(self._configitems.keys()))

 def printHtml(self, asource):
  from time import time
  stop  = int(time())-300
  start = stop - 24*3600 
  print "<A HREF='munin-cgi/munin-cgi-html/static/dynazoom.html?"
  print "cgiurl_graph=/munin-cgi/munin-cgi-graph&plugin_name={0}&size_x=800&size_y=400&start_epoch={1}&stop_epoch={2}' target=sect_cont>".format(asource,str(start),str(stop))
  print "<IMG width=399 height=224 ALT='munin graph:{0}' SRC='/munin-cgi/munin-cgi-graph/{0}-day.png' /></A>".format(asource)

 def widgetCols(self, asources, aclose = False):
  lwidth = 3 if len(asources) < 3 else len(asources)
  print "<DIV CLASS='z-graph' style='width:{}px; height:240px; float:left;'>".format(str(lwidth * 420))
  for src in asources:
   self.printHtml(src)
  if aclose: print "<A class='z-btn z-small-btn' onclick=this.parentElement.style.display='none' style='vertical-align:top; margin:8px;'><B>X</B></A>"
  print "</DIV>"

 def widgetRows(self, asources, aclose = False):
  lheight = 3 if len(asources) < 3 else len(asources)
  print "<DIV CLASS='z-graph' style='width:420px; height:{}px; float:left;'>".format(str(lheight * 240))
  if aclose: print "<A class='z-btn z-small-btn' onclick=this.parentElement.style.display='none' style='float:right; margin:8px;'><B>X</B></A>"
  for src in asources:
   self.printHtml(src)
   print "<BR>"
  print "</DIV>"

 #
 # Config items contains entry: [ handler, updatestate ]
 #
 def loadConf(self):
  # read until find [ ... ] then read two more lines, finally add to dict
  with open(self._configfile) as conffile:
   # Clear old dict first..
   self._configitems.clear()
   entry,handler,update = None, None, None
   extra = []
  
   # Modify for arbitrary length! to store more "nice" stuff with Grapher
   #
   for linen in conffile:
    line = linen.strip()
    if entry:
     if line.startswith("address"):
      handler = line[8:]
     elif line.startswith("update"):
      update = line[7:10].strip()
      self._configitems[entry] = [handler, update]
      entry,handler,update = None, None, None
      extra = []
    elif line.startswith("[") and line.endswith("]"):
     entry = line[1:-1]

 def getEntry(self, aentry):
  if not self._configitems:
   self.loadConf()
  return self._configitems.get(aentry,None)

 def getEntries(self):
  if not self._configitems:
   self.loadConf()
  return self._configitems.keys()
  
 def updateEntry(self, aentry, astate):
  oldstate = "no" if astate == "yes" else "yes"
  try:
   with open(self._configfile, 'r') as conffile:
    filedata = conffile.read()
   pos = filedata.find("[" + aentry + "]")
   old,new = None, None
   if pos > 0:
    old = filedata[pos:pos + 100].split("[")[1]
    new = old.replace("update " + oldstate, "update " + astate, 1)
    filedata = filedata.replace(old,new)
    with open(self._configfile, 'w') as conffile:
     conffile.write(filedata)
    data = self._configitems.get(aentry,None)
    if data:
     data[1] = astate
     self._configitems[aentry] = data
  except Exception as err:
   sysLogMsg("Grapher updateEntry: Error [{}]".format(str(err)))

 def addEntry(self, akey, aupdate, ahandler = '127.0.0.1'):
  with open(self._configfile, 'a') as conffile:
   conffile.write("\n")
   conffile.write("[" + akey + "]\n")
   conffile.write("address " + ahandler + "\n")
   conffile.write("update " + aupdate + "\n")
  self._configitems[akey] = [ ahandler, aupdate ]
 
 #
 # Writes plugin info for devices found with DeviceHandler
 #
 def discover(self, ahandler = '127.0.0.1'):
  from os import chmod
  from time import time
  from DeviceHandler import Devices
  start_time = int(time())
  try:
   with open(self._graphplug, 'w') as f:
    f.write("#!/bin/bash\n")
   chmod(self._graphplug, 0o777)

   devs = Devices()
   devs.loadConf()
   entries = devs.getEntries()
   entries.sort()
   for key in entries:
    t = Thread(target = self._detect, args=[key, devs.getEntry(key), ahandler])
    t.start()
    if active_count() > 10:
     t.join()
  except Exception as err:
   sysLogMsg("graphDiscover: failure in processing Device entries: [{}]".format(str(err)))
  sysLogMsg("graphDiscover: Total time spent: {} seconds".format(int(time()) - start_time))

 ########################### Detect Plugins ###########################
 #
 # Device must answer to ping(!) for system to continue
 #
 def _detect(self, aip, aentry, ahandler = '127.0.0.1'):
  if not pingOS(aip):
   return False
  from JRouter import JRouter  
  activeinterfaces = []
  type = aentry[5]
  fqdn = aentry[1]
  try:
   if type in [ 'ex', 'srx', 'qfx', 'mx', 'wlc' ]:
    if not type == 'wlc':
     jdev = JRouter(aip)
     if jdev.connect():
      activeinterfaces = jdev.getUpInterfaces()
      jdev.close()
     else:
      sysLogMsg("Graph detect: impossible to connect to {}! [{} - {}]".format(fqdn,type,model))
    self._graphlock.acquire()      
    with open(self._graphplug, 'a') as graphfile:
     if self.getEntry(fqdn) == None:
      self.addEntry(fqdn, ahandler, "no")
     graphfile.write('ln -s /usr/local/sbin/plugins/snmp__{0} /etc/munin/plugins/snmp_{1}_{0}\n'.format(type,fqdn))
     graphfile.write('ln -s /usr/share/munin/plugins/snmp__uptime /etc/munin/plugins/snmp_' + fqdn + '_uptime\n')
     graphfile.write('ln -s /usr/share/munin/plugins/snmp__users  /etc/munin/plugins/snmp_' + fqdn + '_users\n')
     for ifd in activeinterfaces:
      graphfile.write('ln -s /usr/share/munin/plugins/snmp__if_    /etc/munin/plugins/snmp_' + fqdn + '_if_'+ ifd[2] +'\n')
    self._graphlock.release()
   elif type == "esxi":
    self._graphlock.acquire()
    with open(self._graphplug, 'a') as graphfile:
     if not self.addEntry(fqdn):
      agrapher.addConf(fqdn, ahandler, "no")
     graphfile.write('ln -s /usr/share/graph/plugins/snmp__uptime /etc/munin/plugins/snmp_' + fqdn + '_uptime\n')              
     graphfile.write('ln -s /usr/local/sbin/plugins/snmp__esxi    /etc/munin/plugins/snmp_' + fqdn + '_esxi\n')
    self._graphlock.release()
  except Exception as err:
   sysLogMsg("Graph detect - error: [{}]".format(str(err)))
   return False
  return True

#############################################################################
