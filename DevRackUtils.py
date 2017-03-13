"""Module docstring.

Module for Rack Utility Classes (Power, UPS, Console)

Exports:
- PDU
- Console

"""  
__author__  = "Zacharias El Banna"
__version__ = "0.1"
__status__  = "Beta"

from GenLib import GenDevice, ConfObject, sys_log_msg
import PasswordContainer as PC

######################################## Console ########################################
#
# Opengear :-)
#

class OpenGear(GenDevice, ConfObject):

 def __init__(self, ahost, adomain = None):
  GenDevice.__init__(self,ahost,adomain,'console')
  ConfObject.__init__(self,None)

 def __str__(self):
  return "OpenGear - {}".format(GenDevice.__str__(self))

 def load_snmp(self):
  from netsnmp import VarList, Varbind, Session
  try:
   portobjs = VarList(Varbind('.1.3.6.1.4.1.25049.17.2.1.2'))
   session = Session(Version = 2, DestHost = self._ip, Community = PC.snmp_read_community, UseNumeric = 1, Timeout = 100000, Retries = 2)
   session.walk(portobjs)
   self._configitems.clear()
   for result in portobjs:
    # [ Port ] = Name
    self._configitems[ int(result.iid) ] = result.val
  except Exception as exception_error:
   print "OpenGear : error loading conf " + str(exception_error)
   sys_log_msg("OpenGear : error loading conf " + str(exception_error))


######################################## PDU ########################################
#
# Avocent :-)
#

# Sort key function: lambda x: int(x.split('.')[0])*100+int(x.split('.')[1])
class Avocent(GenDevice, ConfObject):

 _getstatemap = { '1':'off', '2':'on' }
 _setstatemap = { 'off':'3', 'on':'2', 'reboot':'4' }

 @classmethod 
 def get_outlet_state(cls,state):
  return cls._getstatemap.get(state,'unknown')

 @classmethod
 def set_outlet_state(cls,state):
  return cls._setstatemap.get(state,'1')

 def __init__(self, ahost, adomain):
  GenDevice.__init__(self,ahost,adomain,'pdu')
  ConfObject.__init__(self,None)

 def __str__(self):
  return "Avocent - {}".format(GenDevice.__str__(self))

 def set_state(self,node,state):
  from netsnmp import VarList, Varbind, Session
  try:
   # node = "pdu.outlet"
   session = Session(Version = 2, DestHost = self._ip, Community = PC.snmp_write_community, UseNumeric = 1, Timeout = 100000, Retries = 2)
   setobj = VarList(Varbind("enterprises", "10418.17.2.5.5.1.6.1." + node , Avocent.set_outlet_state(state) ,"INTEGER"))
   session.set(setobj)
   entry = self.get_entry(node)
   if entry:
    entry['state'] = state
   sys_log_msg("Avocent : {0} set state to {0} on {0}".format(self._ip,state,node))
  except Exception as exception_error:
   print "Avocent : error setting state " + str(exception_error)
   sys_log_msg("Avocent : error setting state " + str(exception_error))

 def set_name(self,node,name):
  from netsnmp import VarList, Varbind, Session
  try:
   # node = pdu.outlet
   session = Session(Version = 2, DestHost = self._ip, Community = PC.snmp_write_community, UseNumeric = 1, Timeout = 100000, Retries = 2)
   setobj = VarList(Varbind("enterprises", "10418.17.2.5.5.1.4.1." + node , name, "OPAQUE"))
   session.set(setobj)
   entry = self.get_entry(node)
   if entry:
    entry['name'] = name
  except Exception as exception_error:
   print "Avocent : error setting name " + str(exception_error)
   sys_log_msg("Avocent : error setting name " + str(exception_error))

 def load_snmp(self):
  from netsnmp import VarList, Varbind, Session
  try:
   outletobjs = VarList(Varbind('.1.3.6.1.4.1.10418.17.2.5.5.1.4'))
   stateobjs  = VarList(Varbind('.1.3.6.1.4.1.10418.17.2.5.5.1.5'))
   pduobjs = VarList(Varbind('.1.3.6.1.4.1.10418.17.2.5.3.1.3'))
   session = Session(Version = 2, DestHost = self._ip, Community = PC.snmp_read_community, UseNumeric = 1, Timeout = 100000, Retries = 2)
   session.walk(outletobjs)
   session.walk(stateobjs)
   session.walk(pduobjs)
   statedict = dict(map(lambda var: (var.tag[34:] + "." + var.iid, var.val), stateobjs))
   pdudict   = dict(map(lambda var: (var.iid, var.val),pduobjs))
   for outlet in outletobjs:
    # outlet.iid = outlet number
    pdu= outlet.tag[34:]
    node = pdu + "." + outlet.iid
    self._configitems[ node ] = { 'name': outlet.val, 'state':Avocent.get_outlet_state(statedict[node]), 'pduslot':pdudict.get(pdu,"unknown") + "." + outlet.iid }
  except Exception as exception_error:
   print "Avocent : error loading conf " + str(exception_error)
   sys_log_msg("Avocent : error loading conf " + str(exception_error))
 
 def get_pdu_names(self):
  from netsnmp import VarList, Varbind, Session
  pdus = []
  try:
   pduobjs = VarList(Varbind('.1.3.6.1.4.1.10418.17.2.5.3.1.3'))
   session = Session(Version = 2, DestHost = self._ip, Community = PC.snmp_read_community, UseNumeric = 1, Timeout = 100000, Retries = 2)
   session.walk(pduobjs)
   for pdu in pduobj:
    pdus.append([pdu.iid, pdu.val])
  except Exception as exception_error:
   print "Avocent : error loading pdu member names " + str(exception_error)
   sys_log_msg("Avocent : error loading pdu member names " + str(exception_error))
  return pdus
