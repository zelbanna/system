#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

Module for Rack Utility Classes (Power, UPS, Console)

Exports:
- PDU
- Console

"""  
__author__  = "Zacharias El Banna"
__version__ = "0.1"
__status__  = "Beta"

from GenLib import GenDevice, sys_log_msg

######################################## Console ########################################
#
# Opengear :-)
#

class OpenGear(GenDevice):

 def __init__(self, ahost, adomain):
  GenDevice.__init__(self,ahost,adomain,'console')
  self._configitems = {}

 def __str__(self):
  return "OpenGear: {}".format(GenDevice.__str__(self))
 
 def get_entry(self, akey):
  return self._configitems.get(akey,None)

 def get_entries(self):
  keys = self._configitems.keys()
  keys.sort()
  return keys

 def load_conf(self):
  from netsnmp import VarList, Varbind, Session
  try:
   portobjs = VarList(Varbind('.1.3.6.1.4.1.25049.17.2.1.2'))
   session = Session(Version = 2, DestHost = self._hostname, Community = "public", UseNumeric = 1, Timeout = 100000, Retries = 2)
   session.walk(portobjs)
   self._configitems.clear()
   for result in portobjs:
    # [ Port , Name ]
    self._configitems[ int(result.iid) ] = result.val
  except Exception as exception_error:
   print "OpenGear : error loading conf " + str(exception_error)
   sys_log_msg("OpenGear : error loading conf " + str(exception_error))


######################################## PDU ########################################
#
# APC :-)
#

class APC(GenDevice):

 _statemap = { '1':'off', '2':'on' }
 @classmethod 
 def get_outlet_state(cls,sint):
  return cls._statemap.get(sint,'unknown')
 
 def __init__(self, ahost, adomain):
  GenDevice.__init__(self,ahost,adomain,'apc')
  self._configitems = {}

 def __str__(self):
  return "APC: {}".format(GenDevice.__str__(self))

 def get_entry(self, akey):
  return self._configitems.get(akey,None)

 def get_entries(self):
  keys = self._configitems.keys()
  keys.sort()
  return keys

 def set_conf(self):
  pass

 def load_conf(self):
  from netsnmp import VarList, Varbind, Session
  try:
   outletobjs = VarList(Varbind('.1.3.6.1.4.1.10418.17.2.5.5.1.4'))
   stateobjs  = VarList(Varbind('.1.3.6.1.4.1.10418.17.2.5.5.1.5'))
   session = Session(Version = 2, DestHost = self._fqdn, Community = "public", UseNumeric = 1, Timeout = 100000, Retries = 2)
   session.walk(outletobjs)
   session.walk(stateobjs)
   statedict = dict(map(lambda var: (var.tag[34:] + "." + var.iid, var.val), stateobjs))
   # create object dict and two TD:s per row?      

   for outlet in outletobjs:
    # outlet.iid = outlet number
    lpdu=outlet.tag[34:]
    self._configitems[ lpdu + ":" + outlet.iid ] = [ outlet.val, APC.get_outlet_state(statedict[lpdu+"."+outlet.iid]) ]
  except Exception as exception_error:
   print "APC : error loading conf " + str(exception_error)
   sys_log_msg("APC : error loading conf " + str(exception_error))


  

