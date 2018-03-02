#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Program docstring.

Watchdog for system settings

- Preferably site TTL is same as check frequency

"""
__author__ = "Zacharias El Banna"                     
__version__ = "5.0"
__status__ = "Production"

from socket import gethostbyname
from sys import argv, exit, path as syspath
syspath.append('/usr/local/sbin/')
from sdcp.core.extras import get_results
from sdcp.core.logger import log

if len(argv) < 5 or argv[1] not in [ "run", "install" ]:
 print argv[0] + " <run | install> <fw> <local site NAME> <fw upstream interface> [<ipsec hub NAME>]"
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
 log("System Error - local name server resolution not working, check DNS status")
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
from sdcp.tools.dns import get_loopia_ip, set_loopia_ip, get_loopia_suffix, pdns_sync
from sdcp.devices.srx import Device

try:
 srx = Device(fwip)
 if srx.connect():
  srx.load_dhcp()

  # First check DNS recursion
  if len(srx.dnslist) > 0:
   if srx.ping_rpc(srx.dnslist[0]):
    pdns_sync(srx.dnslist)
    if srx.dhcpip != gethostbyname(site + get_loopia_suffix()):
     if srx.dhcpip != get_loopia_ip(site):
      set_loopia_ip(site,srx.dhcpip)
    # Check IPsec, can we reach the hub?  
    if not gw == "":
     address, tunnels = srx.get_ipsec(gwname)
     # Assume if one tunnel is up it's the hub 
     if tunnels == 0:
      # no tunnels active
      gwip = gethostbyname(gw + get_loopia_suffix())
      # check configured gw ip, still ok - try to ping, otherwise reconf 
      if gwip == address:
       log("Reachability Check - Ping IPsec gateway (" + gw + " | " + gwip + "): " + get_results(srx.ping_rpc(gwip)))
      else: 
       log("Reachability Check - Reconfigure IPsec gateway: " + get_results(srx.set_ipsec(gwname,address,gwip)))
   else:
    log("Reachability Error - Can't reach external name server (DNS): " + srx.dnslist[0])
    exit(1) 
    
  else:
   log("Reachability Error - Can't find DNS in DHCP lease, renewing")
   srx.renew_dhcp(upif)
  srx.close()
 else:
  log("System Error - Cannot reach firewall, check Power and Cables are ok")
   
except Exception as checks:
 log("Watchdog Error: " + str(checks))
