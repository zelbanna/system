#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

Junos Router Base Class
- JRouter
- SRX functions
- EX functions

"""
__author__ = "Zacharias El Banna"
__version__ = "4.3"
__status__ = "Production"

from PasswordContainer import netconf_username, netconf_password
from SystemFunctions import sysLogMsg
from netsnmp import VarList, Varbind, Session
from lxml import etree

################################ JUNOS Object #####################################
#
# Connect to Router, a couple of RPCs will be issued from there
#

class JRouter(object):

 def __init__(self,hostname):
  from jnpr.junos import Device
  from jnpr.junos.utils.config import Config
  self._router = Device(hostname, user=netconf_username, password=netconf_password, normalize=True)
  self._config = Config(self._router)
  self._type = ""
  self._model = ""
  self._version = ""
  self._interfacesname = {}
 
 def __str__(self):
  return str(self._router) + " Type:" + self._type + " Model:" + self._model + " Version:" + self._version

 def connect(self):
  try:
   self._router.open()
   self._model = self._router.facts['model']
   self._version = self._router.facts['version']
  except Exception as err:
   sysLogMsg("System Error - Unable to connect to router: " + str(err))
   return False
  return True

 def close(self):
  try:
   self._router.close()
  except Exception as err:
   sysLogMsg("System Error - Unable to properly close router connection: " + str(err))
 
 def pingRPC(self,ip):
  result = self._router.rpc.ping(host=ip, count='1')
  return len(result.xpath("ping-success"))

 def getRPC(self):
  return self._router.rpc

 def getDev(self):
  return self._router

 def getInfo(self,akey):
  return self._router.facts[akey]

 def getType(self):
  return self._type

 def checkInterfacesName(self):
  interfaces = self._router.rpc.get_interface_information(descriptions=True)
  for interface in interfaces:
   ifd         = interface.find("name").text
   description = interface.find("description").text
   self._interfacesname[ifd] = description

 def getInterfaceName(self, aifl):
  return self._interfacesname.get(aifl.split('.')[0],None)

 def getUpInterfaces(self):
  interfaces = self._router.rpc.get_interface_information()
  result = []
  for ifd in interfaces:
   status = map((lambda pos: ifd[pos].text), [0,2,4,5])
   if status[0].split('-')[0] in [ 'ge', 'fe', 'xe', 'et','st0' ] and status[1] == "up":
    result.append(status)
  return result
 
 #
 # SNMP is much smoother than Netconf for some things :-)
 #
 def quickCheck(self):
  try:
   devobjs = VarList(Varbind('.1.3.6.1.2.1.1.1.0'))
   session = Session(Version = 2, DestHost = self._router._hostname, Community = 'public', UseNumeric = 1, Timeout = 100000, Retries = 2)
   session.get(devobjs)
   datalist = devobjs[0].val.split()
   self._model = datalist[3]
   self._version = datalist[datalist.index('JUNOS') + 1].strip(',')
   if "ex" in self._model:
    self._type = "EX"
   elif "srx" in self._model:
    self._type = "SRX"
   elif "qfx" in self._model:
    self._type = "QFX"
   elif "mx" in self._model:
    self._type = "MX"
  except:
   pass         

################################ SRX Object #####################################

class SRX(JRouter):

 def __init__(self,hostname):
  JRouter.__init__(self, hostname)
  self.dnslist = []
  self.dhcpip = ""
  self.tunnels = 0
  self._type = "SRX"

 def __str__(self):
  return JRouter.__str__(self) + " DNS:" + str(self.dnslist) + " IP:" + self.dhcpip + " IPsec:" + str(self.tunnels)

 def checkDHCP(self):
  try:
   result = self._router.rpc.get_dhcp_client_information() 
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
   return self._router.rpc.cli("request system services dhcp renew " + interface, format='text')
  except Exception as err:
   sysLogMsg("System Error - cannot renew DHCP lease: " +str(err))
  return False
   
 def getIPsec(self,gwname):
  try:
   # Could actually just look at "show security ike security-associations" - len of that result
   # is the number of ikes (not tunnels though) with GW etc
   # If tunnel is down though we don't know if config is aggresive or state down, should check
   self.tunnels = int(self._router.rpc.get_security_associations_information()[0].text)
   ike = self._router.rpc.get_config(filter_xml=etree.XML('<configuration><security><ike><gateway></gateway></ike></security></configuration>'))
   address = ike.xpath(".//gateway[name='" + gwname + "']/address")
   return address[0].text, self.tunnels
  except Exception as err:
   sysLogMsg("System Error - getting IPsec data: " + str(err))
   return None, self.tunnels

 def setIPsec(self,gwname,oldip,newip):
  try:
   self._config.load("set security ike gateway " + gwname + " address " + newip, format = 'set')
   self._config.load("delete security ike gateway " + gwname + " address " + oldip, format = 'set')
   self._config.commit("commit by setIPsec ["+gwname+"]")
  except Exception as err:
   sysLogMsg("System Error - modifying IPsec: " + str(err))
   return False
  return True

################################ EX Object #####################################

class EX(JRouter):

 def __init__(self,hostname):
  JRouter.__init__(self, hostname)
  self._type = "EX"
  self._style  = None
  self._interfacenames = {}

 def __str__(self):
  return JRouter.__str__(self) + " Style:" + str(self._style)

 #
 # should prep for ELS only and send "instance = 'default-instance'" - then id could be retrieved too
 # since grouping is different
 #
 def getSwitchTable(self):
  fdblist = []
  try:
   swdata = self._router.rpc.get_ethernet_switching_table_information()
   if swdata.tag == "l2ng-l2ald-rtb-macdb":
    self._style = "ELS"
    for entry in swdata[0].iter("l2ng-mac-entry"):
     vlan = entry.find("l2ng-l2-mac-vlan-name").text
     mac  = entry.find("l2ng-l2-mac-address").text     
     interface = entry.find("l2ng-l2-mac-logical-interface").text
     fdblist.append([ vlan, mac, interface, self.getInterfaceName(interface) ])
   elif swdata.tag == "ethernet-switching-table-information":
    self._style = "Legacy"
    for entry in swdata[0].iter("mac-table-entry"):
     vlan = entry.find("mac-vlan").text
     mac  = entry.find("mac-address").text
     interface = entry.find(".//mac-interfaces").text
     if not mac == "*" and not interface == "Router":
      fdblist.append([ vlan, mac, interface, self.getInterfaceName(interface) ]) 
  except Exception as err:
   sysLogMsg("System Error - fetching FDB: " + str(err))
  return fdblist
