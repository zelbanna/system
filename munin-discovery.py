#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Program docstring.

Application to discovery network hosts on a subnet and deduce model (and manufacturer) and name
- Places found munin things  in /var/tmp/munin.conf
- Places found hosts updates in /var/tmp/hosts.conf

"""
__author__ = "Zacharias El Banna"
__version__ = "1.0"
__status__ = "Trial"

from netsnmp import VarList, Varbind, Session
from sys import argv, exit, path as syspath
syspath.append('/usr/local/sbin')
from SystemFunctions import pingOS
from JRouter import JRouter

############################### GENERICS ###############################
from struct import pack, unpack
from socket import inet_ntoa, inet_aton, gethostbyaddr

def ip2int(addr):                                                               
 return unpack("!I", inet_aton(addr))[0]

def int2ip(addr):                                                               
 return inet_ntoa(pack("!I", addr))   

############################## Checks model ##############################
#
# result tuple = [ ip, resolved_hname, snmp_hname, vendor, model, type ]
#  - resolved_hname = Unknown if existing device but not found in DNS, None otherwise
#  - snmp_hname     = Unknown if not found by SNMP

def checkModel(ahostname):
 try:
  devobjs = VarList(Varbind('.1.3.6.1.2.1.1.1.0'), Varbind('.1.3.6.1.2.1.1.5.0'))
  session = Session(Version = 2, DestHost = ahostname, Community = 'public', UseNumeric = 1, Timeout = 100000, Retries = 2)
  session.get(devobjs)
  try:
   name = gethostbyaddr(ahostname)[0]  
  except:
   name = "unknown"

  if devobjs[0].val == None:
   return [ ahostname, name, "unknown", None ] if pingOS(ahostname) else [ ahostname, "none", "unknown", None ]

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
 except Exception as exception_error:
  print "DEBUG " + str(exception_error)

#################### MAIN ####################
# print start, stop, stop - start

if len(argv) < 2:
 print argv[0] + " <start/single ip> [<end ip>]"
 exit(0)

start = ip2int(argv[1])
if len(argv) == 2:
 stop  = start  
else: 
 stop  = ip2int(argv[2])

with open('/var/tmp/munin.conf', 'w') as f:
 f.write('############ MUNIN CONF #############\n')
with open('/var/tmp/hosts.conf', 'w') as f:
 f.write('############ MUNIN HOST #############\n')

for ipint in range(start, stop + 1):
 found = checkModel(int2ip(ipint))
 name = found[2] if found[1] == "unknown" else found[1] 

 with open('/var/tmp/hosts.conf', 'a') as hosts:
  if found[1] == "unknown" and not found[2] == "unknown":
   hosts.write(found[0] + '\t' + found[2] + "\n")
  if not found[1] == 'none' and not found[1].split('.')[0] == found[2].split('.')[0]:
   hosts.write('# ' + found[1] + " is not " + found[2] + " for " + found[0] + "\n")

 with open('/var/tmp/munin.conf', 'a') as muninconf:
  if found[3] == "VMware":
   print "Found " + name
   muninconf.write('ln -s /usr/share/munin/plugins/snmp__uptime /etc/munin/plugins/snmp_' + name + '_uptime\n')              
   muninconf.write('ln -s /usr/local/sbin/plugins/snmp__esxi    /etc/munin/plugins/snmp_' + name + '_esxi\n')

  if found[3] == "Juniper" and not found[5] == "other":
   jdev = JRouter(found[0])
   if jdev.connect():
    print "Found " + name
    muninconf.write('ln -s /usr/local/sbin/plugins/snmp__' + found[5] + ' /etc/munin/plugins/snmp_'+ name +'_' + found[5] +'\n')
    muninconf.write('ln -s /usr/share/munin/plugins/snmp__uptime /etc/munin/plugins/snmp_' + name + '_uptime\n')
    muninconf.write('ln -s /usr/share/munin/plugins/snmp__users  /etc/munin/plugins/snmp_' + name + '_users\n')
    for ifd in jdev.getUpInterfaces():
     muninconf.write('ln -s /usr/share/munin/plugins/snmp__if_   /etc/munin/plugins/snmp_' + name + '_if_'+ ifd[2] +'\n')
    jdev.close()
   else:
    print found[1],"impossible to connect !"
