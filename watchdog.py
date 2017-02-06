#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Program docstring.

Watchdog for system settings

- Preferably site TTL is same as check frequency

"""
__author__ = "Zacharias El Banna"                     
__version__ = "3.3"
__status__ = "Production"

from socket import gethostbyname
from sys import argv, exit, path as syspath
syspath.append('/usr/local/sbin/')

if len(argv) < 5 or argv[1] not in [ "run", "debug", "install" ]:
 print argv[0] + " <run | debug | install> <fw> <local site NAME> <fw upstream interface> [<ipsec hub NAME>]"
 print ""
 print " - ipsec hub site name mist be same as gw in DNS (through lookup) AND used in ike, e.g. site-gw"
 print ""
 exit(0)

############################# INSTALL ########################
if argv[1] == "install":
 with open("/etc/cron.d/watchdog",'w') as cf:
  cf.write("""#
# cron-jobs for network watchdog
#

MAILTO=root

# Runs twice an hour, but that should really be in sync with DNS provider's TTL (for the local site at least) 
#
""")
  cf.write("28,58 * * * *   root /usr/local/sbin/watchdog.py run " + " ".join(argv[2:len(argv)]) + "\n")
 exit(0)

try:
 fwip = gethostbyname(argv[2])
except Exception as err:
 sysLogMsg("System Error - local name server resolution not working, check DNS status")
 exit(1)


if len(argv) > 5:
 gw = argv[5]
 gwname = gw + "-gw"
else:
 gw = ""
 gwname = ""

site = argv[3]
upif = argv[4]

########################### Run ################################
from JRouter import SRX
from DNS import getLoopiaIP, setLoopiaIP, getLoopiaSuffix, syncPDNS
from SystemFunctions import sysCheckResults, sysLogMsg, sysSetDebug, sysLogDebug

if argv[1] == "debug":
 sysSetDebug(True)

try:
 srx = SRX(fwip)
 if srx.connect():
  sysLogDebug("Connected to: " + fwip)
  srx.checkDHCP()

  # First check DNS recursion
  if len(srx.dnslist) > 0:
   if srx.pingRPC(srx.dnslist[0]):
    syncPDNS(srx.dnslist)
    if srx.dhcpip != gethostbyname(site + getLoopiaSuffix()):
     if srx.dhcpip != getLoopiaIP(site):
      setLoopiaIP(site,srx.dhcpip)

    # Check IPsec, can we reach the hub?  
    if not gw == "":
     address, tunnels = srx.getIPsec(gwname)

     # Assume if one tunnel is up it's the hub 
     if tunnels == 0:
      # no tunnels active
      gwip = gethostbyname(gw + getLoopiaSuffix())
      # check configured gw ip, still ok - try to ping, otherwise reconf 
      if gwip == address:
       sysLogMsg("Reachability Check - Ping IPsec gateway (" + gw + " | " + gwip + "): " + sysCheckResults(srx.pingRPC(gwip)))
      else: 
       sysLogMsg("Reachability Check - Reconfigure IPsec gateway: " + sysCheckResults(srx.setIPsec(gwname,address,gwip)))
  
   else:
    sysLogMsg("Reachability Error - Can't reach external name server (DNS): " + srx.dnslist[0])
    exit(1) 
    
  else:
   sysLogMsg("Reachability Error - Can't find DNS in DHCP lease, renewing")
   srx.renewDHCP(upif)
  srx.close()
 else:
  sysLogMsg("System Error - Cannot reach firewall, check Power and Cables are ok")
   
except Exception as checks:
 sysLogMsg("Watchdog Error: " + str(checks))
