
#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

Module for munin interaction
- Places found munin things  in /var/tmp/munin.conf
-- Both plugins and munin.conf updates
- Places found hosts updates in /var/tmp/hosts.conf

Exports:
- muninLoadConf
- muninSetConf
- muninAppendConf
- muninCheckHost
- muninDiscover
- Munin

"""  
__author__ = "Zacharias El Banna"
__version__ = "1.4"
__status__ = "Production"

from SystemFunctions import pingOS, sysIPs2Range, sysLogDebug
from JRouter import JRouter
from netsnmp import VarList, Varbind, Session
from socket import gethostbyaddr
from os import chmod
from time import time

######################### Munin Class ########################

class Munin(object):

 def __init__(self, aconf='/etc/munin/munin.conf', alib='/mnt/ramdisk/munin/lib/'):
  self._config = aconf
  self._libdir = alib
 
 def __str__(self):
  return "Config: {0} Libdir: {1}".format(self._config,self._libdir)

 def printHtmlTd(self, asource, acolspan=1):
  stop  = int(time())-300
  start = stop - 24*3600 
  print "<TD COLSPAN={}>".format(str(acolspan))
  print "<A HREF='munin-cgi/munin-cgi-html/static/dynazoom.html?"
  print "cgiurl_graph=/munin-cgi/munin-cgi-graph&plugin_name={0}&size_x=800&size_y=400&start_epoch={1}&stop_epoch={2}' target=management_cont>".format(asource,str(start),str(stop))
  print "<IMG width=399 height=224 SRC='/munin-cgi/munin-cgi-graph/{}-day.png' /></A></TD>".format(asource)

######################### Load munin.conf entries ########################

def muninLoadConf(amuninconf):
 with open(amuninconf) as munin:
  # read until find [ ... ] then read two more lines, finally add to dict
  foundall = {}
  found = []
  
  # Modify for arbitrary length!
  #
  for linen in munin:
   line = linen.strip()
   if len(found) == 0 and line.startswith("[") and line.endswith("]"):
    found.append(line[1:-1])
   elif len(found) == 1 and line.startswith("address"):
    found.append(line[8:])
   elif len(found) == 2 and line.startswith("update"):
    found.append(line[7:10].strip())
    foundall[found[0]] = found[1:3]
    found = []
  return foundall
  
def muninSetConf(amuninconf, aname, astate):
 oldstate = "no" if astate == "yes" else "yes"

 with open(amuninconf, 'r') as munin:
  filedata = munin.read()
 
 pos = filedata.find("[" + aname + "]")
 old = None
 new = None
 if pos > 0:
  old = filedata[pos:pos + 100].split("[")[1]
  new = old.replace("update " + oldstate, "update " + astate, 1)
  filedata = filedata.replace(old,new)
  with open(amuninconf, 'w') as munin:
   munin.write(filedata)
  

def muninAppendConf(amuninconf, aname, aip, aupdate):
 with open(amuninconf, 'a') as munin:
  munin.write("\n")
  munin.write("[" + aname + "]\n")
  munin.write("address " + aip + "\n")
  munin.write("update " + aupdate + "\n")
                                                                                     
############################## Munin Host checks model ##############################
#
# Device must answer to ping(!)
#
# result tuple = [ ip, resolved_hname, snmp_hname, vendor, model, type ]
#  - resolved_hname = Name or "unknown" if not found in DNS
#  - snmp_hname     = "unknown" if nothing found by SNMP

def muninCheckHost(ahostname):
 if not pingOS(ahostname):
  return None

 try:
  devobjs = VarList(Varbind('.1.3.6.1.2.1.1.1.0'), Varbind('.1.3.6.1.2.1.1.5.0'))
  session = Session(Version = 2, DestHost = ahostname, Community = 'public', UseNumeric = 1, Timeout = 100000, Retries = 2)
  session.get(devobjs)
 except:
  pass

 try:
  name = gethostbyaddr(ahostname)[0]  
 except:
  name = "unknown"

 if devobjs[0].val == None:
  return [ ahostname, name, "unknown", None ]
 else:
  infolist = devobjs[0].val.split()
  results = [ ahostname, name, devobjs[1].val.lower(), infolist[0] ]
  if infolist[0] == "Juniper":
   if infolist[1] == "Networks,":
    model = infolist[3].upper()
    results.append(model)
    if   "EX" in model:
     results.append("ex")
    elif "SRX" in model:
     results.append("srx")
    elif "QFX" in model:
     results.append("qfx")
    elif "MX" in model:
     results.append("mx")
    elif "WLC" in model:
     results.append("other")
   else:
    subinfolist = infolist[1].split(",")
    results.append(subinfolist[2])
    results.append("other")
  elif infolist[0] == "Linux":
   if "Debian" in devobjs[0].val:
    results.append("Debian")
   else:
    results.append("Generic")
  elif infolist[0] == "VMware":
   results.append(infolist[1])
  else:
   results.append("other")
   results.append( " ".join(infolist[0:4]) )
  return results


########################## Munin Host Discovery ##########################
#
# Output results to muninfile and hostsmods
#
# - astart ip
# - astop ip
# - domain string (like stolabs)
# - ahandler, ip of machine that execute snmp fetch, defaults to 127.0.0.1
#
# Output files must exist (!)

def muninDiscover(astart, astop, adomain, ahandler = '127.0.0.1'):
 print "MuninDiscover: " + astart + " -> " + astop + ", for domain '" + adomain + "', handler:" + ahandler 
 hostsmods = '/var/tmp/hosts.conf'
 muninadds = '/var/tmp/munin.conf'
 muninconf = '/etc/munin/munin.conf'

 muninconfdict = muninLoadConf(muninconf)
 
 ############## Truncate files ################
 chmod(muninadds, 0o755)
 chmod(hostsmods, 0o644)

 with open(muninadds, 'w') as f:
  f.write("#!/bin/bash\n")

 with open(hostsmods, 'w') as f:
  f.write("################################# HOSTS FOUND  ##################################\n")

 ############### Traverse IPs #################

 for ip in sysIPs2Range(astart, astop):
  found = muninCheckHost(ip)
  
  if not found: continue

  fqdn = found[2] if found[1] == "unknown" else found[1] 

  dnsname  = found[1].split('.')[0].lower()
  snmpname = found[2].split('.')[0].lower()

  with open(hostsmods, 'a') as hosts:
   hosts.write("# {:<5} IP: {:<16} DNS:{:<12} FQDN:{:<16} SNMP:{}\n".format(str(dnsname == snmpname), ip, dnsname, dnsname + "." + adomain, snmpname))

  if not adomain in fqdn:
   # Truncate FQDN and add argument domain
   fqdn = fqdn.split('.')[0] + "." + adomain

  with open(muninadds, 'a') as munin:
   if found[3] == "VMware":
    if not fqdn in muninconfdict:
     muninAppendConf(muninconf, fqdn, ahandler, "no") 
    munin.write('ln -s /usr/share/munin/plugins/snmp__uptime /etc/munin/plugins/snmp_' + fqdn + '_uptime\n')              
    munin.write('ln -s /usr/local/sbin/plugins/snmp__esxi    /etc/munin/plugins/snmp_' + fqdn + '_esxi\n')

   if found[3] == "Juniper" and not found[5] == "other":
    if not fqdn in muninconfdict:
     muninAppendConf(muninconf, fqdn, ahandler, "no")
    munin.write('ln -s /usr/local/sbin/plugins/snmp__' + found[5] + ' /etc/munin/plugins/snmp_'+ fqdn +'_' + found[5] +'\n')
    munin.write('ln -s /usr/share/munin/plugins/snmp__uptime /etc/munin/plugins/snmp_' + fqdn + '_uptime\n')
    munin.write('ln -s /usr/share/munin/plugins/snmp__users  /etc/munin/plugins/snmp_' + fqdn + '_users\n')

    jdev = JRouter(ip)
    if jdev.connect():
     activeinterfaces = jdev.getUpInterfaces()
     jdev.close()
    else:
     print ip,"impossible to connect! [",found[1],"]"
    
    for ifd in activeinterfaces:
     munin.write('ln -s /usr/share/munin/plugins/snmp__if_   /etc/munin/plugins/snmp_' + fqdn + '_if_'+ ifd[2] +'\n')
