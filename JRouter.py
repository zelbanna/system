#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

Junos Router

"""
__author__ = "Zacharias El Banna"                     
__version__ = "3.0"
__status__ = "Production"

from lxml import etree

from PasswordContainer import netconf_username, netconf_password

################################ JUNOS RPCs #####################################
#
# Connecto to Router, a couple of RPCs will be issued from there
#

class SRX(object):

 def __init__(self,hostname):
  from jnpr.junos import Device
  from jnpr.junos.utils.config import Config
  self.router = Device(hostname, user=netconf_username, password=netconf_password, normalize=True)
  self.config = Config(self.router)
  self.dnslist = []
  self.dhcpip = ""
  self.tunnels = 0
 
 def __str__(self):
  return str(self.router) + " DNS:" + str(self.dnslist) + " IP:" + self.dhcpip + " IPsec:" + str(self.tunnels)

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

 def pingRPC(self,ip):
  result = self.router.rpc.ping(host=ip, count='1')
  return len(result.xpath("ping-success"))

 def getRPC(self):
  return self.router.rpc

 def getDev(self):
  return self.router
