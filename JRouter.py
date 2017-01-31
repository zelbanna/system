#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

Junos Router

- SRX functions should be overloaded on top of JRouter

"""
__author__ = "Zacharias El Banna"
__version__ = "4.0"
__status__ = "Production"

from lxml import etree
from PasswordContainer import netconf_username, netconf_password
from netsnmp import VarList, Varbind, Session
from SystemFunctions import sysLogMsg

################################ JUNOS Object #####################################
#
# Connect to Router, a couple of RPCs will be issued from there
#

class JRouter(object):

 def __init__(self,hostname):
  from jnpr.junos import Device
  from jnpr.junos.utils.config import Config
  self.router = Device(hostname, user=netconf_username, password=netconf_password, normalize=True)
  self.config = Config(self.router)
  self.type = None
 
 def __str__(self):
  if not self.router.facts == {}:
   return str(self.router) + " Model:" + self.router.facts['model'] + " Version:" + self.router.facts['version']
  else:
   return str(self.router)

 def connect(self):
  try:
   self.router.open()
  except Exception as err:
   sysLogMsg("System Error - Unable to connect to router: " + str(err))
   return False
  return True

 def close(self):
  try:
   self.router.close()
  except Exception as err:
   sysLogMsg("System Error - Unable to properly close router connection: " + str(err))
 
 def pingRPC(self,ip):
  result = self.router.rpc.ping(host=ip, count='1')
  return len(result.xpath("ping-success"))

 def getRPC(self):
  return self.router.rpc

 def getDev(self):
  return self.router

 def getInfo(self,akey):
  return self.router.facts[akey]

 def getType(self):
  return self.type

 def getUpInterfaces(self):
  # Could have used (terse=True) but that doesn't give SNMP index for munin...
  interfaces = self.router.rpc.get_interface_information()
  result = []
  for intf in interfaces:
   status = map((lambda pos: intf[pos].text), [0,2,4])
   if status[0].split('-')[0] in [ 'ge', 'fe', 'xe', 'et','st0' ] and status[1] == "up":
    result.append(status)
  return result

################################ SRX Object #####################################

class SRX(JRouter):

 def __init__(self,hostname):
  JRouter.__init__(self, hostname)
  self.dnslist = []
  self.dhcpip = ""
  self.tunnels = 0
  self.type = "SRX"

 def __str__(self):
  return JRouter.__str__(self) + " DNS:" + str(self.dnslist) + " IP:" + self.dhcpip + " IPsec:" + str(self.tunnels)

 def checkDHCP(self):
  try:
   result = self.router.rpc.get_dhcp_client_information() 
   addresslist = result.xpath(".//address-obtained")
   if len(addresslist) > 0:
    self.dnslist = result.xpath(".//dhcp-option[dhcp-option-name='name-server']/dhcp-option-value")[0].text.strip('[] ').replace(", "," ").split()
    self.dhcpip = addresslist[0].text
  except Exception as err:
   sysLogMsg("System Error - verifying DHCP assignment: " + str(err))
   return False
  return True

 def renewDHCP(self, interface):
  try:
   return self.router.rpc.cli("request system services dhcp renew " + interface, format='text')
  except Exception as err:
   sysLogMsg("System Error - cannot renew DHCP lease: " +str(err))
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
   sysLogMsg("System Error - reading IPsec data: " + str(err))
  return False

 def setIPsec(self,gwname,oldip,newip):
  try:
   self.config.load("set security ike gateway " + gwname + " address " + newip, format = 'set')
   self.config.load("delete security ike gateway " + gwname + " address " + oldip, format = 'set')
   self.config.commit("commit by setIPsec ["+gwname+"]")
  except Exception as err:
   sysLogMsg("System Error - modifying IPsec: " + str(err))
   return False
  return True

