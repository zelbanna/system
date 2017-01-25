#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

System, DNS and networking interworking module

- One can use other modules imported by this one "nested :-)

"""
__author__ = "Zacharias El Banna"                     
__version__ = "2.0"
__status__ = "Production"

from sys import argv, exit, path as syspath
from jnpr.junos import Device
from jnpr.junos.utils.config import Config
from lxml import etree
from os import system, getpid
from socket import gethostbyname
from subprocess import check_output, check_call
from time import sleep, strftime, localtime
syspath.append('/etc')
import PasswordContainer as PC


################################# Generics ####################################
#
# Convert True/False of test to Success/Failure
def checkResults(test):
 return "success" if test else "failure"

debug = False

def setDebug(astate):
 global debug
 debug = astate
  
def logMsg(amsg):
 if debug: print "Log: " + amsg
 with open('/var/log/system/network.functions.log', 'a') as f:
  f.write(unicode("{} : {}\n".format(strftime('%Y-%m-%d %H:%M:%S', localtime()), amsg)))

################################ LOOPIA DNS ###################################
#
# Change IP for a domain in loopia DNS
#
loopia_domain_server_url = 'https://api.loopia.se/RPCSERV' 

def setLoopiaIP(subdomain, newip):
 import xmlrpclib
 try:
  client = xmlrpclib.ServerProxy(uri = loopia_domain_server_url, encoding = 'utf-8')
  data = client.getZoneRecords(PC.loopia_username, PC.loopia_password, PC.loopia_domain, subdomain)[0]
  oldip = data['rdata']
  data['rdata'] = newip
  status = client.updateZoneRecord(PC.loopia_username, PC.loopia_password, PC.loopia_domain, subdomain, data)[0]
 except Exception as exmlrpc:
  logMsg("System Error - Loopia set: " + str(exmlrpc))
  return False
 return True

#
# Get Loopia settings for subdomain
#
def getLoopiaIP(subdomain):
 import xmlrpclib
 try:
  client = xmlrpclib.ServerProxy(uri = loopia_domain_server_url, encoding = 'utf-8')
  data = client.getZoneRecords(PC.loopia_username, PC.loopia_password, PC.loopia_domain, subdomain)[0]
  return data['rdata']
 except Exception as exmlrpc:
  logMsg("System Error - Loopia get: " + str(exmlrpc))
  return False


################################# OpenDNS ######################################
#
# Return external IP from opendns
#
def OpenDNSmyIP():
 from dns import resolver
 try:
  opendns = resolver.Resolver()
  opendns.nameservers = [gethostbyname('resolver1.opendns.com')]
  myiplookup = opendns.query("myip.opendns.com",'A').response.answer[0]
  return str(myiplookup).split()[4]
 except Exception as exresolve:
  logMsg("OpenDNS Error - Resolve: " + str(exresolve))
  return False

################################ JUNOS RPCs #####################################
#
# Connecto to Router, a couple of RPCs will be issued from there
#

class SRX(object):

 def __init__(self,hostname):
  self.router = Device(hostname, user=PC.netconf_username, password=PC.netconf_password, normalize=True)
  self.dnslist = []
  self.dhcpip = ""
  self.tunnels = 0
 
 def __str__(self):
  return str(self.router) + " DNS:" + str(self.dnslist) + " IP:" + self.dhcpip + " IPsec:" + str(self.tunnels)

 def connect(self):
  try:
   self.router.open()
  except Exception as err:
   logMsg("System Error - Unable to connect to router: " + str(err))
   return False
  return True

 def close(self):
  try:
   self.router.close()
  except Exception as err:
   logMsg("System Error - Unable to properly close router connection: " + str(err))

 def checkDHCP(self):
  try:
   result = self.router.rpc.get_dhcp_client_information() 
   addresslist = result.xpath(".//address-obtained")
   if len(addresslist) > 0:
    self.dnslist = result.xpath(".//dhcp-option[dhcp-option-name='name-server']/dhcp-option-value")[0].text.strip('[] ').replace(", "," ").split()
    self.dhcpip = addresslist[0].text
  except Exception as err:
   logMsg("System Error - verifying DHCP assignment: " + str(err))
   return False
  return True

 def renewDHCP(self, interface):
  try:
   return self.router.rpc.cli("request system services dhcp renew " + interface, format='text')
  except Exception as err:
   logMsg("System Error - cannot renew DHCP lease: " +str(err))
  return False
   
 def checkIPsec(self,gwname):
  try:
   # Could actually just look at "show security ike security-associations" - len of that result
   # is the number of ikes (not tunnels though) with GW etc
   # If tunnel is down though we don't know if config is aggresive or state down, should check
   self.tunnels = int(self.router.rpc.get_security_associations_information()[0].text)
   ike = self.router.rpc.get_config(filter_xml=etree.XML('<configuration><security><ike><gateway></gateway></ike></security></configuration>'))
   address = ike.xpath(".//gateway[name='" + gwname + "']/address")
   return False if len(address) == 0 else address[0].text
  except Exception as err:
   logMsg("System Error - reading IPsec data: " + str(err))
  return False

 def setIPsec(self,gwname,oldip,newip):
  cu = Config(self.router)
  try:
   cu.load("set security ike gateway " + gwname + " address " + newip, format = 'set')
   cu.load("delete security ike gateway " + gwname + " address " + oldip, format = 'set')
   cu.commit("commit by setIPsec ["+gwname+"]")
  except Exception as err:
   logMsg("System Error - modifying IPsec: " + str(err))
   return False
  return True

 def pingRPC(self,ip):
  result = self.router.rpc.ping(host=ip, count='1')
  return len(result.xpath("ping-success"))

 def getRPC(self):
  return self.router.rpc

 def getDev(self):
  return self.router

################################ OS SYSTEM FUNCTIONS ###################################
#
# Ping from node to different services
#
def pingOS(ip):
 return system("ping -c 1 -w2 " + ip + " > /dev/null 2>&1") == 0

def getIPBySite(site):
 return gethostbyname(site + "." + PC.loopia_domain)
 
############################### PDNS SYSTEM FUNCTIONS ##################################
#

def getPDNS():
 recursor = check_output(["sudo","/bin/grep", "^recursor","/etc/powerdns/pdns.conf"])
 return recursor.split('=')[1].split('#')[0].strip()

#
# Replace 'old' recursor with 'new'
#

def setPDNS(old,new):
 if new == "":
  return False
 filedata = None
 with open('/etc/powerdns/pdns.conf', 'r') as file :
  filedata = file.read()

 filedata = filedata.replace("recursor="+old, "recursor="+new)

 with open('/etc/powerdns/pdns.conf', 'w') as file:
  file.write(filedata)
 return True

#
# All-in-one, runs check, verify and (if needed) set and reload pdns service
# - returns True if was in sync and False if modified
# 
def syncPDNS(dnslist):
 pdns = getPDNS()
 if not pdns in dnslist:
  logMsg("System Info - updating recursor to " + dnslist[0])
  setPDNS(pdns,dnslist[0])
  try:
   check_call(["/usr/sbin/service","pdns","reload"])
   sleep(1)
  except Exception as svcerr:
   logMsg("System Error - Reloading PowerDNS: " + str(svcerr))
  return False
 return True  
